"""Synthetic lecture slides with pixel ground truth, for the grounding evaluation.

Run from backend/:
    .venv/Scripts/python scripts/make_samples.py                    # every template and variant
    .venv/Scripts/python scripts/make_samples.py --only cell_organelles --sets clean,photo --debug

Writes samples/synthetic/<set>/<name>.png (photos: .jpg) + <name>.json, set in clean | photo | dark | small.
The JSON matches samples/quick/*.json ({"elements": [{"name", "kind", "box": [x0, y0, x1, y1]}]}, pixel
boxes of that image file) and adds "query" per element: how a student would name it.
Rendering is deterministic for a given --seed (only the photo variant uses randomness).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import zlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
OUT_DIR = ROOT_DIR / "samples" / "synthetic"
DEBUG_DIR = BACKEND_DIR / "data" / "tmp" / "samples_debug"
FONT_DIR = Path("C:/Windows/Fonts")

SS = 2  # supersampling factor: draw at 2x, downsample with LANCZOS for anti-aliased shapes
SETS = ("clean", "photo", "dark", "small")
DARK_TEMPLATES = ("flowchart_loop", "formulas_kinematics")
SMALL_TEMPLATES = ("dense_architecture", "cell_organelles")
SMALL_WIDTH = 900
PHOTO_SIZE = (1600, 1200)
PHOTO_QUALITY = 60
KINDS = ("text", "text_block", "shape", "figure", "arrow")

RGB = tuple[int, int, int]
Pt = tuple[float, float]
Box4 = tuple[float, float, float, float]

# ---------------------------------------------------------------- fonts

FACES: dict[str, dict[str, str]] = {
    "segoe": {"regular": "segoeui.ttf", "semibold": "seguisb.ttf", "bold": "segoeuib.ttf", "italic": "segoeuii.ttf"},
    "calibri": {"regular": "calibri.ttf", "semibold": "calibrib.ttf", "bold": "calibrib.ttf", "italic": "calibrii.ttf"},
    "arial": {"regular": "arial.ttf", "semibold": "arialbd.ttf", "bold": "arialbd.ttf", "italic": "ariali.ttf"},
    "cambria": {"regular": "cambria.ttc", "semibold": "cambriab.ttf", "bold": "cambriab.ttf", "italic": "cambriai.ttf"},
    "times": {"regular": "times.ttf", "semibold": "timesbd.ttf", "bold": "timesbd.ttf", "italic": "timesi.ttf"},
}
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(face: str, size: float, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """A Windows font by face/weight, falling back to Arial and then Pillow's bundled font."""
    files = FACES.get(face, FACES["arial"])
    px = max(1, round(size))
    for name in (files.get(weight, files["regular"]), files["regular"], "arial.ttf"):
        key = (name, px)
        if key in _font_cache:
            return _font_cache[key]
        path = FONT_DIR / name
        if path.is_file():
            _font_cache[key] = ImageFont.truetype(str(path), px)
            return _font_cache[key]
    return ImageFont.load_default(size=px)


# ---------------------------------------------------------------- colours and themes

def mix(a: Sequence[int], b: Sequence[int], t: float) -> RGB:
    """Linear blend: t=0 gives a, t=1 gives b."""
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


WHITE: RGB = (255, 255, 255)


@dataclass(frozen=True)
class Theme:
    bg: RGB
    title: RGB
    text: RGB
    muted: RGB
    accent: RGB
    soft: RGB  # card fill
    outline: RGB  # card outline
    line: RGB  # connectors and arrows
    panel: RGB  # callout fill
    panel_line: RGB
    rule: RGB  # footer rule
    face: str = "segoe"
    header: str = "underline"  # underline | band | bar
    dark: bool = False

    def tint(self, hue: RGB, amount: float = 0.82) -> RGB:
        """A fill of `hue` that sits on this background (pastel on light, deep on dark)."""
        return mix(hue, self.bg, amount if not self.dark else 0.72)

    def ink(self, hue: RGB) -> RGB:
        """`hue` as a stroke colour that reads on this background."""
        return hue if not self.dark else mix(hue, WHITE, 0.35)


def light_theme(accent: RGB, face: str, header: str) -> Theme:
    return Theme(
        bg=(255, 255, 255), title=(24, 32, 48), text=(33, 37, 41), muted=(108, 117, 125), accent=accent,
        soft=mix(accent, WHITE, 0.87), outline=mix(accent, (0, 0, 0), 0.25), line=(73, 80, 87),
        panel=(255, 248, 219), panel_line=(236, 201, 110), rule=(222, 226, 230), face=face, header=header,
    )


def dark_theme(t: Theme) -> Theme:
    bg = (24, 29, 43)
    accent = mix(t.accent, WHITE, 0.3)
    return replace(
        t, bg=bg, title=(248, 250, 252), text=(226, 232, 240), muted=(148, 163, 184), accent=accent,
        soft=mix(t.accent, bg, 0.7), outline=mix(t.accent, WHITE, 0.45), line=(203, 213, 225),
        panel=(36, 45, 66), panel_line=(88, 104, 132), rule=(51, 65, 85), dark=True,
    )


BLUE: RGB = (25, 99, 180)
TEAL: RGB = (12, 122, 116)
GREEN: RGB = (46, 125, 50)
ORANGE: RGB = (201, 86, 18)
INDIGO: RGB = (67, 56, 202)
PURPLE: RGB = (108, 52, 160)
SLATE: RGB = (46, 74, 120)

RED_F: RGB = (224, 49, 49)
BLUE_F: RGB = (25, 113, 194)
GREEN_F: RGB = (47, 158, 68)
ORANGE_F: RGB = (232, 128, 0)


# ---------------------------------------------------------------- geometry helpers

def rect_pts(b: Box4) -> list[Pt]:
    x0, y0, x1, y1 = b
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def round_rect_pts(b: Box4, r: float, n: int = 6) -> list[Pt]:
    x0, y0, x1, y1 = b
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    if r <= 0:
        return rect_pts(b)
    pts: list[Pt] = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ellipse_pts(b: Box4, n: int = 72) -> list[Pt]:
    x0, y0, x1, y1 = b
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def bbox_of(pts: Iterable[Pt]) -> Box4:
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)


@dataclass
class Element:
    """One ground-truth thing on a slide; `pts` outline it in image pixels (used for warps)."""

    name: str
    kind: str
    query: str
    pts: list[Pt]
    shape: str | None = None

    def bbox(self) -> Box4:
        return bbox_of(self.pts)

    def mapped(self, fn: Callable[[list[Pt]], list[Pt]]) -> "Element":
        return replace(self, pts=fn(self.pts))

    def to_json(self, w: int, h: int) -> dict:
        x0, y0, x1, y1 = self.bbox()
        box = [max(0, math.floor(x0)), max(0, math.floor(y0)), min(w, math.ceil(x1)), min(h, math.ceil(y1))]
        out: dict = {"name": self.name, "kind": self.kind}
        if self.shape:
            out["shape"] = self.shape
        out["query"] = self.query
        out["box"] = box
        return out


# ---------------------------------------------------------------- canvas

