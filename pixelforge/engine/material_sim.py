"""
material_sim.py
===============
PixelForge CNC -- 2D Material Simulation for Preview.

Simulates how the engraving will appear on different materials:
  - Line-art mode: Canny edge detection blended onto material texture
  - Relief/emboss mode: 2D bump-mapping/shading overlaid on material
  - Support for Gold, Wood, Aluminum, Steel, Copper, and more
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from pixelforge.engine.material_presets import MATERIAL_PRESETS, DEFAULT_MATERIAL


# ============================================================
# MATERIAL TEXTURE GENERATORS
# ============================================================

def _generate_gold_texture(width: int, height: int) -> np.ndarray:
    """Generate a procedural gold brushed-metal texture.

    Args:
        width: Texture width in pixels.
        height: Texture height in pixels.

    Returns:
        BGR image of gold texture.
    """
    base = np.zeros((height, width, 3), dtype=np.float64)
    base[:, :] = [30, 180, 240]  # BGR gold base

    # Add brushed metal noise
    noise = np.random.normal(0, 8, (height, width, 1))
    # Directional brushing pattern
    y_coords = np.arange(height).reshape(-1, 1).astype(np.float64)
    brush = 1.0 + 0.02 * np.sin(y_coords * 0.5)
    base *= brush
    base += noise
    base += np.random.normal(0, 3, (height, width, 3))

    return np.clip(base, 0, 255).astype(np.uint8)


def _generate_wood_texture(width: int, height: int) -> np.ndarray:
    """Generate a procedural wood grain texture.

    Args:
        width: Texture width in pixels.
        height: Texture height in pixels.

    Returns:
        BGR image of wood texture.
    """
    base = np.zeros((height, width, 3), dtype=np.float64)
    base[:, :] = [40, 100, 160]  # BGR wood base (warm brown)

    # Wood grain lines
    y_coords = np.arange(height).reshape(-1, 1).astype(np.float64)
    grain = np.sin(y_coords * 0.15 + np.random.uniform(0, 6.28)) * 0.5 + 0.5
    grain_freq2 = np.sin(y_coords * 0.08 + 1.5) * 0.3 + 0.5
    combined_grain = (grain * 0.6 + grain_freq2 * 0.4)

    # Apply grain to all channels with slight color variation
    for c in range(3):
        variation = 1.0 + combined_grain * (0.15 if c == 2 else 0.1)
        base[:, :, c] *= variation

    # Add noise
    noise = np.random.normal(0, 5, (height, width, 3))
    base += noise

    return np.clip(base, 0, 255).astype(np.uint8)


def _generate_aluminum_texture(width: int, height: int) -> np.ndarray:
    """Generate a procedural aluminum brushed texture.

    Args:
        width: Texture width in pixels.
        height: Texture height in pixels.

    Returns:
        BGR image of aluminum texture.
    """
    base = np.zeros((height, width, 3), dtype=np.float64)
    base[:, :] = [200, 205, 215]  # BGR aluminum base

    # Brushed lines
    noise_h = np.random.normal(0, 4, (height, width, 1))
    y_coords = np.arange(height).reshape(-1, 1).astype(np.float64)
    brush = 1.0 + 0.01 * np.sin(y_coords * 1.2)
    base *= brush
    base += noise_h
    base += np.random.normal(0, 2, (height, width, 3))

    return np.clip(base, 0, 255).astype(np.uint8)


def _generate_steel_texture(width: int, height: int) -> np.ndarray:
    """Generate a procedural dark steel texture.

    Args:
        width: Texture width in pixels.
        height: Texture height in pixels.

    Returns:
        BGR image of steel texture.
    """
    base = np.zeros((height, width, 3), dtype=np.float64)
    base[:, :] = [140, 148, 158]  # BGR steel base

    noise = np.random.normal(0, 6, (height, width, 3))
    base += noise

    return np.clip(base, 0, 255).astype(np.uint8)


TEXTURE_GENERATORS = {
    "gold": _generate_gold_texture,
    "silver": _generate_gold_texture,  # Similar brushed metal
    "copper": _generate_gold_texture,
    "brass": _generate_gold_texture,
    "aluminum": _generate_aluminum_texture,
    "steel": _generate_steel_texture,
    "acrylic": _generate_aluminum_texture,
    "wood": _generate_wood_texture,
}


def get_material_texture(
    material_name: str, width: int, height: int
) -> np.ndarray:
    """Get a procedural texture for the specified material.

    Args:
        material_name: Key into MATERIAL_PRESETS.
        width: Texture width.
        height: Texture height.

    Returns:
        BGR texture image.
    """
    gen = TEXTURE_GENERATORS.get(material_name, _generate_gold_texture)
    return gen(width, height)


# ============================================================
# LINE-ART ENGRAVING SIMULATION
# ============================================================

def simulate_line_engraving(
    image_bgr: np.ndarray,
    material_name: str = "gold",
    edge_low: int = 50,
    edge_high: int = 150,
    blend_strength: float = 0.7,
) -> np.ndarray:
    """Simulate line-art engraving on a material surface.

    Uses Canny edge detection to extract lines, then blends them
    onto a procedural material texture to simulate how the engraving
    would look.

    Args:
        image_bgr: Input BGR image.
        material_name: Material to simulate on.
        edge_low: Canny lower threshold.
        edge_high: Canny upper threshold.
        blend_strength: How strongly edges darken the surface (0-1).

    Returns:
        BGR image simulating the line engraving.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Detect edges
    edges = cv2.Canny(gray, edge_low, edge_high)

    # Dilate edges slightly for visibility
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    edges = cv2.dilate(edges, kernel, iterations=1)

    # Get material texture
    h, w = gray.shape[:2]
    texture = get_material_texture(material_name, w, h)

    # Create edge mask (inverted: 1 = no edge, 0 = edge)
    edge_mask = (edges / 255.0)  # 1 where edge exists
    edge_mask = 1.0 - edge_mask  # invert: 1 = surface, 0 = edge

    # Darken edges on the texture
    result = texture.astype(np.float64)
    for c in range(3):
        result[:, :, c] *= (1.0 - blend_strength * edge_mask)

    return np.clip(result, 0, 255).astype(np.uint8)


