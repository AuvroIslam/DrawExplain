"""Grounding fusion: cross-check the LLM's chosen region ids against its own box estimate.

For every target the model returns `ids` (region ids read off the Set-of-Mark image) and
`approx` (its own normalized [x, y, w, h] estimate read off the original image). Two
independent guesses that agree are trusted; when they disagree the CV regions, the OCR
text and the ink mask decide (see CONTRACT.md "Grounding fusion").
"""
from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Sequence

import cv2
import numpy as np

from app import config
from app.perception import gpu
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

log = logging.getLogger("app.tutor.grounding")

CONSENSUS_IOU = 0.3
CENTER_EXPAND = 0.10
SNAP_IOU_DISAGREE = 0.5
SNAP_IOU_NO_IDS = 0.4
TEXT_MATCH = 0.6
TEXT_ONLY_MATCH = 0.8
INK_EXPAND = 0.15
CONTAINER_RATIO = 0.05  # estimate < 5% of the chosen region's area: the id is a container
DENSE_INK = 0.6
RELIABLE_AGREEMENT = 0.5  # share of a response's targets whose estimate agrees with its ids

# a description asking for the words themselves keeps the text line instead of its container
_TEXTUAL = frozenset("word words label labels text term terms phrase title heading caption sentence line "
                     "formula equation letter letters name".split())

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

def promote_label(pr: PerceptionResult, ids: list[str], desc: str | None) -> list[str]:
    """A text line that labels a shape names the shape: "the Router" means the Router box, so the
    drawing goes around the box. Kept as text when the description asks for the words themselves."""
    if not ids or set(re.findall(r"[a-z]+", (desc or "").lower())) & _TEXTUAL:
        return ids
    parents = set()
    for rid in ids:
        r = pr.region(rid)
        if r is None or r.kind != "text" or not r.parent_id:
            return ids
        p = pr.region(r.parent_id)
        while p is not None and p.kind == "text_block" and p.parent_id:
            p = pr.region(p.parent_id)
        if p is None or p.kind != "shape":
            return ids
        parents.add(p.id)
    return sorted(parents) if len(parents) == 1 else ids


def _agrees(cv: Box, llm_box: Box) -> bool:
    cx, cy = box_center(llm_box)
    return box_iou(cv, llm_box) >= CONSENSUS_IOU or contains(expand_box(cv, CENTER_EXPAND), cx, cy)


def approx_agreement(pr: PerceptionResult, refs: Sequence[tuple[Any, Any]]) -> float | None:
    """Self-consistency of one model response: the share of targets (with valid ids and a box
    estimate) whose estimate agrees with the chosen regions. None when nothing can be compared.

    A model whose estimates mostly agree with its own region choices localizes reliably, so its
    estimate may arbitrate when the two disagree; one that mostly disagrees (e.g. gpt-4.1-mini,
    whose raw boxes score ~0.1 IoU in our eval) is guessing, and its region ids are trusted instead."""
    n = agree = 0
    for ids, approx in refs:
        llm_box = parse_approx(approx, pr.width, pr.height)
        regions = [pr.region(r) for r in normalize_ids(ids)]
        regions = [r for r in regions if r is not None]
        if llm_box is None or not regions:
            continue
        cv = union_box(r.box for r in regions)
        n += 1
        agree += _agrees(cv, llm_box)  # type: ignore[arg-type]
    agreement = agree / n if n else None
    if config.GPU_ENABLED:  # optional: one batched SAM call for every target that refinement may touch
        try:
            sam_prefetch(pr, refs, agreement is None or agreement >= RELIABLE_AGREEMENT)
        except Exception:  # noqa: BLE001 - refinement is an extra; grounding never depends on it
            log.warning("SAM prefetch failed", exc_info=True)
    return agreement


def fuse(pr: PerceptionResult, ids: Any, approx: Any, desc: str | None = "",
         prefer_container: bool = True, trust_approx: bool = True) -> Grounded | None:
    """Resolve one target reference. None when nothing usable remains (caller drops + warns).
    prefer_container: circle a labelled shape rather than its label text (off for underline/highlight).
    trust_approx: let the model's own box estimate overrule its region ids (see approx_agreement).
    With the GPU service on, a low-confidence result is tightened to its SAM mask (sam_refine)."""
    g = _fuse(pr, ids, approx, desc, prefer_container, trust_approx)
    if g is not None and config.GPU_ENABLED:
        try:
            return sam_refine(pr, g)
        except Exception:  # noqa: BLE001 - keep the CPU result
            log.warning("SAM refinement failed", exc_info=True)
    return g


def _fuse(pr: PerceptionResult, ids: Any, approx: Any, desc: str | None = "",
          prefer_container: bool = True, trust_approx: bool = True) -> Grounded | None:
    llm_box = parse_approx(approx, pr.width, pr.height)
    wanted = normalize_ids(ids)
    if prefer_container:
        wanted = promote_label(pr, wanted, desc)
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
        if not trust_approx:  # the response's estimates are unreliable: the regions decide
            sim = text_similarity(desc, texts)
            if _agrees(cv, llm_box):
                return Grounded(cv, valid, "consensus", _conf(0.85 + 0.1 * sim), llm_box, note)
            return Grounded(cv, valid, "id_only", _conf(0.6 + 0.2 * sim), llm_box,
                            _join(note, "estimates unreliable in this response; trusted the region ids"))
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
        return Grounded(cv, valid, "id_only", _conf(0.45 + 0.2 * sim), llm_box,
                        _join(note, "estimate disagrees and is not on any ink; kept the region ids"))

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