class Canvas:
    """A slide drawn at SS x resolution; every coordinate in the API is a final-image pixel."""

    def __init__(self, w: int, h: int, theme: Theme, ss: int = SS):
        self.w, self.h, self.t, self.ss = w, h, theme, ss
        self.img = Image.new("RGB", (w * ss, h * ss), theme.bg)
        self.d = ImageDraw.Draw(self.img)
        self.elements: list[Element] = []

    def _p(self, pts: Iterable[Pt]) -> list[Pt]:
        return [(x * self.ss, y * self.ss) for x, y in pts]

    def _w(self, width: float) -> int:
        return max(1, round(width * self.ss)) if width else 0

    def add(self, name: str, kind: str, query: str, pts: Iterable[Pt], shape: str | None = None) -> Element:
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind!r}")
        if any(e.name == name for e in self.elements):
            raise ValueError(f"duplicate element name {name!r}")
        el = Element(name, kind, query, list(pts), shape)
        self.elements.append(el)
        return el

    def text(self, xy: Pt, s: str, size: float, *, weight: str = "regular", face: str | None = None,
             fill: RGB | None = None, anchor: str = "la", name: str | None = None, query: str | None = None,
             kind: str = "text") -> Box4:
        f = font(face or self.t.face, size * self.ss, weight)
        p = (xy[0] * self.ss, xy[1] * self.ss)
        self.d.text(p, s, font=f, fill=fill or self.t.text, anchor=anchor)
        x0, y0, x1, y1 = (v / self.ss for v in self.d.textbbox(p, s, font=f, anchor=anchor))
        if query is not None:
            self.add(name or s, kind, query, rect_pts((x0, y0, x1, y1)))
        return (x0, y0, x1, y1)

    def vtext(self, center: Pt, s: str, size: float, *, weight: str = "regular", fill: RGB | None = None,
              name: str | None = None, query: str | None = None) -> Box4:
        """Text rotated 90 degrees (reads bottom to top), centred on `center`."""
        f = font(self.t.face, size * self.ss, weight)
        x0, y0, x1, y1 = f.getbbox(s)
        mask = Image.new("L", (x1 - x0 + 4, y1 - y0 + 4), 0)
        ImageDraw.Draw(mask).text((2 - x0, 2 - y0), s, font=f, fill=255)
        rot = mask.rotate(90, expand=True)
        px, py = round(center[0] * self.ss - rot.width / 2), round(center[1] * self.ss - rot.height / 2)
        self.img.paste(Image.new("RGB", rot.size, fill or self.t.text), (px, py), rot)
        ix0, iy0, ix1, iy1 = rot.getbbox() or (0, 0, rot.width, rot.height)
        box = ((px + ix0) / self.ss, (py + iy0) / self.ss, (px + ix1) / self.ss, (py + iy1) / self.ss)
        if query is not None:
            self.add(name or s, "text", query, rect_pts(box))
        return box

    def rect(self, box: Box4, *, fill: RGB | None = None, outline: RGB | None = None, width: float = 0,
             radius: float = 0, name: str | None = None, query: str | None = None, kind: str = "shape",
             shape: str | None = None) -> list[Pt]:
        b = [v * self.ss for v in box]
        if radius:
            self.d.rounded_rectangle(b, radius=radius * self.ss, fill=fill, outline=outline, width=self._w(width))
        else:
            self.d.rectangle(b, fill=fill, outline=outline, width=self._w(width))
        pts = round_rect_pts(box, radius) if radius else rect_pts(box)
        if query is not None:
            self.add(name or "?", kind, query, pts, shape or ("round" if radius else "rect"))
        return pts

    def ellipse(self, box: Box4, *, fill: RGB | None = None, outline: RGB | None = None, width: float = 0,
                name: str | None = None, query: str | None = None, kind: str = "shape") -> list[Pt]:
        self.d.ellipse([v * self.ss for v in box], fill=fill, outline=outline, width=self._w(width))
        pts = ellipse_pts(box)
        if query is not None:
            self.add(name or "?", kind, query, pts, "ellipse")
        return pts

    def polygon(self, pts: Sequence[Pt], *, fill: RGB | None = None, outline: RGB | None = None, width: float = 0,
                name: str | None = None, query: str | None = None, kind: str = "shape",
                shape: str = "polygon") -> list[Pt]:
        self.d.polygon(self._p(pts), fill=fill, outline=outline, width=self._w(width))
        if query is not None:
            self.add(name or "?", kind, query, pts, shape)
        return list(pts)

    def line(self, pts: Sequence[Pt], *, fill: RGB | None = None, width: float = 2, dash: float = 0) -> None:
        fill = fill or self.t.line
        if not dash:
            self.d.line(self._p(pts), fill=fill, width=self._w(width), joint="curve")
            return
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            seg = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / max(seg, 1e-6), (by - ay) / max(seg, 1e-6)
            pos = 0.0
            while pos < seg:
                end = min(seg, pos + dash)
                self.d.line(self._p([(ax + ux * pos, ay + uy * pos), (ax + ux * end, ay + uy * end)]), fill=fill,
                            width=self._w(width))
                pos += dash * 1.8

    @staticmethod
    def _head(p0: Pt, p1: Pt, size: float, width: float) -> tuple[Pt, list[Pt]]:
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        base = (p1[0] - ux * size, p1[1] - uy * size)
        half = max(size * 0.5, width * 1.6)
        tri = [p1, (base[0] - uy * half, base[1] + ux * half), (base[0] + uy * half, base[1] - ux * half)]
        return (base[0] + ux * 1.5, base[1] + uy * 1.5), tri

    def arrow(self, pts: Sequence[Pt], *, fill: RGB | None = None, width: float = 3, head: float = 12,
              both: bool = False, dash: float = 0, name: str | None = None, query: str | None = None) -> list[Pt]:
        fill = fill or self.t.line
        pts = [(float(x), float(y)) for x, y in pts]
        body = list(pts)
        heads = []
        body[-1], tri = self._head(pts[-2], pts[-1], head, width)
        heads.append(tri)
        if both:
            body[0], tri = self._head(pts[1], pts[0], head, width)
            heads.append(tri)
        self.line(body, fill=fill, width=width, dash=dash)
        for tri in heads:
            self.d.polygon(self._p(tri), fill=fill)
        hw = width / 2
        outline = [(x + dx, y + dy) for x, y in pts for dx in (-hw, hw) for dy in (-hw, hw)]
        outline += [p for tri in heads for p in tri]
        if query is not None:
            self.add(name or "?", "arrow", query, outline)
        return outline

    def finish(self) -> Image.Image:
        return self.img.resize((self.w, self.h), Image.LANCZOS)


# ---------------------------------------------------------------- shared slide parts

def chrome(c: Canvas, title: str, course: str, number: int, subtitle: str | None = None) -> None:
    """Title area and footer that every slide of the deck shares."""
    t, w, h = c.t, c.w, c.h
    if t.header == "band":
        c.rect((0, 0, w, 96), fill=t.accent if not t.dark else mix(t.accent, t.bg, 0.45))
        c.text((56, 50), title, 36, weight="semibold", fill=WHITE, anchor="lm", name="title", query="the slide title")
        top = 96
    elif t.header == "bar":
        c.rect((40, 36, 48, 86), fill=t.accent)
        c.text((66, 62), title, 38, weight="semibold", fill=t.title, anchor="lm", name="title", query="the slide title")
        top = 92
    else:
        c.text((60, 58), title, 38, weight="semibold", fill=t.title, anchor="lm", name="title", query="the slide title")
        c.rect((60, 94, w - 60, 96), fill=t.accent)
        top = 96
    if subtitle:
        c.text((66 if t.header == "bar" else 60, top + 26), subtitle, 21, fill=t.muted, anchor="lm", name="subtitle",
               query="the subtitle under the title")
    c.rect((60, h - 46, w - 60, h - 45), fill=t.rule)
    c.text((60, h - 25), course, 15, fill=t.muted, anchor="lm", name="footer", query="the course name in the footer")
    c.text((w - 60, h - 25), str(number), 15, fill=t.muted, anchor="rm", name="slide number",
           query="the slide number")


