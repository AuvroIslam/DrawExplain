"""Lesson validator: sane counts, unique ids, valid colours, spoken cues and usable geometry.

Two passes: `sanitize_steps` cleans the raw model JSON before grounding, `finalize_steps` /
`finalize_quiz` clean the built objects after geometry. Every fix is recorded in `warnings`.
"""
from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any

from app.schemas import Annotation, Geometry, Point, QuizItem, Step
from app.tutor.geometry import clamp01, clamp_box, clamp_point, is_degenerate

MAX_STEPS = 8
MAX_ANNOTATIONS = 4
MAX_QUIZ = 3
MAX_LABEL_WORDS = 6
LONG_NARRATION_WORDS = 60
FUZZY_CUE = 0.6
MIN_BOX = 0.002
MIN_LINE = 0.004
COLORS = ("red", "blue", "green", "orange", "purple")
KINDS = ("circle", "box", "underline", "highlight", "arrow", "label")
_COLOR_ALIASES = {"yellow": "orange", "gold": "orange", "brown": "orange", "pink": "purple", "violet": "purple",
                  "magenta": "purple", "teal": "green", "cyan": "blue", "navy": "blue", "black": "blue"}
_PUNCT = " \t\n.,;:!?\"'()[]{}"


def _clean(s: Any) -> str:
    return " ".join(str(s or "").split())


MAX_SKETCH_CHARS = 900
MAX_SKETCH_LINES = 16


def clean_sketch(sketch: Any) -> tuple[str | None, str | None]:
    """(Mermaid flowchart text or None, note). Strips code fences; keeps only small flowcharts."""
    text = str(sketch or "").strip()
    if not text:
        return None, None
    text = re.sub(r"^```(?:mermaid)?\s*|\s*```$", "", text).strip()
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if not lines or not re.match(r"^(flowchart|graph)\s+(TD|TB|LR|RL|BT)\b", lines[0].strip(), re.I):
        return None, "sketch dropped (not a Mermaid flowchart)"
    if len(lines) > MAX_SKETCH_LINES or len(text) > MAX_SKETCH_CHARS:
        return None, "sketch dropped (too large)"
    return "\n".join(lines), None


# ---------------------------------------------------------------- cues

def fix_cue(cue: Any, narration: str) -> tuple[str | None, str | None]:
    """Return (cue, note). A case-insensitive substring is returned in the narration's own
    spelling; otherwise the most similar phrase of about the same length; otherwise None."""
    c = _clean(cue).strip(_PUNCT)
    if not c:
        return None, "no cue"
    if not narration:
        return None, f"cue {c!r} dropped (empty narration)"
    i = narration.lower().find(c.lower())
    if i >= 0:
        return narration[i:i + len(c)], None
    words = list(re.finditer(r"\S+", narration))
    n = len(c.split())
    best_r, best = 0.0, None
    for k in range(max(1, n - 1), n + 2):
        for s in range(0, len(words) - k + 1):
            phrase = narration[words[s].start():words[s + k - 1].end()].strip(_PUNCT)
            if not phrase:
                continue
            r = SequenceMatcher(None, c.lower(), phrase.lower()).ratio()
            if r > best_r:
                best_r, best = r, phrase
    if best is not None and best_r >= FUZZY_CUE:
        return best, f"cue {c!r} not in narration; using {best!r}"
    return None, f"cue {c!r} not in narration; dropped"


# ---------------------------------------------------------------- raw model output

def sanitize_steps(raw_steps: Any, warnings: list[str], *, max_steps: int = MAX_STEPS,
                   default_color: str = "red", start: int = 1) -> list[dict]:
    """Clamp counts, normalise kinds/colours/text and repair cues of the raw step dicts."""
    steps = [s for s in (raw_steps or []) if isinstance(s, dict)]
    if len(steps) > max_steps:
        warnings.append(f"model returned {len(steps)} steps; kept the first {max_steps}")
        steps = steps[:max_steps]
    out: list[dict] = []
    for si, s in enumerate(steps, start):
        narration = _clean(s.get("narration"))
        title = _clean(s.get("title")) or f"Step {si}"
        if not narration:
            warnings.append(f"step {si}: empty narration; using the title")
            narration = title
        if len(narration.split()) > LONG_NARRATION_WORDS:
            warnings.append(f"step {si}: long narration ({len(narration.split())} words)")
        anns_in = [a for a in (s.get("annotations") or []) if isinstance(a, dict)]
        if len(anns_in) > MAX_ANNOTATIONS:
            warnings.append(f"step {si}: {len(anns_in)} drawings; kept the first {MAX_ANNOTATIONS}")
            anns_in = anns_in[:MAX_ANNOTATIONS]
        anns: list[dict] = []
        for ai, a in enumerate(anns_in, 1):
            tag = f"step {si} drawing {ai}"
            kind = _clean(a.get("kind")).lower()
            if kind not in KINDS:
                warnings.append(f"{tag}: unknown kind {kind!r}; drawing a circle")
                kind = "circle"
            color = _clean(a.get("color")).lower()
            if color not in COLORS:
                fixed = _COLOR_ALIASES.get(color, default_color)
                warnings.append(f"{tag}: colour {color!r} -> {fixed}")
                color = fixed
            cue, note = fix_cue(a.get("cue"), narration)
            if note:
                warnings.append(f"{tag}: {note}")
            text = _clean(a.get("text")) or None
            if kind == "label" and text and len(text.split()) > MAX_LABEL_WORDS:
                short = " ".join(text.split()[:MAX_LABEL_WORDS])
                warnings.append(f"{tag}: label shortened to {short!r}")
                text = short
            if kind not in ("label", "arrow"):
                text = None
            span = _clean(a.get("span")) or None
            if kind not in ("underline", "highlight"):
                span = None
            anns.append({**a, "kind": kind, "color": color, "cue": cue, "text": text, "span": span})
        sketch, note = clean_sketch(s.get("sketch"))
        if note:
            warnings.append(f"step {si}: {note}")
        out.append({"title": title, "narration": narration, "annotations": anns, "sketch": sketch})
    return out


