"""Drawing geometry for each annotation kind, plus the normalized-box helpers the tutor uses.

All public functions take and return normalized coordinates (schemas.Box / Point); the
aspect-sensitive maths (ellipse padding, arrow directions, gaps) is done in pixels.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from app.perception.gpu import strip_latex
from app.perception.types import PerceptionResult
from app.schemas import Box, Geometry, Point, Region

PxBox = tuple[float, float, float, float]  # x0, y0, x1, y1 in pixels


# ---------------------------------------------------------------- normalized box helpers

def clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else float(v)


def clamp_box(b: Box) -> Box:
    """Intersect a box with the unit square (may become zero-sized when fully outside)."""
    x0, y0 = clamp01(b.x), clamp01(b.y)
    x1, y1 = clamp01(b.x + max(b.w, 0.0)), clamp01(b.y + max(b.h, 0.0))
    return Box(x=x0, y=y0, w=max(0.0, x1 - x0), h=max(0.0, y1 - y0))


def clamp_point(p: Point) -> Point:
    return Point(x=clamp01(p.x), y=clamp01(p.y))


def box_area(b: Box) -> float:
    return max(b.w, 0.0) * max(b.h, 0.0)


def intersection_area(a: Box, b: Box) -> float:
    iw = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    ih = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    return iw * ih if iw > 0 and ih > 0 else 0.0


def box_iou(a: Box, b: Box) -> float:
    inter = intersection_area(a, b)
    union = box_area(a) + box_area(b) - inter
    return inter / union if union > 0 else 0.0


def union_box(boxes: Iterable[Box]) -> Box | None:
    items = list(boxes)
    if not items:
        return None
    x0 = min(b.x for b in items)
    y0 = min(b.y for b in items)
    x1 = max(b.x + b.w for b in items)
    y1 = max(b.y + b.h for b in items)
    return Box(x=x0, y=y0, w=x1 - x0, h=y1 - y0)


def expand_box(b: Box, frac: float) -> Box:
    """Grow width and height by `frac` (0.15 = 15% larger) around the centre."""
    dw, dh = b.w * frac / 2, b.h * frac / 2
    return Box(x=b.x - dw, y=b.y - dh, w=b.w + 2 * dw, h=b.h + 2 * dh)


def box_center(b: Box) -> tuple[float, float]:
    return b.x + b.w / 2, b.y + b.h / 2


def contains(b: Box, x: float, y: float) -> bool:
    return b.x <= x <= b.x + b.w and b.y <= y <= b.y + b.h


def is_degenerate(b: Box | None, min_size: float = 0.002) -> bool:
    return b is None or not all(math.isfinite(v) for v in (b.x, b.y, b.w, b.h)) or b.w < min_size or b.h < min_size


# ---------------------------------------------------------------- pixel helpers

def _edge_px(b: PxBox, ux: float, uy: float) -> tuple[float, float]:
    """Point where the ray from the box centre in direction (ux, uy) leaves the box."""
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    hw, hh = (b[2] - b[0]) / 2, (b[3] - b[1]) / 2
    tx = hw / abs(ux) if abs(ux) > 1e-9 else math.inf
    ty = hh / abs(uy) if abs(uy) > 1e-9 else math.inf
    t = min(tx, ty)
    if not math.isfinite(t):
        return cx, cy
    return cx + ux * t, cy + uy * t


def _center_px(b: PxBox) -> tuple[float, float]:
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def _overlap_px(a: PxBox, b: PxBox) -> float:
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    return iw * ih if iw > 0 and ih > 0 else 0.0


def proportional_span(region: Region | None, span: str) -> Box | None:
    """Fallback span box for a single-line text region: slice the box by character offsets."""
    if region is None or not region.text or not span or region.kind != "text":
        return None
    text = strip_latex(region.text)  # spans index the OCR text, not an appended formula-OCR LaTeX
    if not text:
        return None
    i = text.lower().find(span.strip().lower())
    if i < 0:
        return None
    n = max(len(text), 1)
    b = region.box
    return Box(x=b.x + b.w * i / n, y=b.y, w=b.w * len(span.strip()) / n, h=b.h)


# ---------------------------------------------------------------- drawing geometry

class GeometryBuilder:
    """Turns grounded target boxes into drawing geometry for one lesson.

    Remembers every label box it placed so later labels avoid earlier ones.
    """

    def __init__(self, pr: PerceptionResult):
        self.pr = pr
        self.W = float(max(1, pr.width))
        self.H = float(max(1, pr.height))
        self.diag = math.hypot(self.W, self.H)
        self.placed: list[Box] = []
        texts = [r for r in pr.perception.regions if r.kind == "text"]
        self.text_boxes = [r.box for r in texts]  # labels keep off printed text
        heights = sorted(r.box.h * self.H for r in texts)
        # handwriting a little larger than the page's own text, so dense pages get smaller notes
        page_text = heights[len(heights) // 2] if heights else 0.045 * self.H / 1.25
        self.font_px = min(0.045 * self.H, 60.0, max(20.0, 1.25 * page_text))

    # ---- conversions
    def px(self, b: Box) -> PxBox:
        return b.x * self.W, b.y * self.H, (b.x + b.w) * self.W, (b.y + b.h) * self.H

    def norm(self, x0: float, y0: float, x1: float, y1: float) -> Box:
        return clamp_box(Box(x=x0 / self.W, y=y0 / self.H, w=(x1 - x0) / self.W, h=(y1 - y0) / self.H))

    def pt(self, x: float, y: float) -> Point:
        return clamp_point(Point(x=x / self.W, y=y / self.H))

    def ink_fraction_px(self, x0: float, y0: float, x1: float, y1: float) -> float:
        ink = self.pr.ink
        if ink is None or getattr(ink, "ndim", 0) != 2:
            return 0.0
        h, w = ink.shape
        sx, sy = w / self.W, h / self.H
        a, b = max(0, int(x0 * sx)), max(0, int(y0 * sy))
        c, d = min(w, int(math.ceil(x1 * sx))), min(h, int(math.ceil(y1 * sy)))
        if c <= a or d <= b:
            return 1.0  # outside the image counts as blocked
        return float(np.count_nonzero(ink[b:d, a:c])) / float((c - a) * (d - b))

    # ---- text
    def text_size(self, text: str) -> tuple[float, float]:
        """Normalized (w, h) of handwritten text (font sized from the page's own text height)."""
        font = self.font_px
        chars = max(2, len(text.strip()))
        w_px = 0.52 * font * chars + 0.5 * font
        h_px = 1.3 * font
        return min(0.95, w_px / self.W), min(0.5, h_px / self.H)

    # ---- kinds
    def circle(self, target: Box) -> Geometry:
        x0, y0, x1, y1 = self.px(target)
        w, h = x1 - x0, y1 - y0
        pad = max(10.0, 0.01 * max(self.W, self.H))
        ew, eh = max(w * 1.35, w + 2 * pad), max(h * 1.35, h + 2 * pad)
        if w > 3 * h:  # long text line: make the ellipse tall enough to clear the corners
            eh = max(eh, h * 1.6)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return Geometry(box=self.norm(cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2))

    def rect(self, target: Box) -> Geometry:
        x0, y0, x1, y1 = self.px(target)
        pad = max(8.0, 0.08 * min(x1 - x0, y1 - y0))
        return Geometry(box=self.norm(x0 - pad, y0 - pad, x1 + pad, y1 + pad))

    def span_box(self, ids: list[str], span: str | None) -> Box | None:
        """Box of `span` inside one of the text regions `ids` (perception's span finder first)."""
        if not span or not span.strip():
            return None
        for rid in ids:
            box = None
            try:
                box = self.pr.span_box(rid, span)
            except Exception:
                box = None
            if box is None:
                box = proportional_span(self.pr.region(rid), span)
            if box is not None and not is_degenerate(clamp_box(box), 1e-4):
                return clamp_box(box)
        return None

    def highlight(self, target: Box, ids: list[str], span: str | None) -> tuple[Geometry, bool]:
        sb = self.span_box(ids, span)
        x0, y0, x1, y1 = self.px(sb or target)
        px_, py_ = 3.0, max(2.0, 0.12 * (y1 - y0))
        return Geometry(box=self.norm(x0 - px_, y0 - py_, x1 + px_, y1 + py_)), sb is not None

    def underline(self, target: Box, ids: list[str], span: str | None) -> tuple[Geometry, bool]:
        sb = self.span_box(ids, span)
        x0, y0, x1, y1 = self.px(sb or target)
        gap = min(12.0, max(3.0, 0.15 * (y1 - y0)))
        ext = max(2.0, 0.02 * (x1 - x0))
        y = min(self.H - 1, y1 + gap)
        return Geometry(points=[self.pt(x0 - ext, y), self.pt(x1 + ext, y)]), sb is not None

    def label(self, target: Box, text: str, avoid: list[Box] | None = None) -> Geometry:
        w, h = self.text_size(text)
        lb = self.place(target, w, h, [*(avoid or []), target])
        self.placed.append(lb)
        return Geometry(box=clamp_box(target), label_box=lb, leader=self._leader(lb, target))

    def arrow(self, src: Box, dst: Box, text: str | None = None, avoid: list[Box] | None = None) -> Geometry:
        a, b = self.px(src), self.px(dst)
        (ax, ay), (bx, by) = _center_px(a), _center_px(b)
        d = math.hypot(bx - ax, by - ay)
        if d < 1.0:
            return self.pointer(dst, text, avoid)
        ux, uy = (bx - ax) / d, (by - ay) / d
        s = _edge_px(a, ux, uy)
        e = _edge_px(b, -ux, -uy)
        gap = max(6.0, 0.008 * self.diag)
        along = (e[0] - s[0]) * ux + (e[1] - s[1]) * uy
        if along > 3 * gap:
            s = (s[0] + ux * gap, s[1] + uy * gap)
            e = (e[0] - ux * gap, e[1] - uy * gap)
        elif along <= 0:  # boxes overlap along the centre line: connect the centres instead
            s, e = (ax, ay), (bx, by)
        return self._curve(s, e, text, [*(avoid or []), src, dst])

    def pointer(self, dst: Box, text: str | None = None, avoid: list[Box] | None = None) -> Geometry:
        """Arrow with only a destination: from a caption (or empty space) to the target's edge."""
        b = self.px(dst)
        cx, cy = _center_px(b)
        if text:
            w, h = self.text_size(text)
            lb = self.place(dst, w, h, [*(avoid or []), dst])
            self.placed.append(lb)
            lx, ly = _center_px(self.px(lb))
            d = math.hypot(cx - lx, cy - ly) or 1.0
            ux, uy = (cx - lx) / d, (cy - ly) / d
            s = _edge_px(self.px(lb), ux, uy)
            e = _edge_px(b, -ux, -uy)
            gap = max(5.0, 0.006 * self.diag)
            s, e = (s[0] + ux * gap, s[1] + uy * gap), (e[0] - ux * gap, e[1] - uy * gap)
            geo = self._curve(s, e, None, [])
            return Geometry(points=geo.points, label_box=lb)
        length = max(60.0, 0.09 * self.diag)
        best: tuple[float, tuple[float, float], tuple[float, float]] | None = None
        for k in range(8):
            ang = math.pi / 4 * k + math.pi / 8
            ux, uy = math.cos(ang), math.sin(ang)
            e = _edge_px(b, ux, uy)
            s = (e[0] + ux * length, e[1] + uy * length)
            if not (0 <= s[0] <= self.W and 0 <= s[1] <= self.H):
                continue
            ink = self.ink_fraction_px(min(s[0], e[0]), min(s[1], e[1]), max(s[0], e[0]) + 1, max(s[1], e[1]) + 1)
            if best is None or ink < best[0]:
                best = (ink, s, (e[0] + ux * 4, e[1] + uy * 4))
        if best is None:
            e = _edge_px(b, 0.0, -1.0)
            best = (0.0, (e[0], max(0.0, e[1] - length)), e)
        return self._curve(best[1], best[2], None, [])

    # ---- internals
    def _curve(self, s: tuple[float, float], e: tuple[float, float], text: str | None,
               avoid: list[Box]) -> Geometry:
        """Quadratic Bezier s -> e, bent ~12% of its length toward the side with less ink."""
        length = math.hypot(e[0] - s[0], e[1] - s[1])
        mx, my = (s[0] + e[0]) / 2, (s[1] + e[1]) / 2
        if length < 1e-6:
            c = (mx, my)
        else:
            nx, ny = -(e[1] - s[1]) / length, (e[0] - s[0]) / length
            off = 0.12 * length
            probe = max(off * 0.6, 12.0)
            options = []
            for sign in (1.0, -1.0):
                cx, cy = mx + sign * nx * off, my + sign * ny * off
                qx, qy = mx + sign * nx * off / 2, my + sign * ny * off / 2  # curve midpoint
                inside = 0 <= cx <= self.W and 0 <= cy <= self.H
                ink = self.ink_fraction_px(qx - probe, qy - probe, qx + probe, qy + probe)
                options.append((not inside, round(ink, 3), cy, (cx, cy)))
            c = min(options)[3]
        geo = Geometry(points=[self.pt(*s), self.pt(*c), self.pt(*e)])
        if text:
            qx, qy = 0.25 * s[0] + 0.5 * c[0] + 0.25 * e[0], 0.25 * s[1] + 0.5 * c[1] + 0.25 * e[1]
            anchor = self.norm(qx - 6, qy - 6, qx + 6, qy + 6)
            w, h = self.text_size(text)
            curve_boxes = [self.norm(px - 8, py - 8, px + 8, py + 8) for px, py in self._samples(s, c, e)]
            lb = self.place(anchor, w, h, [*avoid, *curve_boxes])
            self.placed.append(lb)
            geo.label_box = lb
        return geo

    @staticmethod
    def _samples(s, c, e, n: int = 7) -> list[tuple[float, float]]:
        out = []
        for i in range(1, n):
            t = i / n
            out.append(((1 - t) ** 2 * s[0] + 2 * (1 - t) * t * c[0] + t * t * e[0],
                        (1 - t) ** 2 * s[1] + 2 * (1 - t) * t * c[1] + t * t * e[1]))
        return out

    def path_boxes(self, geo: Geometry) -> list[Box]:
        """Small boxes along an arrow so later labels keep off the stroke."""
        if not geo.points or len(geo.points) != 3:
            return []
        s, c, e = ((p.x * self.W, p.y * self.H) for p in geo.points)
        return [self.norm(x - 8, y - 8, x + 8, y + 8) for x, y in [s, *self._samples(s, c, e), e]]

    def _leader(self, label: Box, target: Box) -> list[Point]:
        lb, tb = self.px(label), self.px(target)
        (lx, ly), (tx, ty) = _center_px(lb), _center_px(tb)
        d = math.hypot(tx - lx, ty - ly)
        if d < 1e-6:
            return [self.pt(lx, ly), self.pt(tx, ty)]
        ux, uy = (tx - lx) / d, (ty - ly) / d
        s = _edge_px(lb, ux, uy)
        e = _edge_px(tb, -ux, -uy)
        gap = max(4.0, 0.005 * self.diag)
        if (e[0] - s[0]) * ux + (e[1] - s[1]) * uy > 3 * gap:
            s = (s[0] + ux * gap * 0.5, s[1] + uy * gap * 0.5)
            e = (e[0] - ux * gap, e[1] - uy * gap)
        return [self.pt(*s), self.pt(*e)]

    def place(self, target: Box, w: float, h: float, avoid: list[Box] | None = None) -> Box:
        """Free-space placement via perception's map; own candidate search if that fails."""
        blockers = [*(avoid or []), *self.placed, *(b for b in self.text_boxes if b not in (avoid or []))]
        box = None
        try:
            box = self.pr.freespace.place_near(target, w, h, blockers)
        except Exception:
            box = None
        if box is not None:
            box = clamp_box(box)
            if is_degenerate(box, 1e-3):
                box = None
        return box if box is not None else self._fallback_place(target, w, h, blockers)

    def _fallback_place(self, target: Box, w: float, h: float, avoid: list[Box]) -> Box:
        w, h = min(w, 1.0), min(h, 1.0)
        gx, gy = 12 / self.W, 12 / self.H
        cx, cy = box_center(target)
        r, btm = target.x + target.w, target.y + target.h
        cands = [
            (r + gx, cy - h / 2), (target.x - gx - w, cy - h / 2),
            (cx - w / 2, target.y - gy - h), (cx - w / 2, btm + gy),
            (r + gx, target.y - gy - h), (target.x - gx - w, target.y - gy - h),
            (r + gx, btm + gy), (target.x - gx - w, btm + gy),
        ]
        best: tuple[float, Box] | None = None
        for i, (x, y) in enumerate(cands):
            x, y = min(max(x, 0.0), 1.0 - w), min(max(y, 0.0), 1.0 - h)
            box = Box(x=x, y=y, w=w, h=h)
            overlap = sum(intersection_area(box, a) for a in [target, *avoid]) / max(box_area(box), 1e-9)
            ink = self.ink_fraction_px(*self.px(box))
            score = 3.0 * ink + 5.0 * overlap + 0.05 * i
            if best is None or score < best[0]:
                best = (score, box)
        assert best is not None
        return clamp_box(best[1])