def callout(c: Canvas, box: Box4, heading: str, lines: Sequence[tuple[str, str, str]], size: float = 20,
            name: str | None = None, query: str | None = None) -> None:
    """A rounded note box with a bold heading; `lines` are (text, element name, query) with name '' = no GT."""
    t = c.t
    c.rect(box, fill=t.panel, outline=t.panel_line, width=2, radius=12, name=name, query=query)
    x0, y0 = box[0] + 24, box[1] + 30
    c.text((x0, y0), heading, size, weight="bold", fill=t.text, anchor="lm")
    for i, (s, el_name, el_query) in enumerate(lines):
        c.text((x0, y0 + (i + 1) * size * 1.9), s, size, fill=t.text, anchor="lm", name=el_name or None,
               query=el_query or None)


# ---------------------------------------------------------------- template: network

def _card(c: Canvas, box: Box4, label: str, icon: Callable[[Canvas, float, float], None], query: str) -> None:
    t = c.t
    c.rect(box, fill=t.soft, outline=t.outline, width=2.5, radius=12, name=label, query=query)
    cx = (box[0] + box[2]) / 2
    icon(c, cx, box[1] + 40)
    c.text((cx, box[3] - 22), label, 19, weight="semibold", fill=t.text, anchor="mm")


def _icon_laptop(c: Canvas, cx: float, cy: float) -> None:
    t = c.t
    c.rect((cx - 25, cy - 21, cx + 25, cy + 10), fill=t.tint((120, 170, 230), 0.4), outline=t.outline, width=3,
           radius=3)
    c.polygon([(cx - 33, cy + 13), (cx + 33, cy + 13), (cx + 38, cy + 20), (cx - 38, cy + 20)], fill=t.outline)


def _icon_switch(c: Canvas, cx: float, cy: float) -> None:
    t = c.t
    c.rect((cx - 36, cy - 4, cx + 36, cy + 18), fill=t.outline, radius=3)
    for i in range(6):
        x = cx - 29 + i * 10.5
        c.rect((x, cy + 6, x + 6, cy + 12), fill=t.soft)
    c.arrow([(cx - 22, cy - 12), (cx + 22, cy - 12)], fill=t.outline, width=2.5, head=7)
    c.arrow([(cx + 22, cy - 21), (cx - 22, cy - 21)], fill=t.outline, width=2.5, head=7)


def _icon_router(c: Canvas, cx: float, cy: float) -> None:
    t = c.t
    c.ellipse((cx - 32, cy + 2, cx + 32, cy + 22), fill=t.outline)
    c.rect((cx - 32, cy - 8, cx + 32, cy + 12), fill=t.outline)
    c.ellipse((cx - 32, cy - 20, cx + 32, cy + 4), fill=mix(t.outline, WHITE, 0.25))
    c.arrow([(cx - 14, cy - 13), (cx + 14, cy - 3)], fill=WHITE, width=2, head=6, both=True)
    c.arrow([(cx + 14, cy - 13), (cx - 14, cy - 3)], fill=WHITE, width=2, head=6, both=True)


def _icon_firewall(c: Canvas, cx: float, cy: float) -> None:
    brick = (192, 72, 52) if not c.t.dark else (214, 104, 84)
    mortar = c.t.soft
    x0, y0, x1, y1 = cx - 34, cy - 20, cx + 34, cy + 20
    c.rect((x0, y0, x1, y1), fill=brick)
    for i in range(1, 4):
        y = y0 + i * 10
        c.line([(x0, y), (x1, y)], fill=mortar, width=2)
    for row in range(4):
        off = 0 if row % 2 == 0 else 8.5
        for j in range(5):
            x = x0 + off + j * 17
            if x0 < x < x1:
                c.line([(x, y0 + row * 10), (x, y0 + row * 10 + 10)], fill=mortar, width=2)


def _icon_server(c: Canvas, cx: float, cy: float, color: RGB | None = None) -> None:
    t = c.t
    col = color or t.outline
    c.rect((cx - 20, cy - 24, cx + 20, cy + 22), fill=col, radius=3)
    for i in range(3):
        y = cy - 17 + i * 12
        c.rect((cx - 14, y, cx + 14, y + 7), fill=mix(col, WHITE, 0.55))
        c.ellipse((cx + 8, y + 2, cx + 11, y + 5), fill=(64, 192, 87))


def _cloud(c: Canvas, box: Box4, label: str, query: str) -> None:
    t = c.t
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    circles = [(0.20, 0.64, 0.28), (0.37, 0.42, 0.34), (0.60, 0.36, 0.36), (0.80, 0.58, 0.29),
               (0.54, 0.68, 0.31), (0.34, 0.72, 0.26), (0.70, 0.74, 0.25)]
    stroke = 3.0
    pts: list[Pt] = []
    for fx, fy, fr in circles:
        cx, cy, r = x0 + fx * w, y0 + fy * h, fr * h
        c.ellipse((cx - r - stroke, cy - r - stroke, cx + r + stroke, cy + r + stroke), fill=t.outline)
        pts += ellipse_pts((cx - r - stroke, cy - r - stroke, cx + r + stroke, cy + r + stroke), 48)
    for fx, fy, fr in circles:
        cx, cy, r = x0 + fx * w, y0 + fy * h, fr * h
        c.ellipse((cx - r, cy - r, cx + r, cy + r), fill=t.soft)
    c.add(label, "shape", query, pts, "cloud")
    c.text((x0 + 0.5 * w, y0 + 0.56 * h), label, 24, weight="bold", fill=t.text, anchor="mm")


def network_topology(c: Canvas) -> None:
    t = c.t
    chrome(c, "How a Web Request Travels", "CSE 3101 · Computer Networks · Lecture 4", 12,
           subtitle="Every hop forwards the packet one step closer to the server")
    y0, y1 = 196, 308
    devices = [("Laptop", _icon_laptop, 60), ("Switch", _icon_switch, 270), ("Router", _icon_router, 480),
               ("Firewall", _icon_firewall, 690)]
    for label, icon, x in devices:
        _card(c, (x, y0, x + 150, y1), label, icon, f"the {label}")
    cy = (y0 + y1) / 2
    for (_, _, xa), (_, _, xb) in zip(devices, devices[1:]):
        c.arrow([(xa + 156, cy), (xb - 6, cy)], width=3, head=12)
    _cloud(c, (905, 160, 1215, 344), "Internet", "the Internet cloud")
    c.arrow([(846, cy), (918, cy)], width=3, head=12)
    _card(c, (850, 450, 1000, 562), "DNS Server", lambda cc, x, y: _icon_server(cc, x, y, (47, 158, 68)),
          "the DNS Server")
    _card(c, (1070, 450, 1220, 562), "Web Server", _icon_server, "the Web Server")
    c.line([(1010, 318), (948, 444)], width=2.5, dash=9)
    c.text((968, 384), "DNS lookup", 16, weight="semibold", fill=t.muted, anchor="rm", name="DNS lookup",
           query="the 'DNS lookup' label")
    c.arrow([(1128, 336), (1140, 444)], width=3, head=12)
    c.text((1150, 392), "HTTPS", 16, weight="semibold", fill=t.muted, anchor="lm", name="HTTPS",
           query="the 'HTTPS' label on the arrow to the Web Server")
    callout(c, (60, 400, 760, 556), "Key idea", [
        ("Switch: forwards frames inside one network (MAC addresses)", "note: switch",
         "the note line explaining what a switch does"),
        ("Router: forwards packets between networks (IP addresses)", "note: router",
         "the note line explaining what a router does"),
    ], name="key idea box", query="the Key idea box")
    c.text((60, 608), "Figure 1. Path of an HTTP request from a home laptop to a web server.", 18, weight="italic",
           fill=t.muted, anchor="lm", name="caption", query="the figure caption")


