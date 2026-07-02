"""
simulation.py
=============
PixelForge CNC -- Engraving preview simulation and image analysis.

Renders a realistic metallic engraving preview using multi-light rendering,
and provides smart CNC parameter recommendations based on image complexity.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from pixelforge.engine.material_presets import DEFAULT_MATERIAL, MATERIAL_PRESETS


def analyze_image(image_bgr: np.ndarray) -> dict[str, Any]:
    """Analyze image complexity and return smart CNC recommendations.

    Evaluates edge density, contrast, detail level, brightness distribution,
    and skin-tone presence to recommend optimal engraving parameters.

    Args:
        image_bgr: Input BGR image.

    Returns:
        Dict with analysis results and recommended settings.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Edge density (Canny)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.count_nonzero(edges) / (h * w)

    # Contrast (std deviation)
    contrast = np.std(gray) / 128.0

    # Detail level (Laplacian variance)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    detail_score = min(1.0, laplacian.var() / 500.0)

    # Brightness distribution
    mean_brightness = np.mean(gray) / 255.0

    # Skin tone detection for portrait mode
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    skin_lower = np.array([0, 20, 70], dtype=np.uint8)
    skin_upper = np.array([25, 150, 255], dtype=np.uint8)
    skin_mask = cv2.inRange(hsv, skin_lower, skin_upper)
    skin_ratio = np.count_nonzero(skin_mask) / (h * w)
    is_portrait = skin_ratio > 0.15

    # Classification
    if edge_density > 0.15:
        complexity = "high"
    elif edge_density > 0.05:
        complexity = "medium"
    else:
        complexity = "low"

    rec: dict[str, Any] = {
        "complexity": complexity,
        "edge_density": round(edge_density, 4),
        "contrast": round(contrast, 3),
        "detail_score": round(detail_score, 3),
        "is_portrait": is_portrait,
        "mean_brightness": round(mean_brightness, 3),
    }

    # Recommended spacing based on detail
    if detail_score > 0.6:
        rec["line_spacing_mm"] = 0.04
        rec["spacing_note"] = "High detail -- use ultra-fine spacing"
    elif detail_score > 0.3:
        rec["line_spacing_mm"] = 0.06
        rec["spacing_note"] = "Medium detail -- standard spacing"
    else:
        rec["line_spacing_mm"] = 0.10
        rec["spacing_note"] = "Low detail -- fast spacing OK"

    # Recommended depth based on contrast
    if contrast > 0.5:
        rec["max_depth"] = -0.10
        rec["depth_note"] = "High contrast -- moderate depth for definition"
    elif contrast > 0.3:
        rec["max_depth"] = -0.08
        rec["depth_note"] = "Medium contrast -- shallow depth"
    else:
        rec["max_depth"] = -0.06
        rec["depth_note"] = "Low contrast -- shallow depth, increase gamma"

    # Recommended mode
    if is_portrait:
        rec["recommended_mode"] = "portrait"
        rec["mode_note"] = "Face detected -- portrait mode recommended"
    elif edge_density > 0.1:
        rec["recommended_mode"] = "full"
        rec["mode_note"] = "Complex image -- use full image"
    else:
        rec["recommended_mode"] = "fit"
        rec["mode_note"] = "Simple image -- fit to dimensions"

    # Gamma recommendation
    if mean_brightness < 0.3:
        rec["gamma"] = 0.65
        rec["gamma_note"] = "Dark image -- brighten midtones"
    elif mean_brightness > 0.7:
        rec["gamma"] = 0.95
        rec["gamma_note"] = "Bright image -- slight darkening"
    else:
        rec["gamma"] = 0.80
        rec["gamma_note"] = "Balanced brightness"

    return rec


def get_smart_suggestions(analysis: dict[str, Any]) -> dict[str, Any]:
    """Derive recommended parameter values from image analysis.

    Returns a dict of suggested overrides without mutating any config.
    The caller decides whether and when to apply these to the actual
    settings. This replaces the old apply_smart_recommendations() which
    silently overwrote user-chosen values (material preset, manual mode
    selection) whenever smart_settings was enabled.

    Args:
        analysis: Output from analyze_image().

    Returns:
        Dict with keys: line_spacing_mm, max_depth, gamma, mode.
    """
    return {
        "line_spacing_mm": analysis["line_spacing_mm"],
        "max_depth": analysis["max_depth"],
        "gamma": analysis["gamma"],
        "mode": analysis["recommended_mode"],
    }