# ---------------------------------------------------------------- optional GPU refinement (SAM 2.1)
#
# Targets the CPU pipeline could only locate from the model's own estimate (llm_refined, llm_only)
# and targets that are leftover-ink "figure" regions are sent to SAM 2.1 as box prompts (the box
# grown a little); the mask's tight box replaces the target box when SAM is confident and the mask
# stays a plausible part of the box. All targets of one response go in one batched call, made by
# approx_agreement() (which every caller runs once per response before grounding its targets);
# fuse() then only reads the cached masks, so grounding a single target never waits on the network.

SAM_GROUNDINGS = ("llm_refined", "llm_only")
SAM_FIGURES = True  # also refine targets whose regions are all "figure" (leftover ink) regions
SAM_PROMPT_EXPAND = 0.08  # prompt with the target box grown by 8%
SAM_MIN_SCORE = 0.75  # the mask IoU that SAM itself predicts
# the mask box may shrink the target box to 10% of its area (a loose estimate around a small thing) or grow
# it up to 2x (ink tightening cut off a faint or thin part); anything else is a different object
SAM_MIN_AREA = 0.10
SAM_MAX_AREA = 2.0


def _sam_prompt(pr: PerceptionResult, g: Grounded | None) -> Box | None:
    """The box to refine, or None when this result is not refined."""
    if g is None or g.box is None or g.grounding == "user":
        return None
    if g.grounding in SAM_GROUNDINGS:
        return g.box
    if SAM_FIGURES and g.ids:
        regions = [pr.region(i) for i in g.ids]
        if all(r is not None and r.kind == "figure" for r in regions):
            return g.box
    return None


def _sam_key(b: Box) -> tuple[float, float, float, float]:
    return (round(b.x, 4), round(b.y, 4), round(b.w, 4), round(b.h, 4))


def _sam_cache(pr: PerceptionResult) -> dict:
    return pr.__dict__.setdefault("_sam_masks", {})


def sam_prefetch(pr: PerceptionResult, refs: Sequence[tuple[Any, Any]], trust_approx: bool = True) -> int:
    """Segment, in one GPU call, every target of a response that sam_refine may touch (each target is
    fused both with and without label promotion, without its description, so the set is a superset).
    Returns the number of new masks; 0 when the service is off, cold or failing."""
    if not gpu.sam_enabled() or getattr(pr, "image", None) is None:
        return 0
    cache = _sam_cache(pr)
    want: dict[tuple, Box] = {}
    for ids, approx in refs:
        for prefer_container in (True, False):
            b = _sam_prompt(pr, _fuse(pr, ids, approx, "", prefer_container, trust_approx))
            if b is not None and _sam_key(b) not in cache:
                want.setdefault(_sam_key(b), b)
    if not want or not gpu.ready("segment"):
        return 0
    W, H = pr.width, pr.height
    prompts = [clamp_box(expand_box(b, SAM_PROMPT_EXPAND)) for b in want.values()]
    t0 = time.perf_counter()
    res = gpu.segment(pr.image, [[p.x * W, p.y * H, (p.x + p.w) * W, (p.y + p.h) * H] for p in prompts])
    if res is None:
        return 0
    for k, r in zip(want, res):
        cache[k] = r
    log.info("SAM prefetch: %d boxes in %.2fs", len(res), time.perf_counter() - t0)
    return len(res)


def sam_refine(pr: PerceptionResult, g: Grounded) -> Grounded:
    """g with its box tightened to the prefetched SAM mask, when there is one and it is trustworthy."""
    cache = pr.__dict__.get("_sam_masks")
    b = _sam_prompt(pr, g) if cache else None
    r = cache.get(_sam_key(b)) if (cache and b is not None) else None
    if not r or g.box is None:
        return g
    score = float(r.get("score") or 0.0)
    x0, y0, x1, y1 = (float(v) for v in r["box"])
    m = clamp_box(Box(x=x0 / pr.width, y=y0 / pr.height, w=(x1 - x0) / pr.width, h=(y1 - y0) / pr.height))
    ratio = box_area(m) / max(box_area(g.box), 1e-9)
    cx, cy = box_center(m)
    if (score < SAM_MIN_SCORE or not SAM_MIN_AREA <= ratio <= SAM_MAX_AREA
            or not contains(expand_box(g.box, 0.05), cx, cy)):
        return g
    conf = g.confidence + 0.15 * score if g.grounding in SAM_GROUNDINGS else g.confidence
    return Grounded(m, list(g.ids), g.grounding, _conf(conf), g.llm_box,
                    _join(g.note, f"SAM-refined (mask score {score:.2f})"))


def user_selection(selection: Box, approx: Any = None, pr: PerceptionResult | None = None) -> Grounded:
    llm_box = parse_approx(approx, pr.width, pr.height) if pr is not None else None
    return Grounded(clamp_box(selection), [], "user", 1.0, llm_box)


def overlap_ratio(a: Box, b: Box) -> float:
    """Share of `a` covered by `b`."""
    return intersection_area(a, b) / box_area(a) if box_area(a) > 0 else 0.0


def _join(*notes: str) -> str:
    return "; ".join(n for n in notes if n)