# ---------------------------------------------------------------- template: flowchart

def _pill(c: Canvas, box: Box4, fill: RGB, outline: RGB, name: str, query: str) -> None:
    c.rect(box, fill=fill, outline=outline, width=3, radius=(box[3] - box[1]) / 2, name=name, query=query,
           shape="pill")


def _parallelogram(box: Box4, skew: float) -> list[Pt]:
    x0, y0, x1, y1 = box
    return [(x0 + skew, y0), (x1, y0), (x1 - skew, y1), (x0, y1)]


def _diamond(box: Box4) -> list[Pt]:
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return [(cx, y0), (x1, cy), (cx, y1), (x0, cy)]


def flowchart_loop(c: Canvas) -> None:
    t = c.t
    chrome(c, "Flowchart: Input Validation Loop", "CS 1101 · Programming Fundamentals", 7,
           subtitle="Keep asking for input until it passes the check")
    term, io, dec, proc, err = (GREEN_F, BLUE_F, ORANGE_F, (94, 96, 206), RED_F)
    cy = 300
    _pill(c, (50, cy - 32, 190, cy + 32), t.tint(term), t.ink(mix(term, (0, 0, 0), 0.2)), "Start",
          "the Start terminal")
    c.text((120, cy), "Start", 24, weight="semibold", anchor="mm")
    read = (240, cy - 38, 450, cy + 38)
    c.polygon(_parallelogram(read, 24), fill=t.tint(io), outline=t.ink(mix(io, (0, 0, 0), 0.2)), width=3,
              name="Read input", query="the 'Read input' step", shape="parallelogram")
    c.text((345, cy), "Read input", 24, weight="semibold", anchor="mm")
    diamond = (520, cy - 76, 700, cy + 76)
    c.polygon(_diamond(diamond), fill=t.tint(dec), outline=t.ink(mix(dec, (0, 0, 0), 0.2)), width=3,
              name="Valid?", query="the 'Valid?' decision diamond", shape="diamond")
    c.text((610, cy), "Valid?", 24, weight="semibold", anchor="mm")
    c.rect((780, cy - 38, 970, cy + 38), fill=t.tint(proc), outline=t.ink(mix(proc, (0, 0, 0), 0.2)), width=3,
           radius=4, name="Process data", query="the 'Process data' box", shape="rect")
    c.text((875, cy), "Process data", 24, weight="semibold", anchor="mm")
    _pill(c, (1060, cy - 32, 1200, cy + 32), t.tint(term), t.ink(mix(term, (0, 0, 0), 0.2)), "End",
          "the End terminal")
    c.text((1130, cy), "End", 24, weight="semibold", anchor="mm")
    c.rect((520, 470, 700, 540), fill=t.tint(err), outline=t.ink(mix(err, (0, 0, 0), 0.2)), width=3, radius=4,
           name="Show error", query="the 'Show error' box", shape="rect")
    c.text((610, 505), "Show error", 24, weight="semibold", anchor="mm")

    c.arrow([(190, cy), (250, cy)], width=3, head=13)
    c.arrow([(440, cy), (518, cy)], width=3, head=13)
    c.arrow([(700, cy), (778, cy)], width=3, head=13)
    c.text((739, cy - 14), "Yes", 21, weight="bold", fill=t.ink(GREEN_F), anchor="mb", name="Yes",
           query="the 'Yes' label")
    c.arrow([(970, cy), (1058, cy)], width=3, head=13)
    c.arrow([(610, cy + 76), (610, 468)], width=3, head=13)
    c.text((624, 422), "No", 21, weight="bold", fill=t.ink(RED_F), anchor="lm", name="No", query="the 'No' label")
    c.arrow([(520, 505), (334, 505), (334, cy + 40)], width=3, head=13, name="loop-back arrow",
            query="the loop-back arrow from 'Show error' to 'Read input'")

    key = (780, 420, 1220, 610)
    c.rect(key, fill=t.panel, outline=t.panel_line, width=2, radius=10, name="symbol key",
           query="the flowchart symbol key", kind="figure")
    c.text((804, 446), "Symbol key", 19, weight="bold", anchor="lm")
    entries = [("Start / End", "pill", term), ("Input / Output", "para", io), ("Process step", "rect", proc),
               ("Decision", "diamond", dec)]
    for i, (label, kind, hue) in enumerate(entries):
        x = 806 + (i % 2) * 210
        y = 500 + (i // 2) * 58
        box = (x, y - 15, x + 50, y + 15)
        col, line = t.tint(hue), t.ink(mix(hue, (0, 0, 0), 0.2))
        if kind == "pill":
            c.rect(box, fill=col, outline=line, width=2, radius=15)
        elif kind == "para":
            c.polygon(_parallelogram(box, 10), fill=col, outline=line, width=2)
        elif kind == "rect":
            c.rect(box, fill=col, outline=line, width=2)
        else:
            c.polygon(_diamond((x + 5, y - 17, x + 45, y + 17)), fill=col, outline=line, width=2)
        c.text((x + 62, y), label, 18, anchor="lm")
    c.text((50, 620), "The loop repeats until the user enters valid input.", 21, fill=t.muted, anchor="lm",
           name="caption", query="the sentence under the flowchart")


# ---------------------------------------------------------------- template: cell

def _capsule_pts(cx: float, cy: float, length: float, width: float, angle: float, n: int = 16) -> list[Pt]:
    r = width / 2
    half = length / 2 - r
    local: list[Pt] = []
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n
        local.append((half + r * math.cos(a), r * math.sin(a)))
    for i in range(n + 1):
        a = math.pi / 2 + math.pi * i / n
        local.append((-half + r * math.cos(a), r * math.sin(a)))
    ca, sa = math.cos(angle), math.sin(angle)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in local]


def _leader(c: Canvas, start: Pt, end: Pt, color: RGB) -> None:
    c.line([start, end], fill=color, width=2)
    c.ellipse((end[0] - 4, end[1] - 4, end[0] + 4, end[1] + 4), fill=color)