# ---------------------------------------------------------------- built objects

def _finite_point(p: Point) -> bool:
    return math.isfinite(p.x) and math.isfinite(p.y)


def clean_geometry(kind: str, geo: Geometry) -> Geometry | None:
    """Clamp a geometry into the image; None when it is unusable for its kind."""
    box = clamp_box(geo.box) if geo.box is not None and not is_degenerate(geo.box, 0.0) else None
    label_box = clamp_box(geo.label_box) if geo.label_box is not None and not is_degenerate(geo.label_box, 0.0) else None
    points = [clamp_point(p) for p in geo.points] if geo.points and all(_finite_point(p) for p in geo.points) else None
    leader = [clamp_point(p) for p in geo.leader] if geo.leader and all(_finite_point(p) for p in geo.leader) else None
    if box is not None and is_degenerate(box, MIN_BOX):
        box = None
    if label_box is not None and is_degenerate(label_box, MIN_BOX):
        label_box = None
    if kind in ("circle", "box", "highlight"):
        return Geometry(box=box) if box is not None else None
    if kind == "underline":
        if not points or len(points) != 2 or math.dist((points[0].x, points[0].y), (points[1].x, points[1].y)) < MIN_LINE:
            return None
        return Geometry(points=points)
    if kind == "arrow":
        if not points or len(points) != 3 or math.dist((points[0].x, points[0].y), (points[2].x, points[2].y)) < MIN_LINE:
            return None
        return Geometry(points=points, label_box=label_box)
    if kind == "label":
        if label_box is None:
            return None
        if leader is not None and len(leader) != 2:
            leader = None
        return Geometry(box=box, label_box=label_box, leader=leader)
    return None


def finalize_steps(steps: list[Step], warnings: list[str], *, prefix: str = "") -> list[Step]:
    """Re-index steps from 1, give annotations unique ids "{prefix}s{step}a{n}", clamp
    geometry and drop drawings that have none left."""
    seen: set[str] = set()
    return [finalize_step(step, si, warnings, seen, prefix=prefix) for si, step in enumerate(steps, 1)]


def finalize_step(step: Step, si: int, warnings: list[str], seen: set[str], *, prefix: str = "") -> Step:
    """finalize_steps for one step (streaming): index si, unique ids tracked in `seen`."""
    anns: list[Annotation] = []
    for a in step.annotations[:MAX_ANNOTATIONS]:
        geo = clean_geometry(a.kind, a.geometry)
        if geo is None:
            warnings.append(f"step {si}: dropped a {a.kind} with no usable geometry")
            continue
        if a.color not in COLORS:
            warnings.append(f"step {si}: colour {a.color!r} -> red")
        aid = f"{prefix}s{si}a{len(anns) + 1}"
        while aid in seen:
            aid += "x"
        seen.add(aid)
        anns.append(a.model_copy(update={
            "id": aid,
            "geometry": geo,
            "color": a.color if a.color in COLORS else "red",
            "confidence": round(clamp01(a.confidence), 3),
            "cue": a.cue if a.cue and a.cue.lower() in step.narration.lower() else None,
        }))
    if not anns:
        warnings.append(f"step {si}: no drawings left (narration only)")
    return step.model_copy(update={"index": si, "annotations": anns})


def finalize_quiz(quiz: list[QuizItem], warnings: list[str]) -> list[QuizItem]:
    out: list[QuizItem] = []
    for qi, q in enumerate(quiz, 1):
        if len(out) >= MAX_QUIZ:
            warnings.append(f"quiz: kept the first {MAX_QUIZ} questions")
            break
        box = clamp_box(q.answer_box) if not is_degenerate(q.answer_box, 0.0) else None
        if box is None or is_degenerate(box, MIN_BOX) or not q.question.strip():
            warnings.append(f"quiz {qi}: dropped (no usable answer box or question)")
            continue
        out.append(q.model_copy(update={"answer_box": box}))
    return out
