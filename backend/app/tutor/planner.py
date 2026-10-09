"""Lesson planning: LLM plan -> grounding fusion -> drawing geometry -> validation."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Iterator

from app import config
from app.perception.types import PerceptionResult
from app.schemas import Annotation, Box, FollowupResponse, Lesson, LocatedTarget, QuizItem, Step
from app.tutor import prompts
from app.tutor.geometry import GeometryBuilder
from app.tutor.grounding import RELIABLE_AGREEMENT, Grounded, approx_agreement, fuse, user_selection
from app.tutor.llm import chat_json, chat_json_stream, last_meta
from app.tutor.streaming import StepStream
from app.tutor.validator import MAX_STEPS, finalize_quiz, finalize_step, finalize_steps, sanitize_steps

log = logging.getLogger("app.tutor.planner")


class _Resolver:
    """Grounds the model's {desc, ids, approx} targets, with the student's selection as "SEL"."""

    def __init__(self, pr: PerceptionResult, selection: Box | None = None):
        self.pr = pr
        self.selection = selection
        self.agreement: float | None = None
        self.trust_approx = True

    def calibrate(self, targets: list[Any]) -> None:
        """Measure how far this response's box estimates can be trusted (self-consistency)."""
        refs = [(t.get("ids"), t.get("approx")) for t in targets if isinstance(t, dict)]
        self.agreement = approx_agreement(self.pr, refs)
        self.trust_approx = self.agreement is None or self.agreement >= RELIABLE_AGREEMENT

    def __call__(self, target: Any, prefer_container: bool = True) -> Grounded | None:
        if not isinstance(target, dict):
            return None
        ids = [str(i).strip().upper() for i in (target.get("ids") or [])]
        if prompts.SEL_ID in ids:
            if self.selection is not None:
                return user_selection(self.selection, target.get("approx"), self.pr)
            ids = [i for i in ids if i != prompts.SEL_ID]
        return fuse(self.pr, ids, target.get("approx"), target.get("desc") or "", prefer_container,
                    self.trust_approx)


def _all_targets(raw_steps: list[dict], quiz: Any = None) -> list[Any]:
    out = [a.get(k) for s in raw_steps for a in s["annotations"] for k in ("target", "from_target", "to_target")]
    out += [q.get("answer") for q in (quiz or []) if isinstance(q, dict)]
    return out


def _desc(target: Any) -> str:
    return (target.get("desc") or "?") if isinstance(target, dict) else "?"


def _weakest(*items: Grounded) -> Grounded:
    return min(items, key=lambda g: g.confidence)


class _StepBuilder:
    """Grounds and lays out sanitized steps one at a time (the board fills up step by step, so the
    same builder serves the batch path and the streaming path)."""

    def __init__(self, pr: PerceptionResult, resolve: _Resolver, warnings: list[str]):
        self.pr = pr
        self.resolve = resolve
        self.warnings = warnings
        self.builder = GeometryBuilder(pr)
        self.drawn: list[Box] = []  # everything already on the board; later labels keep off it

    def build(self, si: int, raw: dict) -> Step:
        """Turn one sanitized step dict into a Step with grounded geometry (ids are set later)."""
        pr, resolve, warnings, builder, drawn = self.pr, self.resolve, self.warnings, self.builder, self.drawn
        # Pass 1: ground every target of the step, so labels can avoid all of them.
        resolved: list[tuple[dict, dict[str, Grounded | None]]] = []
        for ai, a in enumerate(raw["annotations"], 1):
            textual = a["kind"] in ("underline", "highlight")  # these need the text line itself
            g = {key: resolve(a.get(key), not textual) for key in ("target", "from_target", "to_target")}
            for key in ("target", "from_target", "to_target"):
                if a.get(key) is not None and g[key] is None:
                    warnings.append(f"step {si} drawing {ai}: could not locate {_desc(a.get(key))!r}")
            resolved.append((a, g))
        step_boxes = [g.box for _, gs in resolved for g in gs.values() if g is not None and g.box is not None]
        step_boxes += drawn

        # Pass 2: geometry per kind (circles/labels/arrows are added to the avoid list as they land).
        annotations: list[Annotation] = []
        for ai, (a, g) in enumerate(resolved, 1):
            ann = _annotation(builder, a, g, step_boxes, si, ai, warnings)
            if ann is None:
                continue
            annotations.append(ann)
            geo = ann.geometry
            new = builder.path_boxes(geo) if ann.kind == "arrow" else ([geo.box] if geo.box is not None else [])
            if geo.label_box is not None:
                new.append(geo.label_box)
            step_boxes.extend(new)
            drawn.extend(new)
        return Step(index=si, title=raw["title"], narration=raw["narration"], annotations=annotations)


