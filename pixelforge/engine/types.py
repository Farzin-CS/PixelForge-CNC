from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class EngravingMode(Enum):
    RASTER_3D = "raster_3d"
    CONTOUR_2D = "contour_2d"
    LINE_ART = "line_art"


class CarvingStrategy(Enum):
    ZIGZAG = "zigzag"
    ONE_WAY_CLIMB = "climb"
    ONE_WAY_CONVENTIONAL = "conventional"


class CuttingDirection(Enum):
    LEFT_TO_RIGHT = "ltr"
    RIGHT_TO_LEFT = "rtl"


@dataclass(frozen=True)
class GCodeConfig:
    width_mm: float = 20.0
    height_mm: float = 25.0
    max_depth: float = -0.12
    safe_z: float = 2.0
    start_z: float = 0.3
    feed_rate: float = 300.0
    plunge_rate: float = 150.0
    spindle_rpm: int = 10000
    line_spacing_mm: float = 0.08
    skip_threshold: float = 0.005
    material: str = "gold"
    carving_strategy: CarvingStrategy = CarvingStrategy.ZIGZAG
    ramp_angle: float = 2.0
    ramp_height: float = 0.3
    rapid_feed: float = 5000.0
    engraving_mode: EngravingMode = EngravingMode.RASTER_3D
    contour_simplify_epsilon: float = 0.5
    min_contour_area: float = 1.0
    line_width_mm: float = 0.2
    contour_passes: int = 1
    lead_in_out: bool = True


@dataclass
class ToolpathSegment:
    cols: list[int]
    row: int
    y_mm: float
    direction: CuttingDirection


@dataclass
class ContourPath:
    points: list[tuple[float, float]]
    is_closed: bool
    depth_mm: float


@dataclass
class GCodeStats:
    total_lines: int = 0
    rapid_moves: int = 0
    cutting_moves: int = 0
    plunge_moves: int = 0
    ramp_moves: int = 0
    travel_distance_mm: float = 0.0
    cutting_distance_mm: float = 0.0
    estimated_time_seconds: float = 0.0
    contour_count: int = 0


ProgressCallback = Optional[Callable[[float, str], None]]
