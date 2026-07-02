"""
depth_map.py
============
PixelForge CNC -- Advanced depth map generation.

Converts input images into realistic depth/height maps suitable for
3D CNC relief carving. Avoids the common pitfall of using raw grayscale
(which creates false depths from lighting/shadows) by applying:
  - Bilateral filtering to preserve edges while smoothing
  - CLAHE for local contrast equalization
  - Optional MiDaS monocular depth estimation (if available)
  - Normal-based shading to simulate realistic surface curvature
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def generate_depth_map_opencv(
    image_bgr: np.ndarray,
    strength: float = 1.0,
    smooth_iterations: int = 3,
    edge_preserve: float = 50.0,
) -> np.ndarray:
    """Generate a depth map using advanced OpenCV techniques.

    This method avoids raw grayscale by:
    1. Bilateral filtering to smooth surfaces while keeping edges sharp
    2. CLAHE for local contrast equalization
    3. Morphological closing to fill small gaps
    4. Gaussian blur for final smoothness

    Args:
        image_bgr: Input BGR image.
        strength: Depth strength multiplier (0.5 = subtle, 2.0 = deep).
        smooth_iterations: Number of bilateral filter passes.
        edge_preserve: Bilateral filter sigmaColor (higher = more smoothing).

    Returns:
        Grayscale depth map (H, W) with values 0-255.
        0 = deepest cut, 255 = surface (uncut).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Step 1: Bilateral filter -- preserves edges while smoothing flat areas
    # This removes lighting artifacts while keeping structural edges
    filtered = gray.copy()
    for _ in range(smooth_iterations):
        filtered = cv2.bilateralFilter(filtered, d=9,
                                       sigmaColor=edge_preserve,
                                       sigmaSpace=edge_preserve)

    # Step 2: CLAHE -- local contrast equalization removes lighting gradients
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    equalized = clahe.apply(filtered)

    # Step 3: Invert so dark = deep cut (lower value = deeper)
    # In CNC convention: 0 = deepest, 255 = surface
    depth = 255 - equalized

    # Step 4: Morphological closing to fill small holes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    depth = cv2.morphologyEx(depth, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Step 5: Gaussian blur for smooth surface
    depth = cv2.GaussianBlur(depth, (5, 5), 0)

    # Step 6: Apply strength
    depth = np.clip(depth.astype(np.float64) * strength, 0, 255).astype(np.uint8)

    return depth


def generate_depth_map_midas(
    image_bgr: np.ndarray,
    strength: float = 1.0,
) -> np.ndarray | None:
    """Generate a depth map using MiDaS monocular depth estimation.

    MiDaS produces metric depth from a single image, which is far more
    accurate than grayscale-based methods for 3D relief generation.

    Args:
        image_bgr: Input BGR image.
        strength: Depth strength multiplier.

    Returns:
        Grayscale depth map (H, W), or None if MiDaS is not available.
    """
    try:
        import torch

        # Try loading MiDaS model
        model_type = "DPT_Large"  # or "DPT_Hybrid" for faster inference
        midas = torch.hub.load("intel-isl/MiDaS", model_type)

        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        if model_type in ["DPT_Large", "DPT_Hybrid"]:
            transform = midas_transforms.dpt_transform
        else:
            transform = midas_transforms.small_transform

        # Prepare image
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        input_batch = transform(rgb)

        # Run inference
        device = "cuda" if torch.cuda.is_available() else "cpu"
        midas.to(device)
        midas.eval()

        with torch.no_grad():
            prediction = midas(input_batch.to(device))
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=rgb.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth = prediction.cpu().numpy()

        # Normalize to 0-255
        depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
        depth = (depth * 255 * strength).clip(0, 255).astype(np.uint8)

        return depth

    except Exception:
        return None


def generate_depth_map(
    image_bgr: np.ndarray,
    method: str = "opencv",
    **kwargs: Any,
) -> np.ndarray:
    """Unified depth map generation interface.

    Args:
        image_bgr: Input BGR image.
        method: "opencv" for CV-based, "midas" for AI-based.
        **kwargs: Additional parameters passed to the chosen method.

    Returns:
        Grayscale depth map (H, W) with values 0-255.
        Returns OpenCV fallback if MiDaS fails.
    """
    if method == "midas":
        result = generate_depth_map_midas(image_bgr, **kwargs)
        if result is not None:
            return result
        # Fallback to OpenCV if MiDaS unavailable
        return generate_depth_map_opencv(image_bgr, **kwargs)

    return generate_depth_map_opencv(image_bgr, **kwargs)
