"""Free-space map: where the page is empty, so labels and arrows never cover content."""
from __future__ import annotations

import math

import cv2
import numpy as np

from app.schemas import Box


class FreeSpace:
    """FreeSpaceMap over the ink mask, backed by an integral image (O(1) box sums)."""

    def __init__(self, ink: np.ndarray, margin_px: int | None = None):
        H, W = ink.shape
        self.W, self.H = W, H
        m = ink.astype(np.uint8)
        k = margin_px if margin_px is not None else max(3, int(round(min(W, H) * 0.006)))
        if k > 1:  # keep a little air between labels and the content they sit next to
            m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
        self.ii = cv2.integral(m, sdepth=cv2.CV_32S)

    def _px(self, b: Box) -> tuple[int, int, int, int]:
        x0 = int(math.floor(b.x * self.W))
        y0 = int(math.floor(b.y * self.H))
        x1 = int(math.ceil((b.x + b.w) * self.W))
        y1 = int(math.ceil((b.y + b.h) * self.H))
        return x0, y0, x1, y1

    def ink_fraction(self, box: Box) -> float:
        x0, y0, x1, y1 = self._px(box)
        total = max(1, (x1 - x0) * (y1 - y0))
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(self.W, x1), min(self.H, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            return 1.0
        ii = self.ii
        inside = int(ii[cy1, cx1] - ii[cy0, cx1] - ii[cy1, cx0] + ii[cy0, cx0])
        outside = total - (cx1 - cx0) * (cy1 - cy0)  # off-image area counts as blocked
        return min(1.0, (inside + outside) / total)

    def place_near(self, target: Box, w: float, h: float, avoid: list[Box] | None = None) -> Box:
        w, h = min(w, 0.98), min(h, 0.98)
        blockers = [target, *(avoid or [])]
        gx, gy = max(8 / self.W, 0.5 * h * self.H / self.W), max(8 / self.H, 0.5 * h)
        cx, cy = target.x + target.w / 2, target.y + target.h / 2
        right, bottom = target.x + target.w, target.y + target.h
        cands: list[tuple[float, float, float]] = []  # x, y, preference penalty
        for step, ring_pen in ((1.0, 0.0), (2.5, 0.15), (5.0, 0.35)):
            dx, dy = gx * step, gy * step
            cands += [
                (right + dx, cy - h / 2, ring_pen), (target.x - dx - w, cy - h / 2, ring_pen + 0.02),
                (cx - w / 2, target.y - dy - h, ring_pen + 0.01), (cx - w / 2, bottom + dy, ring_pen + 0.03),
                (right + dx, target.y - dy - h, ring_pen + 0.05), (target.x - dx - w, target.y - dy - h, ring_pen + 0.06),
                (right + dx, bottom + dy, ring_pen + 0.07), (target.x - dx - w, bottom + dy, ring_pen + 0.08),
                (right + dx, target.y, ring_pen + 0.04), (right + dx, bottom - h, ring_pen + 0.04),
                (target.x, target.y - dy - h, ring_pen + 0.04), (right - w, target.y - dy - h, ring_pen + 0.04),
                (target.x, bottom + dy, ring_pen + 0.05), (right - w, bottom + dy, ring_pen + 0.05),
            ]
        best: tuple[float, Box] | None = None
        for x, y, pref in cands:
            out_of_bounds = max(0.0, -x) + max(0.0, x + w - 1) + max(0.0, -y) + max(0.0, y + h - 1)
            x, y = min(max(x, 0.004), 1 - w - 0.004), min(max(y, 0.004), 1 - h - 0.004)
            b = Box(x=x, y=y, w=w, h=h)
            overlap = sum(_inter(b, a) for a in blockers) / max(w * h, 1e-9)
            dist = math.hypot(x + w / 2 - cx, y + h / 2 - cy)
            score = 4.0 * self.ink_fraction(b) + 6.0 * overlap + 0.8 * dist + pref + 2.0 * out_of_bounds
            if best is None or score < best[0]:
                best = (score, b)
        assert best is not None
        return best[1]


def _inter(a: Box, b: Box) -> float:
    w = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    h = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    return w * h if w > 0 and h > 0 else 0.0