def cell_organelles(c: Canvas) -> None:
    t = c.t
    chrome(c, "Animal Cell: Main Organelles", "BIO 1203 · Cell Biology", 5)
    membrane, cyto = (150, 92, 70), (253, 236, 222)
    cell = (230, 128, 810, 618)
    c.ellipse(cell, fill=cyto, outline=membrane, width=7, name="Cell membrane", query="the cell membrane")
    c.ellipse((cell[0] + 11, cell[1] + 11, cell[2] - 11, cell[3] - 11), outline=(214, 160, 136), width=2)

    for k in range(4):  # rough endoplasmic reticulum around the nucleus
        pts = [(612 + 18 * k + 10 * math.sin(i / 2.2), 268 + i * 9) for i in range(22)]
        c.line(pts, fill=(205, 120, 150), width=3)

    nucleus = (440, 282, 620, 432)
    c.ellipse(nucleus, fill=(201, 176, 228), outline=(112, 72, 152), width=4, name="Nucleus", query="the nucleus")
    c.ellipse((500, 330, 548, 372), fill=(112, 72, 152), name="Nucleolus", query="the nucleolus")
    for a in range(0, 360, 40):
        x, y = 530 + 70 * math.cos(math.radians(a)), 357 + 55 * math.sin(math.radians(a))
        c.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(150, 110, 190))

    mx, my = 410, 488
    mito = _capsule_pts(mx, my, 150, 62, math.radians(-22))
    c.polygon(mito, fill=(246, 170, 104), outline=(184, 96, 36), width=3, name="Mitochondrion",
              query="the mitochondrion", shape="capsule")
    ca, sa = math.cos(math.radians(-22)), math.sin(math.radians(-22))
    zig = []
    for i in range(11):
        lx, ly = -52 + i * 10.4, (-15 if i % 2 else 15)
        zig.append((mx + lx * ca - ly * sa, my + lx * sa + ly * ca))
    c.line(zig, fill=(184, 96, 36), width=2.5)

    golgi_pts: list[Pt] = []
    for k in range(4):
        box = (300 + k * 4, 250 + k * 13, 420 - k * 4, 330 + k * 13)
        c.d.arc([v * c.ss for v in box], 200, 340, fill=(60, 140, 160), width=c._w(5))
        golgi_pts += [p for p in ellipse_pts(box, 90) if p[1] <= (box[1] + box[3]) / 2 - 8]
    c.add("Golgi apparatus", "shape", "the Golgi apparatus", golgi_pts, "arcs")

    rng = np.random.default_rng(11)
    dots: list[Pt] = []
    for _ in range(16):
        x, y = 668 + rng.uniform(-34, 34), 236 + rng.uniform(-22, 22)
        dots += ellipse_pts((x - 4.5, y - 4.5, x + 4.5, y + 4.5), 12)
        c.ellipse((x - 4.5, y - 4.5, x + 4.5, y + 4.5), fill=(52, 58, 128))
    c.add("Ribosomes", "shape", "the cluster of ribosome dots", dots, "dots")

    lc = t.line
    labels = [
        ("Ribosome", (900, 196), (700, 222)),
        ("Nucleus", (900, 306), (618, 352)),
        ("Cytoplasm", (900, 430), (742, 440)),
        ("Cell membrane", (900, 560), (737, 528)),
    ]
    for text, at, target in labels:
        box = c.text(at, text, 24, anchor="lm", name=f"label: {text}", query=f"the label '{text}'")
        _leader(c, (box[0] - 10, at[1]), target, lc)
    for text, at, target in (("Mitochondrion", (60, 590), (350, 522)), ("Golgi apparatus", (60, 214), (318, 262))):
        box = c.text(at, text, 24, anchor="lm", name=f"label: {text}", query=f"the label '{text}'")
        _leader(c, (box[2] + 10, at[1]), target, lc)
    c.text((1220, 640), "Simplified diagram, not to scale", 16, weight="italic", fill=t.muted, anchor="rm",
           name="caption", query="the 'not to scale' note")


# ---------------------------------------------------------------- template: free-body diagram

def free_body(c: Canvas) -> None:
    t = c.t
    chrome(c, "Free-Body Diagram: Pushing a Block", "PHY 1101 · Mechanics", 9)
    floor_y = 470
    c.line([(110, floor_y), (640, floor_y)], fill=t.text, width=3)
    for x in range(118, 640, 18):
        c.line([(x, floor_y + 2), (x - 12, floor_y + 16)], fill=t.muted, width=1.5)
    block = (300, 350, 480, floor_y - 1)
    c.rect(block, fill=t.tint((120, 140, 170), 0.7), outline=t.text, width=3, name="block", query="the block")
    c.text((336, 382), "m", 38, face="cambria", weight="italic", anchor="mm")
    c.ellipse((384, 404, 396, 416), fill=t.text)
    w = 5
    c.arrow([(390, 410), (390, 600)], fill=RED_F, width=w, head=20, name="weight arrow",
            query="the weight arrow (pointing down)")
    c.arrow([(390, 350), (390, 196)], fill=BLUE_F, width=w, head=20, name="normal force arrow",
            query="the normal force arrow (pointing up)")
    c.arrow([(480, 410), (650, 410)], fill=GREEN_F, width=w, head=20, name="applied force arrow",
            query="the applied force arrow")
    c.arrow([(300, 452), (150, 452)], fill=ORANGE_F, width=w, head=20, name="friction arrow",
            query="the friction arrow")
    c.text((404, 590), "Weight  mg", 24, weight="semibold", fill=t.ink(RED_F), anchor="lm", name="label: Weight mg",
           query="the label 'Weight mg'")
    c.text((404, 210), "Normal force  N", 24, weight="semibold", fill=t.ink(BLUE_F), anchor="lm",
           name="label: Normal force N", query="the label 'Normal force N'")
    c.text((565, 392), "Applied force  F", 24, weight="semibold", fill=t.ink(GREEN_F), anchor="mb",
           name="label: Applied force F", query="the label 'Applied force F'")
    c.text((214, 432), "Friction  f", 24, weight="semibold", fill=t.ink(ORANGE_F), anchor="mb",
           name="label: Friction f", query="the label 'Friction f'")

    x = 820
    c.text((x, 160), "Newton's second law", 26, weight="bold", anchor="lm", name="heading",
           query="the heading 'Newton's second law'")
    c.text((x, 232), "\u03a3F = ma", 46, face="cambria", weight="italic", anchor="lm", name="equation: sum",
           query="the equation \u03a3F = ma")
    c.text((x, 312), "x:   F \u2212 f = ma", 32, face="cambria", weight="italic", anchor="lm", name="equation: x",
           query="the x-direction equation F \u2212 f = ma")
    c.text((x, 370), "y:   N \u2212 mg = 0", 32, face="cambria", weight="italic", anchor="lm", name="equation: y",
           query="the y-direction equation N \u2212 mg = 0")
    c.text((x, 428), "f = \u03bcN", 32, face="cambria", weight="italic", anchor="lm", name="equation: friction",
           query="the friction law f = \u03bcN")
    c.text((x, 520), "The block speeds up only if F > f.", 21, anchor="lm", name="note",
           query="the note about when the block speeds up")


# ---------------------------------------------------------------- template: text + formulas

