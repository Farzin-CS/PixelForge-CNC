"""
image_processor.py
==================
PixelForge CNC -- Image loading, preprocessing, and enhancement.

Handles image I/O, face detection cropping, background removal via rembg,
contrast/sharpness enhancement, and resizing for engraving resolution.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import cv2
import numpy as np

from pixelforge.engine.types import ProgressCallback


def load_image(image_path: str) -> np.ndarray:
    """Load an image from disk as a BGR NumPy array.

    Args:
        image_path: Absolute or relative path to the image file.

    Returns:
        BGR image array with shape (H, W, 3).

    Raises:
        FileNotFoundError: If the file cannot be opened by OpenCV.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Cannot open image: {image_path}")
    return image


def detect_and_crop_face(image_bgr: np.ndarray) -> np.ndarray:
    """Detect the largest face and crop with generous padding.

    Uses OpenCV's Haar cascade for frontal face detection. If no face
    is found, returns the original image unchanged.

    Args:
        image_bgr: Input BGR image.

    Returns:
        Cropped BGR image centered on the detected face, or the original.
    """
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            return image_bgr

        face_cascade = cv2.CascadeClassifier(cascade_path)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=5, minSize=(80, 80)
        )

        if len(faces) == 0:
            return image_bgr

        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        H, W = image_bgr.shape[:2]
        pad_x = int(w * 0.45)
        pad_y_top = int(h * 0.55)
        pad_y_bot = int(h * 0.30)

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y_top)
        x2 = min(W, x + w + pad_x)
        y2 = min(H, y + h + pad_y_bot)

        return image_bgr[y1:y2, x1:x2]
    except Exception:
        return image_bgr


def center_crop(image_bgr: np.ndarray) -> np.ndarray:
    """Crop the image to a square from its center.

    Args:
        image_bgr: Input BGR image.

    Returns:
        Square-cropped BGR image.
    """
    h, w = image_bgr.shape[:2]
    size = min(h, w)
    x1 = (w - size) // 2
    y1 = (h - size) // 2
    return image_bgr[y1 : y1 + size, x1 : x1 + size]


def fit_to_dimensions(
    image_bgr: np.ndarray, target_w: float, target_h: float
) -> np.ndarray:
    """Resize image to fit within target dimensions, preserving aspect ratio.

    Args:
        image_bgr: Input BGR image.
        target_w: Target width in pixels.
        target_h: Target height in pixels.

    Returns:
        Resized BGR image fitting within the target box.
    """
    h, w = image_bgr.shape[:2]
    target_ratio = target_w / target_h
    img_ratio = w / h
    if img_ratio > target_ratio:
        new_w = int(target_w)
        new_h = int(new_w / img_ratio)
    else:
        new_h = int(target_h)
        new_w = int(new_h * img_ratio)
    return cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def preprocess_image(image_bgr: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Apply mode-based preprocessing (portrait crop, center crop, fit).

    Args:
        image_bgr: Input BGR image.
        cfg: Configuration dict with 'mode', 'width_mm', 'height_mm'.

    Returns:
        Preprocessed BGR image.
    """
    mode = cfg.get("mode", "full")
    if mode == "portrait":
        return detect_and_crop_face(image_bgr)
    elif mode == "center":
        return center_crop(image_bgr)
    elif mode == "fit":
        return fit_to_dimensions(image_bgr, cfg["width_mm"], cfg["height_mm"])
    return image_bgr


def remove_background(
    image_bgr: np.ndarray, progress_callback: ProgressCallback = None
) -> tuple[np.ndarray, bool]:
    """Remove background using rembg with BiRefNet model.

    Composites the foreground onto a white background for clean engraving.

    Args:
        image_bgr: Input BGR image.
        progress_callback: Optional callback for status messages.

    Returns:
        Tuple of (result_image, success_bool).
    """

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback(0.0, msg)

    try:
        _log("Loading AI model (first run downloads ~200MB)...")
        from rembg import remove, new_session
        from PIL import Image as PILImage

        _log("Initializing BiRefNet model...")
        try:
            import onnxruntime
            _providers = ["CUDAExecutionProvider", "CoreMLExecutionProvider", "CPUExecutionProvider"]
            available = [p for p in _providers if p in onnxruntime.get_available_providers()]
            session = new_session("birefnet-portrait", providers=available)
        except Exception:
            session = new_session("birefnet-portrait")

        _log("Processing image with AI...")
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(rgb)
        output = remove(pil_img, session=session)

        _log("Compositing on white background...")
        bg = PILImage.new("RGBA", output.size, (255, 255, 255, 255))
        bg.paste(output, mask=output.split()[3])
        result = np.array(bg.convert("RGB"))
        result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

        _log("Background removed successfully")
        return result_bgr, True

    except ImportError:
        _log("rembg not installed -- pip install rembg[cpu]")
        return image_bgr, False
    except Exception as e:
        _log(f"Background removal failed: {e}")
        return image_bgr, False


def enhance_image(image_bgr: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    """Apply contrast enhancement, bilateral filtering, sharpening, and gamma.

    Converts the image to grayscale and applies a chain of enhancements
    controlled by the config flags.

    Args:
        image_bgr: Input BGR image.
        cfg: Configuration dict with enhancement flags and gamma value.

    Returns:
        Enhanced grayscale image with shape (H, W).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    if cfg.get("contrast_enhance", True):
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    if cfg.get("bilateral_filter", True):
        gray = cv2.bilateralFilter(gray, d=9, sigmaColor=80, sigmaSpace=80)

    if cfg.get("sharpen_edges", True):
        blurred = cv2.GaussianBlur(gray, (0, 0), 2.0)
        gray = cv2.addWeighted(gray, 1.4, blurred, -0.4, 0)
        gray = np.clip(gray, 0, 255).astype(np.uint8)

    gamma = cfg.get("gamma", 0.85)
    inv_gamma = 1.0 / max(gamma, 0.01)
    table = np.array(
        [((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype=np.uint8
    )
    gray = cv2.LUT(gray, table)

    if cfg.get("invert", False):
        gray = 255 - gray

    return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)


def resize_to_engraving(
    gray: np.ndarray, width_mm: float, height_mm: float, spacing_mm: float
) -> np.ndarray:
    """Resize grayscale image to match the target engraving resolution.

    The number of rows is determined by height_mm / spacing_mm, and
    columns are scaled proportionally.

    Args:
        gray: Input grayscale image.
        width_mm: Target output width in mm.
        height_mm: Target output height in mm.
        spacing_mm: Line spacing in mm (determines row count).

    Returns:
        Resized grayscale image at engraving resolution.
    """
    target_rows = max(1, int(height_mm / spacing_mm))
    h, w = gray.shape
    target_cols = max(1, int(target_rows * (w / h)))
    return cv2.resize(
        gray, (target_cols, target_rows), interpolation=cv2.INTER_LANCZOS4
    )
