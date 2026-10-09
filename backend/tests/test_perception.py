"""Perception on real renders: shapes, labels, spans and free space vs ground truth (no network)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.perception import perceive, prepare_image
from app.schemas import Box

ROOT = Path(__file__).resolve().parents[2]
QUICK = ROOT / "samples" / "quick" / "network_basic.png"
DENSE = Path(__file__).resolve().parent / "fixtures" / "dense_diagram.png"


def _gt(path: Path) -> tuple[dict, list[tuple[str, Box]]]:
    gt = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    W, H = gt["width"], gt["height"]
    return gt, [(e["name"], Box(x=e["box"][0] / W, y=e["box"][1] / H, w=(e["box"][2] - e["box"][0]) / W,
                                h=(e["box"][3] - e["box"][1]) / H)) for e in gt["elements"]]


def _iou(a: Box, b: Box) -> float:
    iw = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    ih = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    inter = iw * ih if iw > 0 and ih > 0 else 0.0
    return inter / (a.w * a.h + b.w * b.h - inter)


@pytest.fixture(scope="module")
def network():
    return perceive(prepare_image(QUICK.read_bytes()), "network")


def test_network_shapes_have_their_labels(network):
    _, truth = _gt(QUICK)
    shapes = [r for r in network.perception.regions if r.kind == "shape"]
    for name in ("Laptop", "Switch", "Router", "Internet"):
        box = dict(truth)[name]
        best = max(shapes, key=lambda r: _iou(r.box, box))
        assert _iou(best.box, box) >= 0.85, name
        assert best.text == name
    assert len(shapes) == 4  # no word blobs, no merged row of boxes


def test_text_lines_are_children_of_their_shapes(network):
    regions = {r.id: r for r in network.perception.regions}
    router_text = next(r for r in regions.values() if r.kind == "text" and r.text == "Router")
    assert regions[router_text.parent_id].kind == "shape"


def test_span_box_finds_one_word(network):
    caption = next(r for r in network.perception.regions if r.text and r.text.startswith("A router"))
    span = network.span_box(caption.id, "router")
    assert span is not None and span.w < caption.box.w * 0.25
    assert caption.box.x - 0.005 <= span.x and span.x + span.w <= caption.box.x + caption.box.w + 0.005


def test_freespace_places_labels_on_empty_page(network):
    router = next(r for r in network.perception.regions if r.kind == "shape" and r.text == "Router")
    spot = network.freespace.place_near(router.box, 0.12, 0.05)
    assert _iou(spot, router.box) == 0 and network.freespace.ink_fraction(spot) < 0.05


def test_marked_image_and_timings(network):
    assert network.marked.size == network.image.size
    assert {"ocr", "regions", "total"} <= set(network.perception.timings)


def test_dense_diagram_recall():
    pr = perceive(prepare_image(DENSE.read_bytes()), "dense")
    _, truth = _gt(DENSE)
    hits = sum(max(_iou(r.box, b) for r in pr.perception.regions) >= 0.5 for _, b in truth)
    assert hits >= 0.95 * len(truth)


def test_native_opencv_failure_is_retried_on_a_fresh_thread(monkeypatch):
    import threading

    import cv2

    from app import perception
    from app.perception import pipeline

    monkeypatch.setattr(perception, "RETRY_PAUSE_S", 0.0)
    calls: list[str] = []
    real = pipeline.perceive

    def flaky(image, image_id, flatten=True):
        calls.append(threading.current_thread().name)
        if len(calls) == 1:
            raise cv2.error("Unknown C++ exception from OpenCV code")
        return real(image, image_id, flatten=flatten)

    monkeypatch.setattr(pipeline, "perceive", flaky)
    pr = perceive(prepare_image(QUICK.read_bytes()), "flaky")
    assert pr.perception.regions and len(calls) == 2 and calls[1] == "perceive-retry" != calls[0]

    def broken(image, image_id, flatten=True):
        raise cv2.error("Unknown C++ exception from OpenCV code")

    monkeypatch.setattr(pipeline, "perceive", broken)
    with pytest.raises(cv2.error):
        perceive(prepare_image(QUICK.read_bytes()), "broken")