def formulas_kinematics(c: Canvas) -> None:
    t = c.t
    chrome(c, "Motion with Constant Acceleration", "PHY 1101 · Mechanics", 14)
    bullets = [
        ("Acceleration is the rate of change of velocity", "the first bullet point"),
        ("With constant acceleration, velocity grows linearly", "the bullet about velocity growing linearly"),
        ("Displacement is the area under the v\u2013t graph", "the bullet about the area under the v\u2013t graph"),
        ("A net force F on a mass m gives a = F / m", "the last bullet point (net force)"),
    ]
    for i, (s, q) in enumerate(bullets):
        y = 160 + i * 56
        c.ellipse((70, y - 5, 80, y + 5), fill=t.accent)
        c.text((96, y), s, 24, anchor="lm", name=f"bullet {i + 1}", query=q)

    gx0, gy0, gx1, gy1 = 110, 400, 470, 560
    c.polygon([(gx0, gy1 - 30), (gx1 - 30, gy0 + 12), (gx1 - 30, gy1), (gx0, gy1)], fill=t.tint(t.accent, 0.8))
    c.line([(gx0, gy1 - 30), (gx1 - 30, gy0 + 12)], fill=t.accent, width=3)
    c.arrow([(gx0, gy1), (gx1, gy1)], fill=t.text, width=2, head=10)
    c.arrow([(gx0, gy1), (gx0, gy0 - 10)], fill=t.text, width=2, head=10)
    c.text((gx1 + 6, gy1), "t", 22, face="cambria", weight="italic", anchor="lm")
    c.text((gx0 - 10, gy0 - 4), "v", 22, face="cambria", weight="italic", anchor="rm")
    c.text((gx0 + 120, gy1 - 30), "area = s", 19, fill=t.text, anchor="mm")
    c.add("v-t graph", "figure", "the small v\u2013t graph", rect_pts((gx0 - 22, gy0 - 22, gx1 + 16, gy1 + 2)))

    panel = (760, 136, 1220, 486)
    c.rect(panel, fill=t.panel if t.dark else t.soft, outline=t.outline, width=2, radius=14, name="equations box",
           query="the Key equations box")
    c.text((790, 172), "Key equations", 22, weight="bold", fill=t.title, anchor="lm")
    formulas = [("v = u + at", "the formula v = u + at"), ("s = ut + \u00bdat\u00b2", "the formula s = ut + \u00bdat\u00b2"),
                ("v\u00b2 = u\u00b2 + 2as", "the formula v\u00b2 = u\u00b2 + 2as"), ("F = ma", "the formula F = ma")]
    for i, (f, q) in enumerate(formulas):
        c.text((806, 236 + i * 68), f, 38, face="cambria", weight="italic", fill=t.text, anchor="lm",
               name=f"formula {i + 1}", query=q)
    c.text((70, 618), "Example: u = 0, a = 2 m/s\u00b2, t = 5 s  \u2192  v = u + at = 10 m/s", 23, anchor="lm",
           name="example", query="the worked example line")


# ---------------------------------------------------------------- template: bar chart

def bar_chart(c: Canvas) -> None:
    t = c.t
    chrome(c, "Which Study Method Works Best?", "PSY 2104 · Learning & Memory", 18)
    px0, py0, px1, base = 150, 150, 820, 560
    scale = (base - py0 - 20) / 100
    grid = mix(t.rule, t.bg, 0.2)
    for v in range(0, 101, 20):
        y = base - v * scale
        c.line([(px0, y), (px1, y)], fill=grid if v else t.text, width=1 if v else 2)
        c.text((px0 - 12, y), str(v), 16, fill=t.muted, anchor="rm")
    s1, s2 = (42, 120, 214), (235, 104, 52)
    cats = [("Re-reading", 70, 42), ("Highlighting", 66, 38), ("Practice tests", 79, 69), ("Spaced review", 74, 63)]
    group_w = (px1 - px0) / len(cats)
    bar_w = 54
    for i, (cat, a, b) in enumerate(cats):
        cx = px0 + group_w * (i + 0.5)
        boxes = []
        for v, col, off in ((a, s1, -bar_w - 3), (b, s2, 3)):
            box = (cx + off, base - v * scale, cx + off + bar_w, base - 1)
            c.rect(box, fill=col)
            boxes.append(box)
        c.add(f"bars: {cat}", "figure", f"the pair of bars for {cat}",
              rect_pts((boxes[0][0], min(bx[1] for bx in boxes), boxes[1][2], base)))
        if cat == "Practice tests":
            c.add("tallest bar", "figure", "the tallest bar", rect_pts(boxes[0]))
        if cat == "Highlighting":
            c.add("shortest bar", "figure", "the shortest bar", rect_pts(boxes[1]))
        lab_name = f"category: {cat}"
        c.text((cx, base + 14), cat, 18, anchor="mt", name=lab_name if i in (0, 3) else None,
               query=f"the x-axis label '{cat}'" if i in (0, 3) else None)
    ybox = c.vtext((92, (py0 + base) / 2), "Average test score (%)", 19, weight="semibold", fill=t.text,
                   name="y-axis title", query="the y-axis title")
    xbox = c.text(((px0 + px1) / 2, base + 62), "Study method", 19, weight="semibold", anchor="mt",
                  name="x-axis title", query="the x-axis title")
    lx, ly = 470, py0 + 8
    legend: list[Pt] = []
    for i, (label, col) in enumerate((("Immediate test", s1), ("One week later", s2))):
        x = lx + i * 180
        legend += c.rect((x, ly - 8, x + 16, ly + 8), fill=col)
        legend += rect_pts(c.text((x + 24, ly), label, 17, anchor="lm"))
    c.add("legend", "figure", "the legend", legend)
    c.add("plot", "figure", "the whole bar chart (with its axes)",
          rect_pts((ybox[0], min(py0 - 10, bbox_of(legend)[1]), px1 + 2, xbox[3])))
    box = (880, 170, 1220, 400)
    c.rect(box, fill=t.panel, outline=t.panel_line, width=2, radius=12, name="takeaway box",
           query="the Takeaway box")
    c.text((904, 202), "Takeaway", 22, weight="bold", anchor="lm")
    lines = ["Testing yourself beats", "re-reading: scores stay", "high a week later."]
    tops = [c.text((904, 252 + i * 38), s, 21, anchor="lm") for i, s in enumerate(lines)]
    c.add("takeaway text", "text_block", "the takeaway sentence", rect_pts(
        (min(b[0] for b in tops), min(b[1] for b in tops), max(b[2] for b in tops), max(b[3] for b in tops))))
    c.text((880, 432), "Data: illustrative class survey (n = 120)", 15, weight="italic", fill=t.muted, anchor="lm",
           name="source note", query="the data source note")


# ---------------------------------------------------------------- template: dense architecture