def _build_steps(pr: PerceptionResult, raw_steps: list[dict], resolve: _Resolver, warnings: list[str]) -> list[Step]:
    sb = _StepBuilder(pr, resolve, warnings)
    return [sb.build(si, raw) for si, raw in enumerate(raw_steps, 1)]


def _annotation(
    builder: GeometryBuilder,
    a: dict,
    g: dict[str, Grounded | None],
    step_boxes: list[Box],
    si: int,
    ai: int,
    warnings: list[str],
) -> Annotation | None:
    kind, tag = a["kind"], f"step {si} drawing {ai}"
    common = {"id": "tmp", "kind": kind, "color": a["color"], "cue": a["cue"], "span": a["span"], "text": a["text"]}

    if kind == "arrow":
        src, dst = g["from_target"], g["to_target"] or g["target"]
        if dst is None and src is not None:  # only one end given: point at it
            src, dst = None, src
        if dst is None or dst.box is None:
            warnings.append(f"{tag}: arrow has no destination; dropped")
            return None
        avoid = [b for b in step_boxes if b is not dst.box and (src is None or b is not src.box)]
        if src is not None and src.box is not None:
            geo = builder.arrow(src.box, dst.box, a["text"], avoid)
            weak = _weakest(src, dst)
            return Annotation(**common, from_ids=src.ids, to_ids=dst.ids, geometry=geo,
                              confidence=weak.confidence, grounding=weak.grounding)
        geo = builder.pointer(dst.box, a["text"], avoid)
        return Annotation(**common, to_ids=dst.ids, geometry=geo, confidence=dst.confidence, grounding=dst.grounding)

    t = g["target"] or g["to_target"] or g["from_target"]
    if t is None or t.box is None:
        warnings.append(f"{tag}: {kind} has no target; dropped")
        return None

    if kind == "circle":
        geo = builder.circle(t.box)
    elif kind == "box":
        geo = builder.rect(t.box)
    elif kind in ("highlight", "underline"):
        make = builder.highlight if kind == "highlight" else builder.underline
        geo, used_span = make(t.box, t.ids, a["span"])
        if a["span"] and not used_span:
            warnings.append(f"{tag}: span {a['span']!r} not found in {'+'.join(t.ids) or 'target'}; using the whole target")
    elif kind == "label":
        if not a["text"]:
            warnings.append(f"{tag}: label without text; circling the target instead")
            common["kind"] = "circle"
            geo = builder.circle(t.box)
        else:
            avoid = [b for b in step_boxes if b is not t.box]
            geo = builder.label(t.box, a["text"], avoid)
    else:  # sanitize_steps only lets known kinds through
        return None
    return Annotation(**common, target_ids=t.ids, geometry=geo, confidence=t.confidence, grounding=t.grounding)


def _build_quiz(raw_quiz: Any, resolve: _Resolver, warnings: list[str]) -> list[QuizItem]:
    quiz: list[QuizItem] = []
    for qi, q in enumerate(raw_quiz or [], 1):
        if not isinstance(q, dict):
            continue
        g = resolve(q.get("answer"))
        if g is None or g.box is None:
            warnings.append(f"quiz {qi}: could not locate the answer {_desc(q.get('answer'))!r}; dropped")
            continue
        quiz.append(QuizItem(question=" ".join(str(q.get("question") or "").split()), answer_ids=g.ids,
                             answer_box=g.box, explanation=" ".join(str(q.get("explanation") or "").split())))
    return finalize_quiz(quiz, warnings)


