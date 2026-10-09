"""Image normalisation and the ink (content) masks every later stage builds on."""
from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps

from app import config

MAX_PIXELS = 40_000_000
MIN_SIDE = 32
MIN_LONG_SIDE = 1000


# ---------------------------------------------------------------- decoding


def prepare_image(data: bytes) -> Image.Image:
    """Decode upload bytes into an RGB image on white: EXIF-rotated, longest side in
    [~1000, MAX_IMAGE_SIDE]. Raises ValueError for unreadable, tiny or huge images."""
    if not data:
        raise ValueError("empty image data")
    try:
        img = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError as exc:
        raise ValueError("image is too large") from exc
    except Exception as exc:
        raise ValueError(f"unreadable image: {type(exc).__name__}") from exc
    w, h = img.size
    if w * h > MAX_PIXELS:
        raise ValueError(f"image is too large ({w}x{h}, max {MAX_PIXELS // 1_000_000} megapixels)")
    if min(w, h) < MIN_SIDE:
        raise ValueError(f"image is too small ({w}x{h}, min {MIN_SIDE} px per side)")
    try:
        img.seek(0)
        img.load()
        img = ImageOps.exif_transpose(img)
        img = _to_rgb_on_white(img)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"unreadable image: {type(exc).__name__}") from exc
    return _resize(img)


def _to_rgb_on_white(img: Image.Image) -> Image.Image:
    """Flatten any transparency onto white and return an 8-bit RGB image."""
    if img.mode in ("I", "I;16", "I;16B", "I;16L", "I;16N", "F"):
        arr = np.asarray(img).astype(np.float32)
        top = float(arr.max()) if arr.size else 0.0
        if top > 255:
            arr = arr / (65535.0 if top <= 65535 else top) * 255.0
        elif 0 < top <= 1.0:
            arr = arr * 255.0
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")
    has_alpha = img.mode in ("RGBA", "LA", "PA", "RGBa", "La") or "transparency" in img.info
    if has_alpha:
        rgba = img.convert("RGBA")
        canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        canvas.alpha_composite(rgba)
        return canvas.convert("RGB")
    return img.convert("RGB")


def _resize(img: Image.Image) -> Image.Image:
    w, h = img.size
    long_side = max(w, h)
    floor = min(MIN_LONG_SIDE, config.MAX_IMAGE_SIDE)
    if long_side > config.MAX_IMAGE_SIDE:
        scale = config.MAX_IMAGE_SIDE / long_side
    elif long_side < floor:
        scale = floor / long_side
    else:
        return img
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return img.resize(size, Image.LANCZOS)


# ---------------------------------------------------------------- ink analysis


@dataclass
class InkInfo:
    """Pixel-level content analysis of the processed image."""

    ink: np.ndarray  # bool HxW: anything that differs from the local background (text, strokes, fills)
    stroke: np.ndarray  # bool HxW: thin contrasting strokes only (outlines, text), no flat fills
    fill: np.ndarray  # bool HxW: smoothed colour difference, solid for filled areas
    dist: np.ndarray  # float32 HxW: Lab distance to the background model
    lab: np.ndarray  # uint8 HxWx3 Lab image
    bg: np.ndarray  # float32 (3,) dominant background colour (Lab)
    dark: bool  # light content on a dark background
    noise: float  # median distance of background pixels to the background model (0 for clean renders)
    threshold: float  # ink threshold on `dist`
    page: np.ndarray | None  # bool HxW page area of a photographed document, None = whole image

    @property
    def outside(self) -> np.ndarray | None:
        return None if self.page is None else ~self.page


def _odd(v: float, lo: int = 3) -> int:
    k = max(lo, int(round(v)))
    return k if k % 2 else k + 1


def _border_pixels(arr: np.ndarray, frac: float = 0.02) -> np.ndarray:
    h, w = arr.shape[:2]
    b = max(2, int(round(min(h, w) * frac)))
    parts = [arr[:b].reshape(-1, arr.shape[2]), arr[-b:].reshape(-1, arr.shape[2]),
             arr[:, :b].reshape(-1, arr.shape[2]), arr[:, -b:].reshape(-1, arr.shape[2])]
    return np.concatenate(parts, axis=0)


