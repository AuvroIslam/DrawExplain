"""Phone photos of a page: find the paper quadrilateral and flatten it (perspective rectification).

Runs before OCR, so text lines are straight and boxes are axis-aligned; the student sees a clean
"scanned" page. Digital slides are never touched: the page must be a tilted quadrilateral that
clearly differs from its surroundings (see preprocess._page_mask).
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from app.perception.preprocess import _page_mask

MIN_PAGE_FRACTION = 0.25
GROW = 0.012  # _page_mask erodes the paper slightly; grow the quad back toward the paper edge


def _order(pts: np.ndarray) -> np.ndarray:
    """Corners as top-left, top-right, bottom-right, bottom-left."""
    s, d = pts.sum(axis=1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], np.float32)


def find_page_quad(rgb: np.ndarray) -> np.ndarray | None:
    h, w = rgb.shape[:2]
    page = _page_mask(cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB))
    if page is None:
        return None
    contours, _ = cv2.findContours(page.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    hull = cv2.convexHull(max(contours, key=cv2.contourArea))
    if cv2.contourArea(hull) < MIN_PAGE_FRACTION * w * h:
        return None
    peri = cv2.arcLength(hull, True)
    for eps in (0.01, 0.02, 0.03, 0.04, 0.06):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            break
    else:
        return None
    quad = _order(approx.reshape(4, 2).astype(np.float32))
    centre = quad.mean(axis=0)
    quad = centre + (quad - centre) * (1.0 + GROW)
    quad[:, 0] = np.clip(quad[:, 0], 0, w - 1)
    quad[:, 1] = np.clip(quad[:, 1], 0, h - 1)
    return quad


def rectify(image: Image.Image) -> tuple[Image.Image, np.ndarray | None]:
    """(flattened page, 3x3 homography from the input image to it), or (image, None) if not a photo."""
    rgb = np.asarray(image.convert("RGB"))
    quad = find_page_quad(rgb)
    if quad is None:
        return image, None
    tl, tr, br, bl = quad
    w = int(round(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))))
    h = int(round(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))))
    if w < 64 or h < 64:
        return image, None
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
    m = cv2.getPerspectiveTransform(quad, dst)
    flat = cv2.warpPerspective(rgb, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(flat), m


def transform_box(m: np.ndarray, box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Pixel box through a homography: bounding box of the 4 transformed corners."""
    x0, y0, x1, y1 = box
    pts = np.array([[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]], np.float32)
    out = cv2.perspectiveTransform(pts, m)[0]
    return float(out[:, 0].min()), float(out[:, 1].min()), float(out[:, 0].max()), float(out[:, 1].max())