def dense_architecture(c: Canvas) -> None:
    t = c.t
    chrome(c, "Computer Architecture: Main Components", "CSE 2105 · Computer Organization", 3)
    pkg = (60, 136, 760, 486)
    c.rect(pkg, fill=t.tint(PURPLE, 0.93), outline=t.outline, width=2.5, radius=16, name="CPU",
           query="the CPU (the big box around the core parts)")
    c.text((84, 164), "CPU", 22, weight="bold", fill=t.title, anchor="lm")

    def box(b: Box4, label: str, query: str | None = None, hue: RGB = PURPLE, shape: str = "round") -> Box4:
        fill, line = t.tint(hue, 0.84), t.ink(mix(hue, (0, 0, 0), 0.25))
        if shape == "ellipse":
            c.ellipse(b, fill=fill, outline=line, width=2, name=label, query=query or f"the {label}")
        else:
            c.rect(b, fill=fill, outline=line, width=2, radius=8 if shape == "round" else 0, name=label,
                   query=query or f"the {label}", shape=shape)
        c.text(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), label, 19, weight="semibold", anchor="mm")
        return b

    cu = box((90, 196, 290, 262), "Control Unit")
    alu = box((330, 196, 500, 262), "ALU")
    reg = box((540, 196, 730, 262), "Registers")
    l1 = box((90, 300, 290, 366), "L1 Cache", hue=TEAL)
    l2 = box((330, 300, 500, 366), "L2 Cache", hue=TEAL)
    box((540, 300, 730, 366), "MMU", query="the MMU (memory management unit)", hue=TEAL)
    box((90, 404, 290, 466), "Clock", query="the Clock", hue=ORANGE, shape="ellipse")
    c.arrow([(cu[2] + 4, 229), (alu[0] - 4, 229)], width=2, head=9)
    c.arrow([(alu[2] + 4, 229), (reg[0] - 4, 229)], width=2, head=9, both=True)
    c.arrow([(l1[2] + 4, 333), (l2[0] - 4, 333)], width=2, head=9, both=True)
    c.arrow([(190, 296), (190, 266)], width=2, head=9)

    ram = box((820, 160, 1020, 230), "RAM", hue=BLUE)
    box((1080, 160, 1280, 230), "Power Supply", hue=(110, 110, 110), shape="rect")
    rom = box((820, 380, 1020, 450), "ROM / BIOS", query="the ROM / BIOS chip", hue=BLUE, shape="rect")
    gpu = box((1080, 380, 1280, 450), "GPU", hue=GREEN)
    disp = box((1340, 380, 1540, 450), "Display", hue=GREEN, shape="rect")
    c.arrow([(pkg[2] + 4, 195), (ram[0] - 4, 195)], width=2.5, head=10, both=True)
    c.arrow([(gpu[2] + 4, 415), (disp[0] - 4, 415)], width=2.5, head=10)

    bus = (60, 540, 1540, 586)
    c.rect(bus, fill=t.accent, radius=6, name="System Bus", query="the System Bus")
    c.text(((bus[0] + bus[2]) / 2, (bus[1] + bus[3]) / 2), "System Bus  (address \u00b7 data \u00b7 control)", 20,
           weight="semibold", fill=WHITE, anchor="mm")
    for x, top in ((410, pkg[3]), ((rom[0] + rom[2]) / 2, rom[3]), ((gpu[0] + gpu[2]) / 2, gpu[3])):
        c.arrow([(x, top + 4), (x, bus[1] - 4)], width=2.5, head=10, both=True)

    bottom = [("I/O Controller", (60, 650, 280, 720), ORANGE), ("SSD", (320, 650, 500, 720), ORANGE),
              ("Network Card", (540, 650, 760, 720), ORANGE), ("USB Hub", (800, 650, 980, 720), ORANGE)]
    for label, b, hue in bottom:
        box(b, label, hue=hue)
        c.arrow([((b[0] + b[2]) / 2, bus[3] + 4), ((b[0] + b[2]) / 2, b[1] - 4)], width=2.5, head=10, both=True)
    kb = box((1060, 620, 1240, 680), "Keyboard", hue=(110, 110, 110), shape="rect")
    ms = box((1060, 712, 1240, 772), "Mouse", hue=(110, 110, 110), shape="rect")
    c.arrow([(kb[0] - 4, 650), (984, 674)], width=2, head=9)
    c.arrow([(ms[0] - 4, 742), (984, 700)], width=2, head=9)
    c.text((60, 812), "Figure 2. Components exchange data over the shared system bus.", 18, weight="italic",
           fill=t.muted, anchor="lm", name="caption", query="the figure caption")


# ---------------------------------------------------------------- registry and variants

@dataclass(frozen=True)
class Template:
    name: str
    size: tuple[int, int]
    theme: Theme
    draw: Callable[[Canvas], None]
    note: str


TEMPLATES: tuple[Template, ...] = (
    Template("network_topology", (1280, 720), light_theme(BLUE, "segoe", "underline"), network_topology,
             "Network diagram: device cards with icons, Internet cloud, arrows, callout, caption."),
    Template("flowchart_loop", (1280, 720), light_theme(TEAL, "calibri", "bar"), flowchart_loop,
             "Flowchart with terminals, parallelogram, decision diamond, Yes/No labels, loop arrow, symbol key."),
    Template("cell_organelles", (1280, 720), light_theme(GREEN, "arial", "underline"), cell_organelles,
             "Biology diagram: cell with organelles and leader-line labels (parts and labels both in GT)."),
    Template("free_body", (1280, 720), light_theme(ORANGE, "calibri", "band"), free_body,
             "Physics free-body diagram: block, four force arrows with labels, equations."),
    Template("formulas_kinematics", (1280, 720), light_theme(INDIGO, "segoe", "underline"), formulas_kinematics,
             "Text + formula slide: bullets, key equations box, small v-t graph, worked example."),
    Template("bar_chart", (1280, 720), light_theme(SLATE, "segoe", "bar"), bar_chart,
             "Grouped bar chart: rotated y-axis title, category labels, legend, takeaway box."),
    Template("dense_architecture", (1600, 900), light_theme(PURPLE, "arial", "band"), dense_architecture,
             "Dense computer-architecture block diagram: 18 small labelled boxes, nested CPU, system bus."),
)
TEMPLATE_NAMES = tuple(t.name for t in TEMPLATES)


def render(tpl: Template, theme: Theme | None = None) -> tuple[Image.Image, list[Element]]:
    c = Canvas(tpl.size[0], tpl.size[1], theme or tpl.theme)
    tpl.draw(c)
    return c.finish(), c.elements


def downscale(img: Image.Image, elements: list[Element], width: int) -> tuple[Image.Image, list[Element]]:
    s = width / img.width
    out = img.resize((width, max(1, round(img.height * s))), Image.LANCZOS)
    return out, [e.mapped(lambda pts: [(x * s, y * s) for x, y in pts]) for e in elements]


