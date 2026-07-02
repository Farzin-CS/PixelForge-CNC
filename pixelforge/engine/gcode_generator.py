"""
gcode_generator.py
==================
PixelForge CNC -- Professional G-code generation engine.

Generates optimized CNC G-code from grayscale depth maps with:
  - Rapid traversal (G0) over zero-depth areas with safe Z retraction
  - Z-axis ramped entry to prevent tool breakage on V-bits
  - Configurable carving strategies (zigzag, climb, conventional)
  - Vectorized NumPy operations for fast segment detection
  - Real-time progress callbacks
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from pixelforge.engine.types import (
    CarvingStrategy,
    CuttingDirection,
    GCodeConfig,
    GCodeStats,
    ProgressCallback,
    ToolpathSegment,
)


# ============================================================
# SEGMENT DETECTION (Vectorized NumPy)
# ============================================================

def _find_segments_in_row(
    depth_row: np.ndarray,
    row_index: int,
    y_mm: float,
    direction: CuttingDirection,
    skip_threshold: float,
    px_width: float,
) -> list[ToolpathSegment]:
    """Detect cutting segments in a single raster row using vectorized ops.

    Finds contiguous runs of pixels where the depth contribution exceeds
    the skip threshold. Returns one ToolpathSegment per contiguous group,
    so that gaps between groups result in separate rapid-traversal moves.

    Args:
        depth_row: 1D array of pixel values (0-255) for this row.
        row_index: Row index in the depth map.
        y_mm: Y coordinate in mm for this row.
        direction: Horizontal cutting direction.
        skip_threshold: Normalized threshold below which pixels are skipped.
        px_width: Width of a single pixel in mm.

    Returns:
        List of ToolpathSegment objects (one per contiguous cutting group).
    """
    # Boolean mask of pixels that need cutting.
    # Darker pixels (lower value) = deeper cut.
    # Depth contribution = (255 - pix) / 255.  A pixel is cut if this
    # exceeds the skip_threshold (normalized 0-1).
    depth_contribution = (255.0 - depth_row.astype(np.float64)) / 255.0
    cutting_mask = depth_contribution > skip_threshold

    if not np.any(cutting_mask):
        return []

    # Vectorized: find indices where cutting_mask transitions
    # Pad with False at both ends to detect edges
    padded = np.concatenate(([False], cutting_mask, [False]))
    transitions = np.diff(padded.astype(np.int8))

    # +1 = segment starts, -1 = segment ends
    starts = np.where(transitions == 1)[0]  # first True index
    ends = np.where(transitions == -1)[0]  # first False after True

    # Build a separate ToolpathSegment for each contiguous group
    segments: list[ToolpathSegment] = []
    for s, e in zip(starts, ends):
        cols = list(range(int(s), int(e)))
        if not cols:
            continue
        if direction == CuttingDirection.RIGHT_TO_LEFT:
            cols.sort(reverse=True)
        else:
            cols.sort()
        segments.append(
            ToolpathSegment(
                cols=cols,
                row=row_index,
                y_mm=y_mm,
                direction=direction,
            )
        )

    return segments


def _build_all_segments(
    depth_map: np.ndarray,
    config: GCodeConfig,
) -> list[ToolpathSegment]:
    """Build ordered toolpath segments for the entire depth map.

    Iterates rows in the order dictated by the carving strategy, and
    for each row detects cutting segments.

    Args:
        depth_map: Grayscale depth map (H, W) with values 0-255.
        config: G-code generation configuration.

    Returns:
        Ordered list of ToolpathSegment objects.
    """
    rows, cols = depth_map.shape
    px_width = config.width_mm / cols if cols > 0 else 0.1

    # Determine row order and direction per strategy
    row_order = _get_row_order(rows, config.carving_strategy)

    segments: list[ToolpathSegment] = []
    for row_idx, direction in row_order:
        y_mm = row_idx * config.line_spacing_mm
        row_segments = _find_segments_in_row(
            depth_map[row_idx],
            row_idx,
            y_mm,
            direction,
            config.skip_threshold,
            px_width,
        )
        segments.extend(row_segments)

    return segments


def _get_row_order(
    num_rows: int, strategy: CarvingStrategy
) -> list[tuple[int, CuttingDirection]]:
    """Determine row processing order and direction for a carving strategy.

    Args:
        num_rows: Total number of rows in the depth map.
        strategy: The carving strategy to use.

    Returns:
        List of (row_index, direction) tuples in cutting order.
    """
    if strategy == CarvingStrategy.ONE_WAY_CLIMB:
        return [(i, CuttingDirection.LEFT_TO_RIGHT) for i in range(num_rows)]
    elif strategy == CarvingStrategy.ONE_WAY_CONVENTIONAL:
        return [(i, CuttingDirection.RIGHT_TO_LEFT) for i in range(num_rows)]
    else:  # ZIGZAG
        return [
            (
                i,
                CuttingDirection.LEFT_TO_RIGHT if i % 2 == 0
                else CuttingDirection.RIGHT_TO_LEFT,
            )
            for i in range(num_rows)
        ]


# ============================================================
# G-CODE LINE BUILDERS
# ============================================================

def _g0_rapid(x: float, y: float, z: float) -> str:
    """Generate a G0 rapid move line.

    Args:
        x: Target X position in mm.
        y: Target Y position in mm.
        z: Target Z position in mm.

    Returns:
        Formatted G0 line (e.g. 'G0 X10.000 Y5.000 Z2.000').
    """
    return f"G0 X{x:.3f} Y{y:.3f} Z{z:.3f}"


def _g1_move(x: float, z: float, feed: float) -> str:
    """Generate a G1 cutting move with explicit feed rate.

    Args:
        x: Target X position in mm.
        z: Target Z depth in mm.
        feed: Feed rate in mm/min.

    Returns:
        Formatted G1 line.
    """
    return f"G1 X{x:.3f} Z{z:.3f} F{feed:.0f}"


def _g1_xy(x: float, feed: float) -> str:
    """Generate a G1 XY move (no Z change) with feed rate.

    Args:
        x: Target X position in mm.
        feed: Feed rate in mm/min.

    Returns:
        Formatted G1 line.
    """
    return f"G1 X{x:.3f} F{feed:.0f}"


def _g1_xz(x: float, z: float) -> str:
    """Generate a G1 move with X and Z change (implicit feed).

    Args:
        x: Target X position in mm.
        z: Target Z depth in mm.

    Returns:
        Formatted G1 line.
    """
    return f"G1 X{x:.3f} Z{z:.3f}"


def _g1_x(x: float) -> str:
    """Generate a G1 X-only move (no Z change, implicit feed).

    Args:
        x: Target X position in mm.

    Returns:
        Formatted G1 line.
    """
    return f"G1 X{x:.3f}"


def _generate_ramp_entry(
    start_x: float,
    start_y: float,
    target_x: float,
    target_z: float,
    config: GCodeConfig,
) -> list[str]:
    """Generate a ramped entry into the material.

    Instead of a vertical plunge, the tool descends at an angle over a
    calculated XY distance. This prevents tool breakage on V-bits.

    If ramp_angle is 0 or very small, falls back to vertical plunge.

    Args:
        start_x: Starting X position.
        start_y: Starting Y position.
        target_x: X position where full depth is reached.
        target_z: Target Z depth (negative).
        config: G-code configuration.

    Returns:
        List of G-code lines for the ramp entry.
    """
    lines: list[str] = []

    if config.ramp_angle <= 0.1:
        # Vertical plunge (fallback)
        lines.append(
            f"G1 Z{target_z:.3f} F{config.plunge_rate:.0f}"
        )
        return lines

    # Calculate ramp geometry
    ramp_angle_rad = math.radians(config.ramp_angle)
    depth_to_cut = abs(target_z - config.start_z)
    ramp_length_mm = depth_to_cut / math.tan(ramp_angle_rad)

    # Clamp ramp length to reasonable bounds
    max_ramp = config.width_mm * 0.5
    ramp_length_mm = min(ramp_length_mm, max_ramp)

    # Calculate ramp end X position
    ramp_end_x = start_x + ramp_length_mm
    if target_x is not None and ramp_end_x > target_x:
        ramp_end_x = target_x

    # Emit ramp move
    lines.append(
        f"G1 X{ramp_end_x:.3f} Y{start_y:.3f} Z{target_z:.3f} "
        f"F{config.plunge_rate:.0f}"
    )

    return lines


# ============================================================
# HEADER / FOOTER
# ============================================================

def _generate_header(config: GCodeConfig) -> list[str]:
    """Generate the G-code preamble with setup commands and metadata.

    Args:
        config: G-code configuration.

    Returns:
        List of header lines.
    """
    strategy_name = config.carving_strategy.value
    lines = [
        "; =============================================",
        "; CNC Engraving -- Variable Depth Raster",
        "; Generated by PixelForge CNC v4.0",
        f"; Material: {config.material}",
        f"; Output: {config.width_mm}mm x {config.height_mm}mm",
        f"; Line spacing: {config.line_spacing_mm}mm",
        f"; Max depth: {config.max_depth}mm",
        f"; Strategy: {strategy_name}",
        f"; Ramp angle: {config.ramp_angle} deg",
        f"; Feed: {config.feed_rate}mm/min | RPM: {config.spindle_rpm}",
        "; =============================================",
        "",
        "T1 M6",
        "G17",
        "G21",
        "G90",
        f"G0 Z{config.safe_z:.3f}",
        f"G0 X0.000 Y0.000 S{config.spindle_rpm} M3",
        "G4 P2",
        "",
    ]
    return lines


def _generate_footer(config: GCodeConfig) -> list[str]:
    """Generate the G-code epilogue with retract and program end.

    Args:
        config: G-code configuration.

    Returns:
        List of footer lines.
    """
    return [
        "",
        f"G0 Z{config.safe_z:.3f}",
        "G0 X0.000 Y0.000",
        "M5",
        "M30",
    ]


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_gcode(
    depth_map: np.ndarray,
    config: GCodeConfig,
    progress_callback: ProgressCallback = None,
) -> tuple[str, GCodeStats]:
    """Generate optimized G-code from a grayscale depth map.

    This is the main entry point for G-code generation. It produces
    CNC G-code with rapid traversal over zero-depth areas, ramped
    tool entry, and configurable carving strategies.

    The depth map is a 2D NumPy array where pixel values (0-255) are
    mapped to Z-axis depth. Brighter pixels = less cutting, darker
    pixels = deeper cuts.

    Args:
        depth_map: Grayscale depth map (H, W) with values 0-255.
        config: Immutable G-code generation configuration.
        progress_callback: Optional callback(percent, message) for updates.

    Returns:
        Tuple of (gcode_string, GCodeStats).
    """
    rows, cols = depth_map.shape
    px_width = config.width_mm / cols if cols > 0 else 0.1

    stats = GCodeStats()
    out: list[str] = []

    # Header
    out.extend(_generate_header(config))
    stats.total_lines = len(out)
    stats.rapid_moves += 2  # initial G0 moves in header

    if progress_callback:
        progress_callback(0.0, "Building toolpath segments...")

    # Build all segments
    segments = _build_all_segments(depth_map, config)
    total_segments = len(segments)

    if progress_callback:
        progress_callback(0.1, f"Found {total_segments} cutting segments")

    # Track state for optimized output
    prev_z: float | None = None
    in_cut: bool = False
    current_x: float = 0.0
    current_y: float = 0.0
    current_z: float = config.safe_z

    for seg_idx, segment in enumerate(segments):
        # Progress update every 50 segments
        if progress_callback and seg_idx % 50 == 0:
            pct = 0.1 + 0.85 * (seg_idx / max(total_segments, 1))
            progress_callback(
                pct,
                f"Generating cuts: segment {seg_idx + 1}/{total_segments}",
            )

        # ── Rapid traversal: move to segment start ──────────
        start_col = segment.cols[0]
        target_x = start_col * px_width
        target_y = segment.y_mm

        # Retract to safe Z if currently cutting
        if in_cut:
            out.append(f"G0 Z{config.safe_z:.3f}")
            stats.rapid_moves += 1
            current_z = config.safe_z
            in_cut = False
            prev_z = None

        # Rapid move to segment start position
        out.append(_g0_rapid(target_x, target_y, config.safe_z))
        stats.rapid_moves += 1
        current_x = target_x
        current_y = target_y

        # Move to start Z (approach height)
        out.append(f"G0 Z{config.start_z:.3f}")
        stats.rapid_moves += 1
        current_z = config.start_z

        # ── Entry: ramp or plunge ───────────────────────────
        first_col = segment.cols[0]
        first_pix = int(depth_map[segment.row, first_col])
        first_depth = config.max_depth * (1.0 - first_pix / 255.0)

        if config.ramp_angle > 0.1:
            # Ramped entry
            ramp_lines = _generate_ramp_entry(
                start_x=target_x,
                start_y=target_y,
                target_x=target_x,
                target_z=first_depth,
                config=config,
            )
            out.extend(ramp_lines)
            stats.ramp_moves += 1
        else:
            # Vertical plunge
            out.append(
                f"G1 Z{first_depth:.3f} F{config.plunge_rate:.0f}"
            )
            stats.plunge_moves += 1

        prev_z = first_depth
        in_cut = True
        stats.cutting_moves += 1

        # ── Cut through all pixels in this segment ──────────
        for col_idx in segment.cols:
            pix = int(depth_map[segment.row, col_idx])
            depth = config.max_depth * (1.0 - pix / 255.0)
            x = col_idx * px_width

            z_changed = (prev_z is None) or (abs(depth - prev_z) > 0.002)

            if z_changed:
                out.append(_g1_xz(x, depth))
                prev_z = depth
            else:
                out.append(_g1_x(x))

            stats.cutting_moves += 1

        # Calculate cutting distance for this segment
        if len(segment.cols) > 1:
            dx = abs(segment.cols[-1] - segment.cols[0]) * px_width
            stats.cutting_distance_mm += dx

    # ── Retract and home ────────────────────────────────────
    out.extend(_generate_footer(config))
    stats.rapid_moves += 2

    # ── Final statistics ────────────────────────────────────
    stats.total_lines = len(out)

    # Estimate machining time
    cutting_time = stats.cutting_distance_mm / config.feed_rate * 60.0
    travel_time = stats.travel_distance_mm / config.rapid_feed * 60.0
    stats.estimated_time_seconds = cutting_time + travel_time

    if progress_callback:
        progress_callback(1.0, f"G-code complete: {stats.total_lines} lines")

    return "\n".join(out), stats