def remove_specks(mask: np.ndarray, min_area: int) -> np.ndarray:
    """Drop 8-connected components smaller than `min_area` pixels."""
    if min_area <= 1 or not mask.any():
        return mask
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    keep = stats[:, cv2.CC_STAT_AREA] >= min_area
    keep[0] = False
    return keep[labels]


def _border_spread(border: np.ndarray, bg: np.ndarray) -> float:
    return float(np.percentile(np.linalg.norm(border - bg, axis=1), 90))


def _page_mask(lab: np.ndarray) -> np.ndarray | None:
    """Photographed document on a desk: the paper region (bool HxW), else None.

    The paper is the largest connected area with the chroma of the image centre; it must leave a
    clearly different surround and have a tilted (non axis-aligned) outline, so digital slides with
    coloured bands are never mistaken for photos."""
    h, w = lab.shape[:2]
    scale = 360.0 / max(h, w)
    small = cv2.resize(lab, (max(8, int(w * scale)), max(8, int(h * scale))), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    f = small.astype(np.float32)
    centre = f[sh // 4: 3 * sh // 4, sw // 4: 3 * sw // 4].reshape(-1, 3)
    paper = np.median(centre, axis=0)
    chroma = np.sqrt((f[..., 1] - paper[1]) ** 2 + (f[..., 2] - paper[2]) ** 2)
    like = (chroma < 14) & (f[..., 0] > 0.45 * paper[0]) & (f[..., 0] < paper[0] + 60)
    k = _odd(min(sh, sw) * 0.06)
    like = cv2.morphologyEx(like.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(like, connectivity=4)
    if n <= 1:
        return None
    best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    contours, _ = cv2.findContours((labels == best).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    hull = cv2.convexHull(max(contours, key=cv2.contourArea))
    frac = cv2.contourArea(hull) / float(sh * sw)
    if not 0.2 <= frac <= 0.95:
        return None
    filled = np.zeros((sh, sw), np.uint8)
    cv2.fillConvexPoly(filled, hull, 1)
    outside = f[filled == 0]
    if outside.shape[0] < 50 or float(np.linalg.norm(np.median(outside, axis=0) - paper)) < 22:
        return None
    if not _tilted(hull, sw, sh):
        return None
    hull_full = (hull.astype(np.float32) / scale).astype(np.int32)
    page = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(page, hull_full, 1)
    erode = _odd(min(h, w) * 0.012)
    page = cv2.erode(page, cv2.getStructuringElement(cv2.MORPH_RECT, (erode, erode)))
    return page.astype(bool)


def _tilted(hull: np.ndarray, w: int, h: int) -> bool:
    """True when the long edges of the hull are not axis-aligned (a photo, not a layout band)."""
    peri = cv2.arcLength(hull, True)
    approx = cv2.approxPolyDP(hull, 0.02 * peri, True).reshape(-1, 2).astype(np.float32)
    if len(approx) < 3:
        return False
    tilts = []
    for i in range(len(approx)):
        p, q = approx[i], approx[(i + 1) % len(approx)]
        dx, dy = q - p
        length = float(np.hypot(dx, dy))
        on_border = (min(p[0], q[0]) <= 1 and max(p[0], q[0]) <= 1) or (min(p[1], q[1]) <= 1 and max(p[1], q[1]) <= 1)             or (min(p[0], q[0]) >= w - 2) or (min(p[1], q[1]) >= h - 2)
        if length < 0.15 * max(w, h) or on_border:
            continue
        ang = abs(np.degrees(np.arctan2(dy, dx))) % 90.0
        tilts.append(min(ang, 90.0 - ang))
    return bool(tilts) and float(np.median(tilts)) >= 0.8


def _background_model(lab: np.ndarray, page: np.ndarray | None) -> np.ndarray:
    """Low-frequency background colour per pixel (uint8 Lab): large-window median at low resolution,
    so lighting gradients become background while strokes, text and medium fills stay content.
    Off-page pixels (desk) are inpainted from the page first so they do not leak into it."""
    h, w = lab.shape[:2]
    scale = 96.0 / min(h, w)
    sw, sh = max(8, int(round(w * scale))), max(8, int(round(h * scale)))
    small = cv2.resize(lab, (sw, sh), interpolation=cv2.INTER_AREA)
    if page is not None:
        off = cv2.resize(page.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_AREA) < 1
        off = cv2.dilate(off.astype(np.uint8), np.ones((3, 3), np.uint8))
        small = cv2.inpaint(small, off, 5, cv2.INPAINT_TELEA)
    k = _odd(min(sw, sh) * 0.5, lo=5)
    med = cv2.medianBlur(small, k)
    med = cv2.GaussianBlur(med, (0, 0), 2.0)
    return cv2.resize(med, (w, h), interpolation=cv2.INTER_LINEAR)


def analyse_ink(rgb: np.ndarray) -> InkInfo:
    """Ink / stroke / fill masks: colour distance to the background (handles dark slides),
    adaptive threshold on lightness (handles uneven lighting), page area for photos."""
    h, w = rgb.shape[:2]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    lum = lab[..., 0]
    border = _border_pixels(lab).astype(np.float32)
    bg = np.median(border, axis=0)
    spread = _border_spread(border, bg)
    page = _page_mask(lab) if spread >= 8.0 else None
    if page is not None:
        bg = np.median(lab[page][::7].astype(np.float32), axis=0)
    labf = lab.astype(np.float32)
    if spread < 6.0 and page is None:
        diff = labf - bg
    else:
        diff = labf - _background_model(lab, page).astype(np.float32)
    dist = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
    dark = bool(bg[0] < 100)
    sample = dist[::3, ::3] if page is None else dist[page][::9]
    noise = float(np.median(sample)) if sample.size else 0.0

    thr = float(max(16.0, 8.0 + 3.0 * noise))
    min_side = min(h, w)
    speck = max(4, int(round(10 * (min_side / 1000.0) ** 2)))
    strong = dist > thr
    fill = cv2.GaussianBlur(dist, (0, 0), 1.5) > thr

    lp = (255 - lum) if dark else lum
    block = _odd(min_side / 28.0, lo=15)
    c = float(max(10.0, 2.0 * noise))
    stroke = cv2.adaptiveThreshold(lp, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, c) > 0
    stroke |= dist > max(60.0, 2.5 * thr)
    stroke &= dist > 0.5 * thr
    if page is not None:
        strong &= page
        fill &= page
        stroke &= page
    stroke = remove_specks(stroke, speck)
    ink = remove_specks(fill | stroke, speck)
    return InkInfo(ink=ink, stroke=stroke, fill=fill, dist=dist, lab=lab, bg=bg, dark=dark, noise=noise,
                   threshold=thr, page=page)


def otsu_threshold(values: np.ndarray) -> float:
    v = np.clip(values, 0, 255).astype(np.uint8).reshape(-1, 1)
    if v.size == 0:
        return 0.0
    t, _ = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return float(t)


def local_text_mask(crop_rgb: np.ndarray, floor: float = 22.0) -> np.ndarray:
    """Binarise a small crop (a text line) against its own background: the crop border's median
    colour; Otsu on the Lab distance with a floor so a blank crop stays blank."""
    if crop_rgb.size == 0:
        return np.zeros(crop_rgb.shape[:2], bool)
    lab = cv2.cvtColor(np.ascontiguousarray(crop_rgb), cv2.COLOR_RGB2LAB).astype(np.float32)
    ring = np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]], axis=0)
    bg = np.median(ring, axis=0)
    d = np.sqrt(((lab - bg) ** 2).sum(axis=2))
    t = max(floor, otsu_threshold(d))
    return d > t
