"""Offline tests for the tutor: grounding fusion branches and the full planner path (mocked LLM)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.perception.types import PerceptionResult
from app.schemas import Box, Perception, Region
from app.tutor import grounding, planner
from app.tutor.geometry import box_iou

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "quick" / "network_basic.png"
GT = json.loads(SAMPLE.with_suffix(".json").read_text(encoding="utf-8"))
W, H = GT["width"], GT["height"]


def _nbox(x0: float, y0: float, x1: float, y1: float) -> Box:
    return Box(x=x0 / W, y=y0 / H, w=(x1 - x0) / W, h=(y1 - y0) / H)


class _FreeSpace:
    """Minimal FreeSpaceMap over an ink mask (the real one lives in perception)."""

    def __init__(self, ink: np.ndarray):
        self.ink = ink

    def ink_fraction(self, box: Box) -> float:
        h, w = self.ink.shape
        x0, y0 = int(box.x * w), int(box.y * h)
        x1, y1 = max(x0 + 1, int((box.x + box.w) * w)), max(y0 + 1, int((box.y + box.h) * h))
        crop = self.ink[max(0, y0):y1, max(0, x0):x1]
        return float(crop.mean()) if crop.size else 1.0

    def place_near(self, target: Box, w: float, h: float, avoid: list[Box] | None = None) -> Box:
        cands = [Box(x=target.x + target.w + 0.01, y=target.y, w=w, h=h),
                 Box(x=target.x, y=target.y - h - 0.01, w=w, h=h),
                 Box(x=target.x, y=target.y + target.h + 0.01, w=w, h=h)]
        def score(b: Box) -> float:
            b = Box(x=min(max(b.x, 0), 1 - w), y=min(max(b.y, 0), 1 - h), w=w, h=h)
            return self.ink_fraction(b) + sum(box_iou(b, a) for a in (avoid or []))
        best = min(cands, key=score)
        return Box(x=min(max(best.x, 0), 1 - w), y=min(max(best.y, 0), 1 - h), w=w, h=h)


@pytest.fixture(scope="module")
def pr() -> PerceptionResult:
    img = Image.open(SAMPLE).convert("RGB")
    ink = np.asarray(img.convert("L")) < 200
    els = {e["name"].split(":")[0]: e for e in GT["elements"]}
    regions = [
        Region(id="R1", kind="text", box=_nbox(*els["title"]["box"]), text="How Packets Travel Across Networks", source="ocr"),
        Region(id="R2", kind="shape", box=_nbox(*els["Internet"]["box"]), text="Internet"),
        Region(id="R3", kind="shape", box=_nbox(*els["Laptop"]["box"]), text="Laptop"),
        Region(id="R4", kind="shape", box=_nbox(*els["Switch"]["box"]), text="Switch"),
        Region(id="R5", kind="shape", box=_nbox(*els["Router"]["box"]), text="Router"),
        Region(id="R6", kind="text", box=_nbox(*els["caption"]["box"]),
               text="A router forwards packets between different networks", source="ocr"),
    ]
    perception = Perception(image_id="test", width=W, height=H, regions=regions)
    return PerceptionResult(perception=perception, image=img, marked=img, ink=ink, freespace=_FreeSpace(ink))


def _approx(b: Box, dx: float = 0.0) -> list[float]:
    return [b.x + dx, b.y, b.w, b.h]


# ---------------------------------------------------------------- fusion branches

def test_consensus_uses_cv_box(pr):
    router = pr.region("R5").box
    g = grounding.fuse(pr, ["R5"], _approx(router, 0.01), "Router box")
    assert g.grounding == "consensus" and g.box == router and g.confidence >= 0.9


def test_disagreement_snaps_to_matching_region(pr):
    switch = pr.region("R4").box
    g = grounding.fuse(pr, ["R5"], _approx(switch), "Switch box")  # wrong id, right estimate
    assert g.grounding == "cv_snap" and g.ids == ["R4"]


def test_no_ids_snaps_by_iou(pr):
    g = grounding.fuse(pr, [], _approx(pr.region("R3").box), "Laptop")
    assert g.grounding == "cv_snap" and g.ids == ["R3"]


def test_unknown_id_and_no_box_falls_back_to_text(pr):
    g = grounding.fuse(pr, ["R99"], None, "Router")
    assert g is not None and g.ids == ["R5"]


def test_nothing_usable_returns_none(pr):
    assert grounding.fuse(pr, [], None, "") is None


# ---------------------------------------------------------------- planner (mocked LLM)

def _t(rid: str, desc: str, pr: PerceptionResult) -> dict:
    return {"desc": desc, "ids": [rid], "approx": _approx(pr.region(rid).box)}


def _canned(pr: PerceptionResult) -> dict:
    ann = lambda **k: {"kind": "circle", "color": "red", "target": None, "from_target": None, "to_target": None,
                       "span": None, "text": None, "cue": None, **k}
    return {
        "title": "How packets travel",
        "summary": "Packets hop from device to device until they reach the internet.",
        "steps": [
            {"title": "The big picture", "narration": "This slide shows how packets travel across networks.",
             "annotations": [ann(kind="highlight", color="orange", target=_t("R1", "title", pr), span="Packets",
                                 cue="packets travel")]},
            {"title": "Meet the router", "narration": "The router I just circled connects your network to the internet.",
             "annotations": [ann(target=_t("R5", "Router box", pr), cue="router I just circled"),
                             ann(kind="label", color="red", target=_t("R5", "Router box", pr), text="forwards packets",
                                 cue="connects your network"),
                             ann(kind="arrow", color="blue", from_target=_t("R5", "Router", pr),
                                 to_target=_t("R2", "Internet", pr), text="out", cue="to the internet")]},
            {"title": "The key sentence", "narration": "Notice the word router in this sentence.",
             "annotations": [ann(kind="underline", color="green", target=_t("R6", "caption", pr), span="router",
                                 cue="word router"),
                             ann(kind="box", color="purple", target={"desc": "x", "ids": ["R42"], "approx": None},
                                 cue="not in narration at all")]},
        ],
        "quiz": [{"question": "Tap the device that forwards packets.", "answer": _t("R5", "Router", pr),
                  "explanation": "Routers forward packets between networks."}],
    }


def test_plan_lesson_offline(pr, monkeypatch):
    monkeypatch.setattr(planner, "chat_json", lambda *a, **k: (_canned(pr), {"input_tokens": 1, "output_tokens": 1}))
    lesson = planner.plan_lesson(pr, model="test-model")
    assert [s.index for s in lesson.steps] == [1, 2, 3]
    kinds = [a.kind for s in lesson.steps for a in s.annotations]
    assert kinds == ["highlight", "circle", "label", "arrow", "underline"]  # the unlocatable box was dropped
    ids = [a.id for s in lesson.steps for a in s.annotations]
    assert len(set(ids)) == len(ids)
    router = pr.region("R5").box
    circle = lesson.steps[1].annotations[0]
    assert circle.grounding == "consensus" and circle.target_ids == ["R5"]
    cb = circle.geometry.box  # the ellipse must enclose the router box
    assert cb.x <= router.x and cb.y <= router.y and cb.x + cb.w >= router.x + router.w and cb.y + cb.h >= router.y + router.h
    label = lesson.steps[1].annotations[1]
    assert label.geometry.label_box is not None and box_iou(label.geometry.label_box, router) == 0
    arrow = lesson.steps[1].annotations[2]
    assert arrow.from_ids == ["R5"] and arrow.to_ids == ["R2"] and len(arrow.geometry.points) == 3
    underline = lesson.steps[2].annotations[0]
    (p0, p1) = underline.geometry.points
    caption = pr.region("R6").box
    assert caption.x - 0.01 <= p0.x < p1.x <= caption.x + caption.w + 0.01
    assert p1.x - p0.x < caption.w * 0.5  # the span, not the whole line
    for s in lesson.steps:
        for a in s.annotations:
            assert a.cue is None or a.cue.lower() in s.narration.lower()
    assert any("could not locate" in w for w in lesson.warnings)
    assert len(lesson.quiz) == 1 and lesson.quiz[0].answer_ids == ["R5"]


def test_followup_selection_offline(pr, monkeypatch):
    sel = Box(x=0.5, y=0.4, w=0.2, h=0.2)
    data = {"title": "About that box", "steps": [{
        "title": "Your selection", "narration": "This part you circled is the router.",
        "annotations": [{"kind": "circle", "color": "purple", "target": {"desc": "selection", "ids": ["SEL"], "approx": None},
                         "from_target": None, "to_target": None, "span": None, "text": None, "cue": "part you circled"}]}]}
    monkeypatch.setattr(planner, "chat_json", lambda *a, **k: (data, {}))
    fu = planner.answer_followup(pr, "what is this?", selection=sel, model="test-model")
    a = fu.steps[0].annotations[0]
    assert a.grounding == "user" and a.color == "purple" and a.id.startswith("q")


def test_locate_targets_offline(pr, monkeypatch):
    data = {"targets": [{"query": "the Router", "ids": ["R5"], "approx": _approx(pr.region("R5").box)},
                        {"query": "the Switch", "ids": [], "approx": _approx(pr.region("R4").box)}]}
    monkeypatch.setattr(planner, "chat_json", lambda *a, **k: (data, {}))
    out = planner.locate_targets(pr, ["the Router", "the Switch"], model="test-model")
    assert [o.region_ids for o in out] == [["R5"], ["R4"]]
    assert out[0].grounding == "consensus" and out[1].grounding == "cv_snap"


def _chunks(text: str, seed: int) -> list[str]:
    import random

    rnd, out, i = random.Random(seed), [], 0
    while i < len(text):
        n = rnd.randint(1, 40)
        out.append(text[i:i + n])
        i += n
    return out


def test_step_stream_yields_each_step_once(pr):
    from app.tutor.streaming import StepStream

    data = _canned(pr)
    for seed in range(5):
        parser, got = StepStream(), []
        for c in _chunks(json.dumps(data, ensure_ascii=False), seed):
            got += parser.feed(c)
        assert got == data["steps"]
        assert parser.header()["title"] == data["title"] and parser.result() == data


def test_stream_lesson_matches_batch_lesson(pr, monkeypatch):
    data = _canned(pr)
    monkeypatch.setattr(planner, "chat_json", lambda *a, **k: (data, {"input_tokens": 1, "output_tokens": 1}))
    monkeypatch.setattr(planner, "chat_json_stream", lambda *a, **k: iter(_chunks(json.dumps(data), 7)))
    batch = planner.plan_lesson(pr, model="test-model")
    events = list(planner.stream_lesson(pr, model="test-model"))
    assert [e["type"] for e in events] == ["meta", "header", "step", "step", "step", "lesson"]
    streamed = events[-1]["lesson"]
    assert [s["index"] for s in streamed["steps"]] == [1, 2, 3]
    for a, b in zip(batch.steps, streamed["steps"]):
        assert [x.id for x in a.annotations] == [x["id"] for x in b["annotations"]]
        assert [x.geometry.model_dump() for x in a.annotations] == [x["geometry"] for x in b["annotations"]]
    assert events[2]["step"] == streamed["steps"][0] and len(streamed["quiz"]) == 1


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to call OpenAI")
def test_plan_lesson_live():
    from app.perception import perceive, prepare_image

    real = perceive(prepare_image(SAMPLE.read_bytes()), "live")
    lesson = planner.plan_lesson(real)
    assert 3 <= len(lesson.steps) <= 8 and any(s.annotations for s in lesson.steps)
