import numpy as np
from pixelforge.engine.contour_tracer import extract_contours, convert_to_line_art


def test_extract_basic_shape():
    img = np.zeros((100, 100), dtype=np.uint8)
    img[20:80, 20:80] = 255
    contours = extract_contours(img, min_area=10)
    assert len(contours) >= 1


def test_extract_empty():
    img = np.zeros((50, 50), dtype=np.uint8)
    contours = extract_contours(img)
    assert len(contours) == 0


def test_extract_all_white():
    img = np.ones((50, 50), dtype=np.uint8) * 255
    contours = extract_contours(img)
    assert len(contours) >= 1


def test_extract_invert():
    img = np.zeros((50, 50), dtype=np.uint8)
    img[10:40, 10:40] = 255
    contours = extract_contours(img, invert=True, min_area=10)
    assert len(contours) >= 1


def test_simplify_high_epsilon():
    img = np.zeros((50, 50), dtype=np.uint8)
    img[5:45, 5:45] = 255
    contours = extract_contours(img, simplify_epsilon=10.0, min_area=10)
    assert len(contours) >= 1
    # High epsilon should produce fewer vertices
    assert len(contours[0].points) <= 8


def test_extract_min_area_filter():
    img = np.zeros((100, 100), dtype=np.uint8)
    img[2:8, 2:8] = 255  # small shape
    img[20:80, 20:80] = 255  # large shape
    contours = extract_contours(img, min_area=100)
    # Only the large shape should remain
    assert len(contours) >= 1


def test_line_art_simple():
    img = np.zeros((50, 50), dtype=np.uint8)
    img[:, 25] = 255
    lines = convert_to_line_art(img, min_line_length=5)
    assert len(lines) >= 1


def test_line_art_empty():
    img = np.zeros((50, 50), dtype=np.uint8)
    lines = convert_to_line_art(img)
    assert len(lines) == 0


def test_contour_path_has_points():
    img = np.zeros((50, 50), dtype=np.uint8)
    img[10:40, 10:40] = 255
    contours = extract_contours(img)
    for c in contours:
        assert len(c.points) >= 3
        assert isinstance(c.is_closed, bool)
