"""Region proposals: OCR text lines, closed shapes, figures and text blocks, ids in reading order.

Shapes are found as HOLES of the closed outline mask (RETR_CCOMP), so boxes joined by connector
lines still come out one by one; the outline thickness is measured outward from each hole so the
box hugs the shape's outer edge. Solid filled shapes come from the fill mask. Whatever ink is left
after removing text and shapes becomes figures (icons, drawings, arrows, chart parts).
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.perception.preprocess import InkInfo
from app.schemas import Box, Region

PxBox = tuple[float, float, float, float]  # x0, y0, x1, y1 in pixels

MAX_REGIONS = 80
MIN_SHAPE_AREA = 0.0015  # fraction of the image area
MAX_SHAPE_AREA = 0.70
MIN_FIGURE_AREA = 0.0012
MIN_FIGURE_LENGTH = 0.06  # long thin things (arrows) are kept even when their box is small


@dataclass
class TextLine:
    box: PxBox
    text: str
    score: float


@dataclass(eq=False)
class _Proto:
    kind: str
    box: PxBox
    text: str | None = None
    score: float = 1.0
    source: str = "opencv"
    parent: "_Proto | None" = None
    rid: str = ""
    contour: np.ndarray | None = None  # hole contour of an outlined shape (its inner edge)
    thick: float = 0.0  # outline thickness in pixels


# ---------------------------------------------------------------- box maths (pixels)

def _area(b: PxBox) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _inter(a: PxBox, b: PxBox) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _iou(a: PxBox, b: PxBox) -> float:
    i = _inter(a, b)
    u = _area(a) + _area(b) - i
    return i / u if u > 0 else 0.0


def _inside(inner: PxBox, outer: PxBox, frac: float) -> bool:
    a = _area(inner)
    return a > 0 and _inter(inner, outer) >= frac * a


# ---------------------------------------------------------------- shapes

def _ray_thickness(mask: np.ndarray, x: int, y: int, dx: int, dy: int, limit: int) -> int | None:
    """Run length of mask pixels starting next to (x, y) going (dx, dy); None if no stroke there."""
    H, W = mask.shape
    n, cx, cy = 0, x + dx, y + dy
    while 0 <= cx < W and 0 <= cy < H and mask[cy, cx] and n < limit:
        n, cx, cy = n + 1, cx + dx, cy + dy
    return n or None


def _outline_shapes(closed: np.ndarray, W: int, H: int, k: int) -> list[_Proto]:
    img_area = float(W * H)
    contours, hier = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return []
    limit = 6 * k + 12
    out: list[_Proto] = []
    for i, c in enumerate(contours):
        if hier[0][i][3] < 0:  # an outer boundary; shapes are the holes
            continue
        x, y, w, h = cv2.boundingRect(c)
        if min(w, h) < 8 or not MIN_SHAPE_AREA * img_area <= w * h <= MAX_SHAPE_AREA * img_area:
            continue
        if cv2.contourArea(c) < 0.45 * w * h:  # irregular pocket between connectors, not a shape
            continue
        # the hole's edge is the ring's inner edge: walk outward at 3 points per side and keep the
        # thinnest reading, so a connector line leaving the shape cannot stretch the box
        xs = [x + w // 4, x + w // 2, x + 3 * w // 4]
        ys = [y + h // 4, y + h // 2, y + 3 * h // 4]
        rays = [
            [_ray_thickness(closed, px, y, 0, -1, limit) for px in xs],
            [_ray_thickness(closed, px, y + h - 1, 0, 1, limit) for px in xs],
            [_ray_thickness(closed, x, py, -1, 0, limit) for py in ys],
            [_ray_thickness(closed, x + w - 1, py, 1, 0, limit) for py in ys],
        ]
        sides = [min((v for v in side if v), default=None) for side in rays]
        found = [s for s in sides if s]
        t = float(np.median(found)) if found else 2.0
        top, bottom, left, right = (min(s, 2 * t) if s else t for s in sides)
        box = (max(0.0, x - left), max(0.0, y - top), min(float(W), x + w + right), min(float(H), y + h + bottom))
        out.append(_Proto("shape", box, score=0.9, contour=c, thick=t))
    return out


def _filled_shapes(ink: InkInfo, lines: list[TextLine], W: int, H: int) -> list[_Proto]:
    img_area = float(W * H)
    # opening removes connector lines and text strokes, so touching filled boxes separate
    k = max(5, int(round(0.012 * min(W, H))))
    solid = cv2.morphologyEx(ink.fill.astype(np.uint8), cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    n, _, stats, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
    out: list[_Proto] = []
    for j in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[j])
        if min(w, h) < 10 or not MIN_SHAPE_AREA * img_area <= w * h <= MAX_SHAPE_AREA * img_area:
            continue
        if area < 0.6 * w * h:  # solid shapes only; rings and text are handled elsewhere
            continue
        box = (float(x), float(y), float(x + w), float(y + h))
        if any(_iou(box, ln.box) > 0.5 or _inside(box, ln.box, 0.6) for ln in lines):  # text blobs
            continue
        out.append(_Proto("shape", box, score=0.8))
    return out


def _edges(ink: InkInfo, W: int, H: int) -> np.ndarray:
    """Colour edges (Canny on L, a and b), so outlined AND filled shapes both become closed rings."""
    blur = cv2.GaussianBlur(ink.lab, (0, 0), 1.0 if ink.noise < 2 else 1.6)
    lo, hi = (30, 90) if ink.noise < 2 else (40, 110)
    e = cv2.Canny(blur[..., 0], lo, hi)
    for ch in (1, 2):  # chroma edges: a purple disc on beige has little lightness contrast
        e |= cv2.Canny(blur[..., ch], lo // 2, hi // 2)
    if ink.page is not None:
        e[~ink.page] = 0
    return e


def _drop_pockets(shapes: list[_Proto]) -> list[_Proto]:
    """A 'shape' whose border cuts through >= 2 smaller shapes is the empty pocket enclosed by
    connectors between them (graph faces, flowchart loops), not a drawn shape."""
    out = []
    for s in shapes:
        cut = sum(1 for o in shapes if o is not s and _area(o.box) < _area(s.box)
                  and 0 < _inter(o.box, s.box) < 0.9 * _area(o.box))
        if cut < 2:
            out.append(s)
    return out


def _dedupe(protos: list[_Proto], thr: float) -> list[_Proto]:
    """Drop near-duplicates; outline shapes (they keep their contour) win over filled ones."""
    kept: list[_Proto] = []
    for p in sorted(protos, key=lambda q: (-q.score, -_area(q.box))):
        if all(_iou(p.box, q.box) <= thr for q in kept):
            kept.append(p)
    return kept


# ---------------------------------------------------------------- figures

def _figures(ink: InkInfo, lines: list[TextLine], shapes: list[_Proto], W: int, H: int) -> list[_Proto]:
    img_area = float(W * H)
    m = ink.ink.astype(np.uint8).copy()
    for s in shapes:  # erase outlines only, so things drawn inside a shape (organelles, icons) remain
        if s.contour is not None:
            cv2.drawContours(m, [s.contour], -1, 0, thickness=int(round(2 * s.thick + 5)))
        else:
            x0, y0, x1, y1 = (int(round(v)) for v in s.box)
            m[max(0, y0 - 2):min(H, y1 + 3), max(0, x0 - 2):min(W, x1 + 3)] = 0
    for b in [ln.box for ln in lines]:
        x0, y0, x1, y1 = (int(round(v)) for v in b)
        m[max(0, y0 - 2):min(H, y1 + 3), max(0, x0 - 2):min(W, x1 + 3)] = 0
    if not m.any():
        return []
    d = max(3, int(round(min(W, H) * 0.008)))
    merged = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(merged, connectivity=8)
    out: list[_Proto] = []
    for j in range(1, n):
        x, y, w, h, _ = (int(v) for v in stats[j])
        long_thin = max(w, h) >= MIN_FIGURE_LENGTH * max(W, H)
        if w * h < MIN_FIGURE_AREA * img_area and not long_thin:
            continue
        if w * h > 0.85 * img_area:
            continue
        ys, xs = np.nonzero((labels[y:y + h, x:x + w] == j) & (m[y:y + h, x:x + w] > 0))
        if xs.size < 12:
            continue
        box = (float(x + xs.min()), float(y + ys.min()), float(x + xs.max() + 1), float(y + ys.max() + 1))
        out.append(_Proto("figure", box, score=0.6))
    return out


# ---------------------------------------------------------------- text blocks

def _blocks(lines: list[_Proto], W: int) -> list[_Proto]:
    """Groups of >= 2 vertically adjacent, aligned lines with the same container."""
    order = sorted(lines, key=lambda p: p.box[1])
    parent_of: dict[int, int] = {}

    def find(i: int) -> int:
        while parent_of.get(i, i) != i:
            i = parent_of[i]
        return i

    for i, a in enumerate(order):
        ah = a.box[3] - a.box[1]
        for j in range(i - 1, -1, -1):
            b = order[j]
            bh = b.box[3] - b.box[1]
            gap = a.box[1] - b.box[3]
            if gap > 1.2 * max(ah, bh):
                if a.box[1] - b.box[1] > 4 * max(ah, bh):
                    break
                continue
            if b.parent is not a.parent or max(ah, bh) > 1.7 * min(ah, bh):
                continue
            left_aligned = abs(a.box[0] - b.box[0]) <= 0.03 * W
            overlap = min(a.box[2], b.box[2]) - max(a.box[0], b.box[0])
            if left_aligned or overlap >= 0.5 * min(a.box[2] - a.box[0], b.box[2] - b.box[0]):
                parent_of[find(i)] = find(j)
                break
    groups: dict[int, list[_Proto]] = {}
    for i, p in enumerate(order):
        groups.setdefault(find(i), []).append(p)
    out: list[_Proto] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        box = (min(m.box[0] for m in members), min(m.box[1] for m in members),
               max(m.box[2] for m in members), max(m.box[3] for m in members))
        block = _Proto("text_block", box, "\n".join(m.text or "" for m in members),
                       float(np.mean([m.score for m in members])), "merged", members[0].parent)
        for m in members:
            m.parent = block
        out.append(block)
    return out


# ---------------------------------------------------------------- assembly

def _smallest_container(p: _Proto, shapes: list[_Proto], frac: float) -> _Proto | None:
    best = None
    for s in shapes:
        if s is p or _area(s.box) <= _area(p.box) or not _inside(p.box, s.box, frac):
            continue
        if best is None or _area(s.box) < _area(best.box):
            best = s
    return best


def build_regions(ink: InkInfo, lines: list[TextLine], W: int, H: int) -> list[Region]:
    k = max(3, int(round(min(W, H) / 300)))
    edges = _edges(ink, W, H)
    for ln in lines:  # glyphs would close into letter blobs; blank the text lines first
        x0, y0, x1, y1 = (int(round(v)) for v in ln.box)
        edges[max(0, y0 - 1):min(H, y1 + 2), max(0, x0 - 1):min(W, x1 + 2)] = 0
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    closed = (closed > 0).astype(np.uint8)

    shapes = _dedupe(_outline_shapes(closed, W, H, k) + _filled_shapes(ink, lines, W, H), 0.85)
    shapes = [s for s in shapes if not any(_iou(s.box, ln.box) > 0.6 for ln in lines)]
    shapes = _drop_pockets(shapes)
    texts = [_Proto("text", ln.box, ln.text, ln.score, "ocr") for ln in lines]
    figures = [f for f in _figures(ink, lines, shapes, W, H) if all(_iou(f.box, s.box) <= 0.7 for s in shapes)]

    for s in shapes:
        s.parent = _smallest_container(s, shapes, 0.9)
    for p in texts + figures:
        p.parent = _smallest_container(p, shapes, 0.75)
    blocks = _blocks(texts, W)
    for s in shapes:  # a shape's label = its own lines (not those of nested shapes)
        own = [t for t in texts if t.parent is s or (t.parent is not None and t.parent.parent is s
                                                     and t.parent.kind == "text_block")]
        if own:
            s.text = " ".join(t.text or "" for t in sorted(own, key=lambda t: (t.box[1], t.box[0])))
            s.source = "merged"

    protos = texts + shapes + blocks + figures
    if len(protos) > MAX_REGIONS:
        protos = _cap(protos)
    row = max(1.0, 0.025 * H)
    protos.sort(key=lambda p: (round(p.box[1] / row), p.box[0], -_area(p.box)))
    for i, p in enumerate(protos, 1):
        p.rid = f"R{i}"
    kept = set(map(id, protos))
    regions = []
    for p in protos:
        parent = p.parent
        while parent is not None and id(parent) not in kept:
            parent = parent.parent
        x0, y0, x1, y1 = p.box
        regions.append(Region(
            id=p.rid, kind=p.kind,  # type: ignore[arg-type]
            box=Box(x=x0 / W, y=y0 / H, w=(x1 - x0) / W, h=(y1 - y0) / H),
            text=p.text or None, score=round(float(p.score), 3), source=p.source,  # type: ignore[arg-type]
            parent_id=parent.rid if parent is not None else None,
        ))
    return regions


def _cap(protos: list[_Proto]) -> list[_Proto]:
    """Keep text lines and shapes; drop the smallest figures, then text blocks, then small shapes."""
    rank = {"text": 0, "shape": 1, "text_block": 2, "figure": 3}
    ordered = sorted(protos, key=lambda p: (rank[p.kind], -_area(p.box)))
    return ordered[:MAX_REGIONS]
