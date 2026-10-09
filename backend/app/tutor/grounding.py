"""Grounding fusion: cross-check the LLM's chosen region ids against its own box estimate.

For every target the model returns `ids` (region ids read off the Set-of-Mark image) and
`approx` (its own normalized [x, y, w, h] estimate read off the original image). Two
independent guesses that agree are trusted; when they disagree the CV regions, the OCR
text and the ink mask decide (see CONTRACT.md "Grounding fusion").
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Sequence

import cv2
import numpy as np

from app.perception.types import PerceptionResult
from app.schemas import Box, Grounding, Region
from app.tutor.geometry import (
    box_area,
    box_center,
    box_iou,
    clamp_box,
    contains,
    expand_box,
    intersection_area,
    union_box,
)

CONSENSUS_IOU = 0.3
CENTER_EXPAND = 0.10
SNAP_IOU_DISAGREE = 0.5
SNAP_IOU_NO_IDS = 0.4
TEXT_MATCH = 0.6
TEXT_ONLY_MATCH = 0.8
INK_EXPAND = 0.15
CONTAINER_RATIO = 0.05  # estimate < 5% of the chosen region's area: the id is a container
DENSE_INK = 0.6

_STOP = frozenset(
    "a an the of to in on at for and or is are this that these those it its with by from as be "
    "box word words text label region circle shape part".split()
)


@dataclass
class Grounded:
    """One resolved target: the box to draw around and how it was found."""

    box: Box | None
    ids: list[str] = field(default_factory=list)
    grounding: Grounding = "llm_only"
    confidence: float = 0.0
    llm_box: Box | None = None
    note: str = ""


# ---------------------------------------------------------------- inputs

def parse_approx(approx: Any, width: int, height: int) -> Box | None:
    """The model's [x, y, w, h] as a clamped Box. Tolerates pixel values and [x0, y0, x1, y1]."""
    if not isinstance(approx, (list, tuple)) or len(approx) != 4:
        return None
    try:
        x, y, w, h = (float(v) for v in approx)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in (x, y, w, h)):
        return None
    if max(x, y, w, h) > 1.5:  # pixels
        x, w = x / max(width, 1), w / max(width, 1)
        y, h = y / max(height, 1), h / max(height, 1)
    if (x + w > 1.03 or y + h > 1.03) and w > x and h > y and w <= 1.0 and h <= 1.0:
        w, h = w - x, h - y  # corner format
    b = clamp_box(Box(x=x, y=y, w=w, h=h))
    if b.w < 1e-3 or b.h < 1e-3:
        return None
    return b


def normalize_ids(ids: Any) -> list[str]:
    out: list[str] = []
    for i in ids or []:
        rid = str(i).strip().upper()
        if rid and rid not in out:
            out.append(rid)
    return out


# ---------------------------------------------------------------- text similarity

def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in _STOP]


def _coverage(a: Sequence[str], b: Sequence[str]) -> float:
    """Mean best fuzzy match (>= 0.75, else 0) of each token of `a` among the tokens of `b`."""
    if not a or not b:
        return 0.0
    total = 0.0
    for t in a:
        best = max(SequenceMatcher(None, t, u).ratio() for u in b)
        total += best if best >= 0.75 else 0.0
    return total / len(a)


def text_similarity(desc: str | None, text: str | None) -> float:
    """How well a target description matches a region's OCR text, 0..1 (difflib on tokens)."""
    td, tt = _tokens(desc or ""), _tokens(text or "")
    if not td or not tt:
        return 0.0
    whole = SequenceMatcher(None, " ".join(td), " ".join(tt)).ratio()
    cover = _coverage(tt, td)  # how much of the region's text the description mentions
    if len(tt) <= 3:  # short printed label: description words found in it
        cover = max(cover, 0.9 * _coverage(td, tt))
    return min(1.0, max(whole, cover))


def best_text_region(pr: PerceptionResult, desc: str) -> tuple[Region, float] | None:
    best: tuple[Region, float] | None = None
    for r in pr.perception.regions:
        if not r.text:
            continue
        s = text_similarity(desc, r.text)
        if best is None or s > best[1] or (s == best[1] and box_area(r.box) < box_area(best[0].box)):
            best = (r, s)
    return best


# ---------------------------------------------------------------- CV helpers

def best_region(pr: PerceptionResult, box: Box) -> tuple[Region, float] | None:
    best: tuple[Region, float] | None = None
    for r in pr.perception.regions:
        iou = box_iou(r.box, box)
        if best is None or iou > best[1]:
            best = (r, iou)
    return best