def render_engraving_preview(
    gray: np.ndarray,
    cfg: dict[str, Any],
    material_name: str | None = None,
) -> np.ndarray:
    """Render a high-quality metallic engraving simulation.

    Uses a multi-light rendering system with:
      - 3-point lighting (key, fill, rim)
      - Screen-space ambient occlusion
      - Schlick Fresnel approximation
      - Micro-surface brushing pattern
      - Edge-enhanced depth perception

    Args:
        gray: Grayscale depth map (H, W).
        cfg: Configuration dict with rendering parameters.
        material_name: Override material for rendering. Uses cfg default.

    Returns:
        BGR image (H, W, 3) simulating the engraved result.
    """
    mat_name = material_name or cfg.get("material", DEFAULT_MATERIAL)
    mat = MATERIAL_PRESETS.get(mat_name, MATERIAL_PRESETS[DEFAULT_MATERIAL])

    base_color = mat["base_color"].copy()
    spec_str = mat["specular_strength"]
    roughness = mat["roughness"]
    ambient_str = mat["ambient"]
    fresnel_str = mat["fresnel"]
    max_depth = abs(cfg.get("max_depth", -0.12))

    h, w = gray.shape
    depth_f = gray.astype(np.float64)

    depth_uint8 = np.clip(depth_f, 0, 255).astype(np.uint8)
    depth_f = cv2.edgePreservingFilter(
        depth_uint8, flags=1, sigma_s=30, sigma_r=0.3
    ).astype(np.float64)

    # Normalize depth: 0 = deepest cut, 1 = uncut surface
    depth_norm = depth_f / 255.0

    # Surface normals from depth (multi-scale)
    grad_x_fine = cv2.Sobel(depth_f, cv2.CV_64F, 1, 0, ksize=1)
    grad_y_fine = cv2.Sobel(depth_f, cv2.CV_64F, 0, 1, ksize=1)
    grad_x_coarse = cv2.Sobel(depth_f, cv2.CV_64F, 1, 0, ksize=5)
    grad_y_coarse = cv2.Sobel(depth_f, cv2.CV_64F, 0, 1, ksize=5)

    grad_x = grad_x_fine * 0.6 + grad_x_coarse * 0.4
    grad_y = grad_y_fine * 0.6 + grad_y_coarse * 0.4

    strength = max_depth * 15.0
    nx = grad_x * strength / 255.0
    ny = grad_y * strength / 255.0
    nz = np.ones_like(nx)

    mag = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-8
    nx /= mag
    ny /= mag
    nz /= mag

    # 3-Point Lighting System
    light_angle = np.radians(cfg.get("light_angle", 45.0))

    # Key light (main, warm)
    kx = np.cos(light_angle) * 0.7
    ky = np.sin(light_angle) * 0.7
    kz = 0.7
    kmag = np.sqrt(kx**2 + ky**2 + kz**2)
    kx, ky, kz = kx / kmag, ky / kmag, kz / kmag

    # Fill light (softer, opposite side)
    fx = np.cos(light_angle + np.pi) * 0.3
    fy = np.sin(light_angle + np.pi) * 0.3
    fz = 0.6
    fmag = np.sqrt(fx**2 + fy**2 + fz**2)
    fx, fy, fz = fx / fmag, fy / fmag, fz / fmag

    # Rim light (from behind/above)
    rx = np.cos(light_angle + np.pi / 4) * 0.2
    ry = np.sin(light_angle + np.pi / 4) * 0.2
    rz = 0.9
    rmag = np.sqrt(rx**2 + ry**2 + rz**2)
    rx, ry, rz = rx / rmag, ry / rmag, rz / rmag

    # Diffuse from each light
    diff_key = np.clip(nx * kx + ny * ky + nz * kz, 0, 1)
    diff_fill = np.clip(nx * fx + ny * fy + nz * fz, 0, 1)
    diff_rim = np.clip(nx * rx + ny * ry + nz * rz, 0, 1)

    diffuse = diff_key * 0.6 + diff_fill * 0.25 + diff_rim * 0.15

    # Specular (Blinn-Phong with Schlick Fresnel)
    hx_k, hy_k, hz_k = kx, ky, kz + 1.0
    hmag_k = np.sqrt(hx_k**2 + hy_k**2 + hz_k**2) + 1e-8
    hx_k, hy_k, hz_k = hx_k / hmag_k, hy_k / hmag_k, hz_k / hmag_k

    spec_angle_k = np.clip(nx * hx_k + ny * hy_k + nz * hz_k, 0, 1)
    shininess = (1.0 - roughness) * 200.0 + 20.0
    specular_k = np.power(spec_angle_k, shininess)

    cos_theta = np.clip(nz, 0, 1)
    fresnel = fresnel_str + (1.0 - fresnel_str) * np.power(1.0 - cos_theta, 5)

    specular = specular_k * spec_str * fresnel

    # Ambient Occlusion (screen-space approximation)
    kernel_size = max(3, min(15, h // 20))
    if kernel_size % 2 == 0:
        kernel_size += 1
    ao_blur = cv2.GaussianBlur(depth_f, (kernel_size, kernel_size), 0)
    ao = np.clip(ao_blur / (depth_f + 1e-8), 0, 1)
    ao = np.power(ao, 0.5)

    # Micro-surface brushing pattern
    brush_angle = light_angle + np.pi / 6
    brush_freq = 0.8
    y_coords = np.arange(h).reshape(-1, 1).astype(np.float64)
    brush_pattern = 1.0 + 0.015 * np.sin(y_coords * brush_freq + brush_angle)

    # Combine everything
    depth_darken = 0.3 + 0.7 * depth_norm

    edges = cv2.Canny(gray, 30, 100).astype(np.float64) / 255.0
    edges_blur = cv2.GaussianBlur(edges, (3, 3), 0)
    edge_highlight = 1.0 + edges_blur * 0.15

    result = np.zeros((h, w, 3), dtype=np.float64)
    for c in range(3):
        bc = base_color[c]
        channel = bc * ambient_str * ao
        channel += bc * diffuse * depth_darken * 0.7
        spec_on_surface = specular * (0.3 + 0.7 * depth_norm)
        channel += 255.0 * spec_on_surface * (1.0 - roughness * 0.5)
        channel *= edge_highlight
        channel *= brush_pattern
        result[:, :, c] = np.clip(channel, 0, 255)

    # Subtle scan lines
    spacing_px = max(1, int(cfg.get("line_spacing_mm", 0.08) * 100))
    if spacing_px > 2 and h > 10:
        scan = np.ones((h, 1), dtype=np.float64)
        for row in range(0, h, spacing_px):
            if row < h:
                scan[row, 0] = 1.03
                if row + 1 < h:
                    scan[row + 1, 0] = 0.97
        result *= scan[:, :, np.newaxis]

    # Surface noise (micro roughness)
    noise = np.random.normal(0, 0.6 * roughness, (h, w, 1))
    result += noise

    result = np.clip(result, 0, 255).astype(np.uint8)
    return result