def _desk(w: int, h: int, rng: np.random.Generator) -> np.ndarray:
    """A darker desk-coloured background: wood-like grain or a laminate, float32 RGB."""
    import cv2

    palettes = [(96, 64, 42), (74, 76, 80), (58, 46, 38), (112, 84, 58), (52, 66, 60)]
    base = np.array(palettes[int(rng.integers(len(palettes)))], np.float32)
    yy = np.arange(h, dtype=np.float32)[:, None]
    low = cv2.resize(rng.normal(0, 1, (h // 60 + 2, w // 60 + 2)).astype(np.float32), (w, h),
                     interpolation=cv2.INTER_CUBIC)
    warp = 30 * cv2.resize(rng.normal(0, 1, (6, 8)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    p1, p2 = float(rng.uniform(3.5, 6.0)), float(rng.uniform(11, 17))
    grain = np.sin((yy + warp) / p1) * 0.5 + np.sin((yy + 0.6 * warp) / p2) * 0.5
    tex = 1 + 0.07 * float(rng.uniform(0.4, 1.0)) * grain + 0.06 * low
    return base[None, None, :] * tex[..., None]


def to_photo(img: Image.Image, elements: list[Element], rng: np.random.Generator,
             size: tuple[int, int] = PHOTO_SIZE) -> tuple[Image.Image, list[Element]]:
    """The slide printed on paper and photographed on a desk: perspective (a few % per corner),
    rotation (+-3 deg), drop shadow, uneven light, blur, noise. GT = bbox of the warped outline."""
    import cv2

    sw, sh = img.size
    m = round(0.035 * sw)
    paper = Image.new("RGB", (sw + 2 * m, sh + 2 * m), img.getpixel((sw // 2, sh - 2)))
    paper.paste(img, (m, m))
    pw, ph = paper.size
    w, h = size
    scale = min(rng.uniform(0.84, 0.9) * w / pw, 0.86 * h / ph)
    ang = math.radians(rng.uniform(-3.0, 3.0))
    cx, cy = w / 2 + rng.uniform(-0.02, 0.02) * w, h / 2 + rng.uniform(-0.02, 0.02) * h
    ca, sa = math.cos(ang), math.sin(ang)
    dst = []
    for x, y in ((0, 0), (pw, 0), (pw, ph), (0, ph)):
        lx, ly = (x - pw / 2) * scale, (y - ph / 2) * scale
        jx, jy = rng.uniform(-0.03, 0.03) * pw * scale, rng.uniform(-0.03, 0.03) * ph * scale
        dst.append((cx + lx * ca - ly * sa + jx, cy + lx * sa + ly * ca + jy))
    src = np.float32([(0, 0), (pw, 0), (pw, ph), (0, ph)])
    mat = cv2.getPerspectiveTransform(src, np.float32(dst))

    warped = cv2.warpPerspective(np.asarray(paper, np.float32), mat, (w, h), flags=cv2.INTER_CUBIC)
    mask = cv2.warpPerspective(np.ones((ph, pw), np.float32), mat, (w, h), flags=cv2.INTER_LINEAR)
    desk = _desk(w, h, rng)
    shift = np.float32([[1, 0, rng.uniform(6, 14)], [0, 1, rng.uniform(8, 16)]])
    shadow = cv2.GaussianBlur(cv2.warpAffine(mask, shift, (w, h)), (0, 0), 10)
    desk *= (1 - 0.55 * shadow)[..., None]
    alpha = mask[..., None]
    out = np.clip(warped, 0, 255) * alpha + desk * (1 - alpha)

    ys = (np.arange(h, dtype=np.float32) / h - 0.5)[:, None]
    xs = (np.arange(w, dtype=np.float32) / w - 0.5)[None, :]
    gx, gy = (float(v) for v in rng.uniform(-1, 1, 2))
    light = 1.0 + 0.24 * (gx * xs + gy * ys)
    light *= 1 - 0.32 * (xs ** 2 + ys ** 2)
    bx, by = dst[int(rng.integers(4))]
    blob = np.exp(-((xs * w + w / 2 - bx) ** 2 + (ys * h + h / 2 - by) ** 2) / (2 * (0.28 * w) ** 2))
    light *= 1 - float(rng.uniform(0.12, 0.22)) * blob
    cast = np.array([1.0, 0.98, 0.93] if rng.random() < 0.6 else [0.95, 0.98, 1.0], np.float32)
    out *= light.astype(np.float32)[..., None] * (cast * float(rng.uniform(0.94, 1.0)))
    out = cv2.GaussianBlur(out, (0, 0), float(rng.uniform(0.8, 1.2)))
    out += rng.standard_normal(out.shape, dtype=np.float32) * 3.0
    out += rng.standard_normal((h, w, 1), dtype=np.float32) * 2.0
    photo = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    def warp(pts: list[Pt]) -> list[Pt]:
        arr = np.float32([[(x + m, y + m) for x, y in pts]])
        return [(float(x), float(y)) for x, y in cv2.perspectiveTransform(arr, mat)[0]]

    return photo, [e.mapped(warp) for e in elements]


# ---------------------------------------------------------------- output

def save(folder: Path, name: str, img: Image.Image, elements: list[Element], meta: dict, jpeg: bool = False) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.{'jpg' if jpeg else 'png'}"
    if jpeg:
        img.save(path, quality=PHOTO_QUALITY)
    else:
        img.save(path, optimize=True)
    gt = {"image": path.name, "width": img.width, "height": img.height, **meta,
          "elements": [e.to_json(img.width, img.height) for e in elements]}
    path.with_suffix(".json").write_text(json.dumps(gt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def debug_overlay(path: Path, out_dir: Path) -> Path:
    """Draw the ground-truth boxes of one sample onto a copy, for eyeballing."""
    gt = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    img = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(img)
    f = font("arial", 12)
    colors = [(230, 0, 0), (0, 140, 0), (0, 80, 230), (200, 0, 200), (230, 120, 0), (0, 160, 160)]
    for i, el in enumerate(gt["elements"]):
        col = colors[i % len(colors)]
        x0, y0, x1, y1 = el["box"]
        d.rectangle([x0, y0, x1, y1], outline=col, width=1)
        d.text((x0 + 1, max(0, y0 - 13)), el["name"], font=f, fill=col)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{path.parent.name}__{path.stem}.png"
    img.save(out)
    return out


def variants_for(tpl: Template, sets: Sequence[str]) -> list[str]:
    out = []
    for s in sets:
        if s == "dark" and tpl.name not in DARK_TEMPLATES:
            continue
        if s == "small" and tpl.name not in SMALL_TEMPLATES:
            continue
        out.append(s)
    return out


def generate(out_dir: Path = OUT_DIR, only: Sequence[str] | None = None, sets: Sequence[str] = SETS, seed: int = 7,
             debug_dir: Path | None = None) -> list[Path]:
    """Render every requested template/variant; returns the written image paths."""
    unknown = [s for s in sets if s not in SETS] + [n for n in (only or []) if n not in TEMPLATE_NAMES]
    if unknown:
        raise ValueError(f"unknown set/template: {', '.join(unknown)}")
    written: list[Path] = []
    for tpl in TEMPLATES:
        if only and tpl.name not in only:
            continue
        clean: tuple[Image.Image, list[Element]] | None = None
        for set_name in variants_for(tpl, sets):
            rng = np.random.default_rng(zlib.crc32(f"{seed}:{tpl.name}:{set_name}".encode()))
            if set_name == "dark":
                img, els = render(tpl, dark_theme(tpl.theme))
            else:
                clean = clean or render(tpl)
                img, els = clean
                if set_name == "photo":
                    img, els = to_photo(img, els, rng)
                elif set_name == "small":
                    img, els = downscale(img, els, SMALL_WIDTH)
            meta = {"template": tpl.name, "set": set_name, "seed": seed,
                    "note": f"{tpl.note} Variant: {set_name}. Boxes are [x0, y0, x1, y1] pixels of this file."}
            path = save(out_dir / set_name, tpl.name, img, els, meta, jpeg=set_name == "photo")
            written.append(path)
            if debug_dir is not None:
                debug_overlay(path, debug_dir)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="output root (default samples/synthetic)")
    ap.add_argument("--only", default="", help=f"comma-separated templates: {', '.join(TEMPLATE_NAMES)}")
    ap.add_argument("--sets", default=",".join(SETS), help="comma-separated variants: clean,photo,dark,small")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--debug", action="store_true", help=f"also write GT overlays to {DEBUG_DIR}")
    args = ap.parse_args(argv)
    only = [s.strip() for s in args.only.split(",") if s.strip()] or None
    sets = [s.strip() for s in args.sets.split(",") if s.strip()]
    paths = generate(args.out, only, sets, args.seed, DEBUG_DIR if args.debug else None)
    for p in paths:
        gt = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
        print(f"{p.parent.name}/{p.name}: {gt['width']}x{gt['height']}, {len(gt['elements'])} elements, "
              f"{p.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