def plan_lesson(pr: PerceptionResult, model: str | None = None) -> Lesson:
    model = model or config.OPENAI_MODEL
    t0 = time.perf_counter()
    data, meta = chat_json(model, prompts.LESSON_SYSTEM, prompts.lesson_parts(pr), prompts.LESSON_SCHEMA, "lesson")
    t1 = time.perf_counter()
    warnings: list[str] = []
    resolve = _Resolver(pr)
    raw_steps = sanitize_steps(data.get("steps"), warnings)
    resolve.calibrate(_all_targets(raw_steps, data.get("quiz")))
    steps = finalize_steps(_build_steps(pr, raw_steps, resolve, warnings), warnings)
    quiz = _build_quiz(data.get("quiz"), resolve, warnings)
    t2 = time.perf_counter()
    lesson = Lesson(
        lesson_id=uuid.uuid4().hex[:12],
        image_id=pr.perception.image_id,
        title=" ".join(str(data.get("title") or "Let's look at this page").split()),
        summary=" ".join(str(data.get("summary") or "").split()),
        steps=steps,
        quiz=quiz,
        model=model,
        timings={"llm": round(t1 - t0, 3), "ground": round(t2 - t1, 3), "total": round(t2 - t0, 3),
                 "input_tokens": float(meta.get("input_tokens", 0)), "output_tokens": float(meta.get("output_tokens", 0)),
                 **({"approx_agreement": round(resolve.agreement, 3)} if resolve.agreement is not None else {})},
        warnings=warnings,
    )
    log.info("lesson %s: %d steps, %d drawings, %d quiz, %.1fs (%s)", lesson.lesson_id, len(steps),
             sum(len(s.annotations) for s in steps), len(quiz), t2 - t0, model)
    return lesson


def stream_lesson(pr: PerceptionResult, model: str | None = None) -> Iterator[dict[str, Any]]:
    """plan_lesson, streamed: events {"type": "meta"}, {"type": "header"}, {"type": "step"} per step as
    soon as the model has written it (grounded, laid out, validated), then {"type": "lesson"} with the
    full lesson (the same steps plus the quiz). Lets the board start drawing step 1 while the model is
    still writing step 4."""
    model = model or config.OPENAI_MODEL
    t0 = time.perf_counter()
    lesson_id = uuid.uuid4().hex[:12]
    yield {"type": "meta", "lesson_id": lesson_id, "image_id": pr.perception.image_id, "model": model}
    warnings: list[str] = []
    resolve = _Resolver(pr)
    sb = _StepBuilder(pr, resolve, warnings)
    parser = StepStream()
    raw_seen: list[dict] = []
    steps: list[Step] = []
    seen_ids: set[str] = set()
    header_sent = False
    first_step: float | None = None
    for delta in chat_json_stream(model, prompts.LESSON_SYSTEM, prompts.lesson_parts(pr), prompts.LESSON_SCHEMA, "lesson"):
        for raw in parser.feed(delta):
            if not header_sent and (head := parser.header()) is not None:
                header_sent = True
                yield {"type": "header", "title": " ".join(str(head.get("title") or "").split()),
                       "summary": " ".join(str(head.get("summary") or "").split())}
            if len(steps) >= MAX_STEPS:
                continue
            clean = sanitize_steps([raw], warnings, start=len(steps) + 1)
            if not clean:
                continue
            raw_seen.append(clean[0])
            resolve.calibrate(_all_targets(raw_seen))  # self-consistency over what has arrived so far
            step = finalize_step(sb.build(len(steps) + 1, clean[0]), len(steps) + 1, warnings, seen_ids)
            steps.append(step)
            if first_step is None:
                first_step = time.perf_counter() - t0
            yield {"type": "step", "step": step.model_dump()}
    data = parser.result()
    resolve.calibrate(_all_targets(raw_seen, data.get("quiz")))
    quiz = _build_quiz(data.get("quiz"), resolve, warnings)
    total = time.perf_counter() - t0
    meta = dict(last_meta)
    lesson = Lesson(
        lesson_id=lesson_id,
        image_id=pr.perception.image_id,
        title=" ".join(str(data.get("title") or "Let's look at this page").split()),
        summary=" ".join(str(data.get("summary") or "").split()),
        steps=steps,
        quiz=quiz,
        model=model,
        timings={"llm": round(float(meta.get("seconds") or total), 3), "total": round(total, 3),
                 "first_step": round(first_step or total, 3),
                 "first_token": round(float(meta.get("first_token_seconds") or 0.0), 3),
                 "input_tokens": float(meta.get("input_tokens", 0)), "output_tokens": float(meta.get("output_tokens", 0)),
                 **({"approx_agreement": round(resolve.agreement, 3)} if resolve.agreement is not None else {})},
        warnings=warnings,
    )
    log.info("streamed lesson %s: %d steps, first step after %.1fs, total %.1fs (%s)", lesson_id, len(steps),
             first_step or total, total, model)
    yield {"type": "lesson", "lesson": lesson.model_dump()}


