"""RapidOCR text lines (PP-OCRv4 det + rec on onnxruntime), as axis-aligned pixel boxes."""
from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

MIN_SCORE = 0.5

_engine = None
_lock = threading.Lock()


@dataclass
class OcrLine:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    score: float
    quad: list[list[float]]

    @property
    def box(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    @property
    def angle(self) -> float:
        """Baseline angle in degrees (positive = rising to the right in image coordinates)."""
        (ax, ay), (bx, by) = self.quad[0], self.quad[1]
        return float(np.degrees(np.arctan2(ay - by, bx - ax)))


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def warmup() -> None:
    """Load the ONNX models now (~1.5 s) instead of on the first request."""
    with _lock:
        _get_engine()


def run_ocr(rgb: np.ndarray, invert: bool = False) -> list[OcrLine]:
    """OCR an RGB uint8 image. `invert` helps light-on-dark slides. Thread-safe (one engine, locked)."""
    bgr = np.ascontiguousarray(rgb[..., ::-1])
    if invert:
        bgr = 255 - bgr
    h, w = rgb.shape[:2]
    with _lock:
        result, _ = _get_engine()(bgr, use_cls=False)  # the 180-degree classifier doubles the time
    lines: list[OcrLine] = []
    for quad, text, score in result or []:
        text = (text or "").strip()
        score = float(score)
        if not text or score < MIN_SCORE:
            continue
        if len(text) <= 2 and not any(ch.isalnum() for ch in text):
            continue
        pts = np.asarray(quad, dtype=np.float32).reshape(-1, 2)
        x0, y0 = np.clip(pts.min(axis=0), 0, None)
        x1, y1 = pts.max(axis=0)
        x1, y1 = min(float(x1), w), min(float(y1), h)
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        lines.append(OcrLine(float(x0), float(y0), float(x1), float(y1), text, score, pts.tolist()))
    return lines