# ============================================================
# RELIEF / BUMP-MAPPING SIMULATION
# ============================================================

def simulate_relief_engraving(
    depth_map: np.ndarray,
    material_name: str = "gold",
    light_angle: float = 45.0,
    bump_strength: float = 1.0,
    ambient: float = 0.3,
) -> np.ndarray:
    """Simulate embossed/relief engraving on a material surface.

    Uses 2D bump-mapping: computes surface normals from the depth map,
    then applies directional lighting to simulate how the relief would
    catch light on the actual material.

    Args:
        depth_map: Grayscale depth map (H, W) with values 0-255.
        material_name: Material to simulate on.
        light_angle: Light direction in degrees (0 = from right).
        bump_strength: How pronounced the bump effect appears.
        ambient: Ambient light level (0-1).

    Returns:
        BGR image simulating the relief engraving.
    """
    h, w = depth_map.shape

    # Get material texture
    texture = get_material_texture(material_name, w, h)

    # Compute surface normals from depth map using Sobel operators
    depth_f = depth_map.astype(np.float64) / 255.0

    grad_x = cv2.Sobel(depth_f, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(depth_f, cv2.CV_64F, 0, 1, ksize=3)

    # Scale normals by bump strength
    strength = bump_strength * 10.0
    nx = -grad_x * strength
    ny = -grad_y * strength
    nz = np.ones_like(nx)

    # Normalize
    mag = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-8
    nx /= mag
    ny /= mag
    nz /= mag

    # Compute light direction
    angle_rad = np.radians(light_angle)
    lx = np.cos(angle_rad)
    ly = np.sin(angle_rad)
    lz = 0.8

    # Normalize light
    lmag = np.sqrt(lx**2 + ly**2 + lz**2)
    lx, ly, lz = lx / lmag, ly / lmag, lz / lmag

    # Diffuse lighting (Lambertian)
    diffuse = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)

    # Specular (Blinn-Phong)
    hx, hy, hz = lx, ly, lz + 1.0
    hmag = np.sqrt(hx**2 + hy**2 + hz**2) + 1e-8
    hx, hy, hz = hx / hmag, hy / hmag, hz / hmag
    spec_angle = np.clip(nx * hx + ny * hy + nz * hz, 0, 1)
    specular = np.power(spec_angle, 32.0) * 0.4

    # Combine lighting
    lighting = ambient + (1.0 - ambient) * diffuse + specular

    # Apply lighting to texture
    result = texture.astype(np.float64)
    for c in range(3):
        result[:, :, c] *= lighting

    result += specular[:, :, np.newaxis] * 200.0  # White specular highlight

    return np.clip(result, 0, 255).astype(np.uint8)


# ============================================================
# UNIFIED SIMULATION INTERFACE
# ============================================================

def simulate_material_preview(
    image_bgr: np.ndarray,
    depth_map: np.ndarray | None = None,
    material_name: str = "gold",
    mode: str = "relief",
    **kwargs: Any,
) -> np.ndarray:
    """Generate a material simulation preview.

    Args:
        image_bgr: Original input image.
        depth_map: Optional pre-computed depth map. If None, generated
                   using OpenCV depth map method.
        material_name: Material to simulate.
        mode: "line" for line-art, "relief" for embossed/3D effect.
        **kwargs: Additional parameters for the simulation.

    Returns:
        BGR image simulating the engraving on the material.
    """
    if mode == "line":
        return simulate_line_engraving(
            image_bgr, material_name=material_name, **kwargs
        )

    # Relief mode
    if depth_map is None:
        from pixelforge.engine.depth_map import generate_depth_map
        depth_map = generate_depth_map(image_bgr)

    return simulate_relief_engraving(
        depth_map, material_name=material_name, **kwargs
    )