def answer_followup(
    pr: PerceptionResult,
    question: str,
    lesson: Lesson | None = None,
    selection: Box | None = None,
    model: str | None = None,
) -> FollowupResponse:
    model = model or config.OPENAI_MODEL
    t0 = time.perf_counter()
    data, meta = chat_json(model, prompts.FOLLOWUP_SYSTEM, prompts.followup_parts(pr, question, lesson, selection),
                           prompts.FOLLOWUP_SCHEMA, "followup")
    t1 = time.perf_counter()
    warnings: list[str] = []
    raw_steps = sanitize_steps(data.get("steps"), warnings, max_steps=2, default_color="purple")
    resolve = _Resolver(pr, selection)
    resolve.calibrate(_all_targets(raw_steps))
    steps = _build_steps(pr, raw_steps, resolve, warnings)
    steps = finalize_steps(steps, warnings, prefix=f"q{uuid.uuid4().hex[:4]}")
    t2 = time.perf_counter()
    return FollowupResponse(
        title=" ".join(str(data.get("title") or "Your question").split()),
        steps=steps,
        model=model,
        timings={"llm": round(t1 - t0, 3), "ground": round(t2 - t1, 3), "total": round(t2 - t0, 3),
                 "input_tokens": float(meta.get("input_tokens", 0)), "output_tokens": float(meta.get("output_tokens", 0))},
        warnings=warnings,
    )


def locate_targets(pr: PerceptionResult, queries: list[str], model: str | None = None) -> list[LocatedTarget]:
    model = model or config.OPENAI_MODEL
    if not queries:
        return []
    data, _ = chat_json(model, prompts.LOCATE_SYSTEM, prompts.locate_parts(pr, queries), prompts.LOCATE_SCHEMA, "locate")
    entries = [e for e in (data.get("targets") or []) if isinstance(e, dict)]
    by_query = {str(e.get("query", "")).strip().lower(): e for e in entries}
    agreement = approx_agreement(pr, [(e.get("ids"), e.get("approx")) for e in entries])
    trust = agreement is None or agreement >= RELIABLE_AGREEMENT
    out: list[LocatedTarget] = []
    for i, q in enumerate(queries):
        e = by_query.get(q.strip().lower()) or (entries[i] if i < len(entries) else None)
        g = fuse(pr, e.get("ids"), e.get("approx"), q, trust_approx=trust) if e is not None else None
        if g is None or g.box is None:
            out.append(LocatedTarget(query=q, box=None, region_ids=[], grounding="llm_only", confidence=0.0,
                                     llm_box=g.llm_box if g is not None else None))
            continue
        out.append(LocatedTarget(query=q, box=g.box, region_ids=g.ids, grounding=g.grounding,
                                 confidence=g.confidence, llm_box=g.llm_box))
    return out
