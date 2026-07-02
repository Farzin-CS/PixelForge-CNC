from __future__ import annotations

import cv2
import numpy as np

from pixelforge.engine.types import ContourPath, ProgressCallback


def extract_contours(
    gray: np.ndarray,
    simplify_epsilon: float = 0.5,
    min_area: float = 1.0,
    invert: bool = False,
    detail_level: float = 0.5,
    progress_callback: ProgressCallback = None,
) -> list[ContourPath]:
    if progress_callback:
        progress_callback(0.0, "Thresholding image...")

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if invert:
        binary = 255 - binary

    low = int(20 + (1.0 - detail_level) * 60)
    high = int(80 + (1.0 - detail_level) * 120)
    edges = cv2.Canny(blurred, low, high)
    edge_mask = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    binary = cv2.bitwise_or(binary, edge_mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

    if progress_callback:
        progress_callback(0.2, "Finding contours...")

    contours, _ = cv2.findContours(
        binary.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )

    if progress_callback:
        progress_callback(0.4, f"Processing {len(contours)} contours...")

    h, w = binary.shape[:2]
    result: list[ContourPath] = []
    seen: set[tuple[int, ...]] = set()

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        x, y, bw, bh = cv2.boundingRect(contour)
        if bw >= w - 2 and bh >= h - 2:
            continue

        key = (x // 4, y // 4, bw // 4, bh // 4)
        if key in seen:
            continue
        seen.add(key)

        perimeter = cv2.arcLength(contour, True)
        detail_factor = 2.0 - detail_level * 1.8
        eps = max(0.3, detail_factor * perimeter * 0.01) if perimeter > 0 else simplify_epsilon
        simplified = cv2.approxPolyDP(contour, eps, True)

        points = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]
        if len(points) < 3:
            continue

        if len(points) > 6:
            xs = np.array([p[0] for p in points], dtype=np.float64)
            ys = np.array([p[1] for p in points], dtype=np.float64)
            ksize = min(5, len(points) if len(points) % 2 == 1 else len(points) - 1)
            if ksize >= 3:
                xs = cv2.GaussianBlur(xs, (1, ksize), 0.5).ravel()
                ys = cv2.GaussianBlur(ys, (1, ksize), 0.5).ravel()
                points = [(float(xs[i]), float(ys[i])) for i in range(len(points))]

        is_closed = perimeter > 0
        result.append(ContourPath(points=points, is_closed=is_closed, depth_mm=0.0))

        if progress_callback and len(result) % 50 == 0:
            progress_callback(
                0.4 + 0.3 * (len(result) / max(len(result) + 1, 1)),
                f"Processing contour {len(result)}",
            )

    if progress_callback:
        progress_callback(0.7, f"Found {len(result)} contours")

    def _contour_area(c: ContourPath) -> float:
        xs = [p[0] for p in c.points]
        ys = [p[1] for p in c.points]
        return (max(xs) - min(xs)) * (max(ys) - min(ys)) if xs and ys else 0

    result.sort(key=_contour_area, reverse=True)
    return result


def _simplify_polyline(
    points: list[tuple[float, float]], epsilon: float
) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    pts = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
    simplified = cv2.approxPolyDP(pts, epsilon, False)
    return [(float(p[0][0]), float(p[0][1])) for p in simplified]


def convert_to_line_art(
    gray: np.ndarray,
    edge_low: int = 50,
    edge_high: int = 150,
    min_line_length: int = 10,
    detail_level: float = 0.5,
    progress_callback: ProgressCallback = None,
) -> list[ContourPath]:
    if progress_callback:
        progress_callback(0.0, "Detecting lines...")

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    block = int(31 - detail_level * 24)
    if block % 2 == 0:
        block += 1
    block = max(3, min(31, block))
    c_val = int(10 - detail_level * 8)
    c_val = max(2, min(10, c_val))

    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block, c_val,
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    if progress_callback:
        progress_callback(0.2, "Thinning edges...")

    try:
        skeleton = cv2.ximgproc.thinning(clean)
        if skeleton is None:
            skeleton = clean
    except Exception:
        skeleton = clean

    if progress_callback:
        progress_callback(0.4, "Tracing paths...")

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skeleton, 8)

    min_len = max(3, int(min_line_length * (0.5 + detail_level)))

    result: list[ContourPath] = []
    for label_id in range(1, num_labels):
        if stats[label_id, cv2.CC_STAT_AREA] < min_len:
            continue

        ys, xs = np.where(labels == label_id)
        if len(xs) < 2:
            continue

        coords = list(zip(xs.tolist(), ys.tolist()))

        perim = stats[label_id, cv2.CC_STAT_AREA]
        eps = max(0.2, perim * 0.02 * (2.0 - detail_level))
        coords = _simplify_polyline(coords, eps)

        if len(coords) < 2:
            continue

        result.append(ContourPath(points=coords, is_closed=False, depth_mm=0.0))

        if progress_callback and label_id % 50 == 0:
            progress_callback(
                0.4 + 0.4 * (label_id / max(num_labels, 1)),
                f"Tracing line {label_id}/{num_labels}",
            )

    if progress_callback:
        progress_callback(0.8, f"Found {len(result)} line segments")

    return result
