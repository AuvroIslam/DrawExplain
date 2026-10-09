"""PIL renderer of lesson annotations over the untouched original image.

render_lesson(image, steps, upto=None, regions=None) draws every annotation of steps[:upto] from
its normalized Geometry. It is meant to be faithful (debugging, CLI, eval), not pretty: the real
whiteboard is the Excalidraw board in the frontend.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.schemas import Annotation, Box, Point, Region, Step

PALETTE: dict[str, str] = {
    "red": "#e03131",
    "blue": "#1971c2",
    "green": "#2f9e44",
    "orange": "#f08c00",
    "purple": "#9c36b5",
}
HAND_FONTS = ("C:/Windows/Fonts/segoepr.ttf", "segoepr.ttf", "C:/Windows/Fonts/arial.ttf", "arial.ttf", "DejaVuSans.ttf")
BOLD_FONTS = ("C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arial.ttf")
HIGHLIGHT_ALPHA = 85
REGION_RGBA = (120, 120, 120, 120)

XY = tuple[float, float]
Rect = tuple[float, float, float, float]


def render_lesson(
    image: Image.Image,
    steps: Sequence[Step | dict[str, Any]],
    upto: int | None = None,
    regions: Iterable[Region] | None = None,
) -> Image.Image:
    """Image with the annotations of steps[:upto] drawn on top (RGB, same size as `image`)."""
    base = image.convert("RGBA")
    size = base.size
    w, h = size
    stroke = max(3, round(0.004 * max(w, h)))

    if regions:
        base = Image.alpha_composite(base, _region_layer(size, list(regions)))

    marker = Image.new("RGBA", size, (0, 0, 0, 0))  # translucent highlighter, under the pen strokes
    pen = Image.new("RGBA", size, (0, 0, 0, 0))
    marker_draw = ImageDraw.Draw(marker)
    pen_draw = ImageDraw.Draw(pen)
    badges: list[tuple[int, XY, tuple[int, int, int]]] = []

    for step in [s if isinstance(s, Step) else Step.model_validate(s) for s in steps][:upto]:
        badge_done = False
        for ann in step.annotations:
            color = _rgb(ann.color)
            drawn = _draw_annotation(ann, color, size, stroke, pen_draw, marker_draw)
            if drawn is not None and not badge_done:
                badges.append((step.index, (drawn[0], drawn[1]), color))
                badge_done = True

    out = Image.alpha_composite(Image.alpha_composite(base, marker), pen)
    if badges:
        badge_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        badge_draw = ImageDraw.Draw(badge_layer)
        for index, anchor, color in badges:
            _draw_badge(badge_draw, index, anchor, color, size)
        out = Image.alpha_composite(out, badge_layer)
    return out.convert("RGB")


def _draw_annotation(
    ann: Annotation,
    color: tuple[int, int, int],
    size: tuple[int, int],
    stroke: int,
    pen: ImageDraw.ImageDraw,
    marker: ImageDraw.ImageDraw,
) -> Rect | None:
    """Draw one annotation; returns its pixel bounds (for the step badge) or None if nothing was drawn."""
    g = ann.geometry
    box = _rect(g.box, size)
    points = [_xy(p, size) for p in g.points or []]
    label_box = _rect(g.label_box, size)

    if ann.kind == "circle" and box:
        pen.ellipse(box, outline=color, width=stroke)
        return box
    if ann.kind == "box" and box:
        pen.rectangle(box, outline=color, width=stroke)
        return box
    if ann.kind == "highlight" and box:
        marker.rectangle(box, fill=(*color, HIGHLIGHT_ALPHA))
        return box
    if ann.kind == "underline":
        if len(points) < 2 and box:
            points = [(box[0], box[3]), (box[2], box[3])]
        if len(points) >= 2:
            _polyline(pen, points, color, stroke)
            return _bounds(points)
        return None
    if ann.kind == "arrow":
        if len(points) == 2:
            points = [points[0], _mid(points[0], points[1]), points[1]]
        if len(points) < 3:
            return None
        curve = _bezier(points[0], points[1], points[2])
        _polyline(pen, curve, color, stroke)
        _arrowhead(pen, curve, points, color, stroke)
        if ann.text and label_box:
            _text_in_box(pen, ann.text, label_box, color)
        return _bounds(curve)
    if ann.kind == "label":
        leader = [_xy(p, size) for p in g.leader or []]
        if len(leader) >= 2:
            thin = max(2, round(stroke * 0.6))
            _polyline(pen, leader[:2], color, thin)
            r = thin + 1
            x, y = leader[1]
            pen.ellipse((x - r, y - r, x + r, y + r), fill=color)
        if label_box is None and box and ann.text:
            bh = max(14.0, (box[3] - box[1]) * 0.5)
            label_box = (box[0], max(0.0, box[1] - bh - 4), box[2], max(bh, box[1] - 4))
        if label_box and ann.text:
            _text_in_box(pen, ann.text, label_box, color)
            return label_box
        return _bounds(leader) if len(leader) >= 2 else None
    return None


# ---------------------------------------------------------------- primitives


def _polyline(draw: ImageDraw.ImageDraw, pts: Sequence[XY], color: tuple[int, int, int], width: int) -> None:
    draw.line(list(pts), fill=color, width=width, joint="curve")
    r = width / 2
    for x, y in (pts[0], pts[-1]):  # round caps
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def _bezier(p0: XY, p1: XY, p2: XY, n: int = 48) -> list[XY]:
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        out.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    return out


def _arrowhead(
    draw: ImageDraw.ImageDraw, curve: list[XY], ctrl: list[XY], color: tuple[int, int, int], stroke: int
) -> None:
    end = curve[-1]
    dx, dy = 2 * (ctrl[2][0] - ctrl[1][0]), 2 * (ctrl[2][1] - ctrl[1][1])  # tangent at t = 1
    if math.hypot(dx, dy) < 1e-6:
        dx, dy = ctrl[2][0] - ctrl[0][0], ctrl[2][1] - ctrl[0][1]
    if math.hypot(dx, dy) < 1e-6:
        return
    angle = math.atan2(dy, dx)
    length = max(12.0, 4.5 * stroke)
    for side in (-1, 1):
        a = angle + math.pi - side * math.radians(28)
        tip = (end[0] + length * math.cos(a), end[1] + length * math.sin(a))
        _polyline(draw, [end, tip], color, stroke)


def _text_in_box(draw: ImageDraw.ImageDraw, text: str, box: Rect, color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    bw, bh = max(1.0, x1 - x0), max(1.0, y1 - y0)
    font, lines, line_h = _fit_text(text, bw, bh)
    total = line_h * len(lines)
    y = y0 + (bh - total) / 2
    halo = max(1, round(font.size / 10))
    for line in lines:
        lw = font.getlength(line)
        draw.text((x0 + (bw - lw) / 2, y), line, font=font, fill=color, stroke_width=halo, stroke_fill="white")
        y += line_h


def _fit_text(text: str, bw: float, bh: float) -> tuple[ImageFont.FreeTypeFont, list[str], float]:
    """Largest font (and greedy word wrap) that fits the box; never below 9 px."""
    start = max(9, min(int(bh * 0.8), 96))
    for size in range(start, 8, -1):
        font = _font(HAND_FONTS, size)
        line_h = _line_height(font)
        lines = _wrap(text, font, bw)
        if line_h * len(lines) <= bh * 1.1 and max(font.getlength(ln) for ln in lines) <= bw * 1.05:
            return font, lines, line_h
    font = _font(HAND_FONTS, 9)
    return font, _wrap(text, font, bw), _line_height(font)


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and font.getlength(trial) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    lines.append(current)
    return lines


def _line_height(font: ImageFont.FreeTypeFont) -> float:
    left, top, right, bottom = font.getbbox("Hgjy")
    return (bottom - top) * 1.15


def _draw_badge(
    draw: ImageDraw.ImageDraw, index: int, anchor: XY, color: tuple[int, int, int], size: tuple[int, int]
) -> None:
    w, h = size
    r = max(9, round(0.011 * max(w, h)))
    cx = min(max(anchor[0] - r * 0.7, r + 1), w - r - 1)
    cy = min(max(anchor[1] - r * 0.7, r + 1), h - r - 1)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, 235), outline=(255, 255, 255, 255), width=2)
    font = _font(BOLD_FONTS, max(9, round(r * 1.2)))
    draw.text((cx, cy), str(index), font=font, fill=(255, 255, 255, 255), anchor="mm")


def _region_layer(size: tuple[int, int], regions: list[Region]) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _font(BOLD_FONTS, max(9, round(0.009 * max(size))))
    for region in regions:
        rect = _rect(region.box, size)
        if rect is None:
            continue
        draw.rectangle(rect, outline=REGION_RGBA, width=1)
        draw.text((rect[0] + 2, rect[1] + 1), region.id, font=font, fill=REGION_RGBA)
    return layer


# ---------------------------------------------------------------- helpers


@lru_cache(maxsize=256)
def _font(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)  # type: ignore[return-value]


def _rgb(color: str) -> tuple[int, int, int]:
    value = PALETTE.get(color, PALETTE["red"]).lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rect(box: Box | None, size: tuple[int, int]) -> Rect | None:
    if box is None:
        return None
    w, h = size
    x0, x1 = sorted((box.x * w, (box.x + box.w) * w))
    y0, y1 = sorted((box.y * h, (box.y + box.h) * h))
    if x1 - x0 < 1 and y1 - y0 < 1:
        return None
    return x0, y0, max(x1, x0 + 1), max(y1, y0 + 1)


def _xy(p: Point, size: tuple[int, int]) -> XY:
    return p.x * size[0], p.y * size[1]


def _mid(a: XY, b: XY) -> XY:
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def _bounds(pts: Sequence[XY]) -> Rect:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)