def tighten_to_ink(pr: PerceptionResult, box: Box, expand: float = INK_EXPAND) -> Box | None:
    """Shrink/shift an estimated box onto the ink inside it (searching a box `expand` larger).

    Keeps connected ink components that lie mostly inside the estimate; None when the area
    is empty or uniformly dense (photo texture), i.e. when there is nothing to tighten to.
    """
    ink = pr.ink
    if ink is None or getattr(ink, "ndim", 0) != 2:
        return None
    H, W = ink.shape
    ex = clamp_box(expand_box(box, expand))
    x0, y0 = int(math.floor(ex.x * W)), int(math.floor(ex.y * H))
    x1, y1 = int(math.ceil((ex.x + ex.w) * W)), int(math.ceil((ex.y + ex.h) * H))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    crop = np.ascontiguousarray(ink[y0:y1, x0:x1] > 0)
    if not crop.any() or float(crop.mean()) > DENSE_INK:
        return None
    n, _, stats, _ = cv2.connectedComponentsWithStats(crop.astype(np.uint8), connectivity=8)
    ix0, iy0 = box.x * W - x0, box.y * H - y0
    ix1, iy1 = (box.x + box.w) * W - x0, (box.y + box.h) * H - y0
    min_area = max(4, min(30, int(0.0005 * crop.size)))
    kept: list[tuple[int, int, int, int]] = []
    ink_px = 0
    for k in range(1, n):
        cx, cy, cw, ch, area = (int(v) for v in stats[k])
        if area < min_area:
            continue
        ow = min(cx + cw, ix1) - max(cx, ix0)
        oh = min(cy + ch, iy1) - max(cy, iy0)
        if ow <= 0 or oh <= 0 or (ow * oh) / float(cw * ch) < 0.5:
            continue
        kept.append((cx, cy, cx + cw, cy + ch))
        ink_px += area
    if not kept or ink_px < max(12.0, 0.002 * (ix1 - ix0) * (iy1 - iy0)):
        return None
    bx0 = min(k[0] for k in kept) + x0
    by0 = min(k[1] for k in kept) + y0
    bx1 = max(k[2] for k in kept) + x0
    by1 = max(k[3] for k in kept) + y0
    out = clamp_box(Box(x=bx0 / W, y=by0 / H, w=(bx1 - bx0) / W, h=(by1 - by0) / H))
    return out if out.w > 0 and out.h > 0 else None


def _conf(v: float) -> float:
    return round(min(1.0, max(0.0, v)), 3)


# ---------------------------------------------------------------- fusion

def fuse(pr: PerceptionResult, ids: Any, approx: Any, desc: str | None = "") -> Grounded | None:
    """Resolve one target reference. None when nothing usable remains (caller drops + warns)."""
    llm_box = parse_approx(approx, pr.width, pr.height)
    wanted = normalize_ids(ids)
    valid = [r for r in wanted if pr.region(r) is not None]
    bad = [r for r in wanted if r not in valid]
    note = f"unknown ids {', '.join(bad)}" if bad else ""

    if valid:
        regions = [pr.region(r) for r in valid]
        cv = union_box(r.box for r in regions)  # type: ignore[union-attr]
        assert cv is not None
        texts = " ".join(r.text or "" for r in regions)  # type: ignore[union-attr]
        if llm_box is None:
            sim = text_similarity(desc, texts)
            return Grounded(cv, valid, "id_only", _conf(0.55 + 0.2 * sim), None, _join(note, "no box estimate"))
        iou = box_iou(cv, llm_box)
        cx, cy = box_center(llm_box)
        center_in = contains(expand_box(cv, CENTER_EXPAND), cx, cy)
        if iou >= CONSENSUS_IOU or center_in:
            if iou < CONSENSUS_IOU and box_area(llm_box) < CONTAINER_RATIO * box_area(cv):
                snap = best_region(pr, llm_box)
                if snap is not None and snap[1] >= SNAP_IOU_DISAGREE and snap[0].id not in valid:
                    return Grounded(snap[0].box, [snap[0].id], "cv_snap", _conf(0.6 + 0.25 * snap[1]), llm_box,
                                    _join(note, f"{'+'.join(valid)} is a container; snapped to {snap[0].id}"))
            return Grounded(cv, valid, "consensus", _conf(0.9 + 0.09 * min(1.0, iou / 0.8)), llm_box, note)
        snap = best_region(pr, llm_box)
        if snap is not None and snap[1] >= SNAP_IOU_DISAGREE:
            return Grounded(snap[0].box, [snap[0].id], "cv_snap", _conf(0.6 + 0.25 * snap[1]), llm_box,
                            _join(note, f"estimate disagrees with {'+'.join(valid)}; snapped to {snap[0].id}"))
        sim = text_similarity(desc, texts)
        if sim >= TEXT_MATCH:
            return Grounded(cv, valid, "id_only", _conf(0.5 + 0.2 * sim), llm_box,
                            _join(note, f"estimate disagrees with {'+'.join(valid)} but its text matches"))
        refined = tighten_to_ink(pr, llm_box)
        if refined is not None:
            return Grounded(refined, [], "llm_refined", 0.45, llm_box,
                            _join(note, f"estimate disagrees with {'+'.join(valid)}; used inked estimate"))
        return Grounded(llm_box, [], "llm_only", 0.3, llm_box, _join(note, "raw estimate"))

    if llm_box is not None:
        snap = best_region(pr, llm_box)
        if snap is not None and snap[1] >= SNAP_IOU_NO_IDS:
            return Grounded(snap[0].box, [snap[0].id], "cv_snap", _conf(0.55 + 0.3 * snap[1]), llm_box, note)
        refined = tighten_to_ink(pr, llm_box)
        if refined is not None:
            return Grounded(refined, [], "llm_refined", 0.45, llm_box, note)
        return Grounded(llm_box, [], "llm_only", 0.3, llm_box, note)

    if desc:  # neither ids nor a box: last resort, a region whose printed text is the description
        match = best_text_region(pr, desc)
        if match is not None and match[1] >= TEXT_ONLY_MATCH:
            return Grounded(match[0].box, [match[0].id], "cv_snap", 0.5, None, _join(note, "matched by text only"))
    return None


def user_selection(selection: Box, approx: Any = None, pr: PerceptionResult | None = None) -> Grounded:
    llm_box = parse_approx(approx, pr.width, pr.height) if pr is not None else None
    return Grounded(clamp_box(selection), [], "user", 1.0, llm_box)


def overlap_ratio(a: Box, b: Box) -> float:
    """Share of `a` covered by `b`."""
    return intersection_area(a, b) / box_area(a) if box_area(a) > 0 else 0.0


def _join(*notes: str) -> str:
    return "; ".join(n for n in notes if n)
