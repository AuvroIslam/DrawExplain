"""Offline tests for solver-backed simulations: solvers, the pixel cross-check, detection and the
planner integration (every model call is mocked)."""
from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.perception.types import PerceptionResult
from app.schemas import Box, Perception, Region
from app.tutor import planner, prompts, solvers
from app.tutor.context import LessonContext
from app.tutor.llm import LLMError
from app.tutor.solvers import algorithms as alg
from app.tutor.solvers.crosscheck import check_graph
from app.tutor.solvers.extract import clean

INF = math.inf

# the weighted graph on page 3 of dijkstra-slides.pdf
SLIDE_EDGES = [("A", "B", 5), ("A", "H", 18), ("A", "G", 9), ("A", "I", 1), ("B", "C", 7), ("I", "C", 6), ("I", "G", 3),
               ("I", "E", 2), ("C", "D", 8), ("C", "E", 11), ("H", "G", 2), ("G", "F", 1), ("F", "E", 4), ("E", "D", 20)]


def slide_graph(directed: bool = False) -> alg.Graph:
    return alg.Graph([], [alg.Edge(a, b, float(w), directed) for a, b, w in SLIDE_EDGES])


# ---------------------------------------------------------------- Dijkstra


def test_dijkstra_slide_graph_all_distances():
    t = alg.dijkstra(slide_graph(), "A")
    dist = {k: alg.fmt(v) for k, v in t.data["dist"].items()}
    assert dist == {"A": "0", "B": "5", "C": "7", "D": "15", "E": "3", "F": "5", "G": "4", "H": "6", "I": "1"}
    assert t.data["order"] == ["A", "I", "E", "G", "B", "F", "H", "C", "D"]  # B before F: tie at 5, alphabetical
    assert "B, F tie at 5" in t.steps[4]
    assert t.data["prev"]["H"] == "G" and t.data["prev"]["D"] == "C" and t.data["prev"]["G"] == "I"
    first = t.data["iterations"][0]["relax"]  # iteration 1 relaxes every edge of A, old -> new
    assert {(r["node"], r["old"], r["new"]) for r in first} == {("B", INF, 5), ("G", INF, 9), ("H", INF, 18), ("I", INF, 1)}


def test_dijkstra_stops_when_target_is_finalized():
    t = alg.dijkstra(slide_graph(), "A", "E")
    assert t.data["order"] == ["A", "I", "E"] and t.data["stop"] == "target"
    assert len(t.steps) == 3
    assert "G 9→4 (1+3, shorter than 9" in t.steps[1]
    assert "C ∞→7" in t.steps[1] and "E ∞→3" in t.steps[1]
    assert t.data["path"] == ["A", "I", "E"]
    assert "A → I → E with total cost 3 (1 + 2)" in t.result
    assert "E is the target" in t.steps[2]


def test_dijkstra_records_edges_that_do_not_improve():
    t = alg.dijkstra(slide_graph(), "A")
    third = t.steps[2]  # E: C stays 7 because 3 + 11 = 14
    assert "C stays 7 (3+11 = 14 is not shorter)" in third and "F ∞→7" in third and "D ∞→23" in third
    assert "D 23→15" in t.steps[7]


def test_dijkstra_directed_and_errors():
    g = alg.Graph([], [alg.Edge("A", "B", 1, True), alg.Edge("B", "C", 1, True), alg.Edge("C", "A", 1, True)])
    assert alg.dijkstra(g, "B").data["dist"] == {"A": 2.0, "B": 0.0, "C": 1.0}
    with pytest.raises(alg.SolverError):
        alg.dijkstra(alg.Graph([], [alg.Edge("A", "B", -1)]), "A")
    with pytest.raises(alg.SolverError):
        alg.dijkstra(slide_graph(), "Z")
    unreachable = alg.dijkstra(alg.Graph(["Q"], [alg.Edge("A", "B", 2)]), "A", "Q")
    assert unreachable.data["path"] == [] and "cannot be reached" in unreachable.result


# ---------------------------------------------------------------- BFS / DFS


def test_bfs_queue_and_order():
    t = alg.bfs(slide_graph(), "A")
    assert t.data["order"] == ["A", "B", "G", "H", "I", "C", "F", "E", "D"]
    assert "Queue: [B, G, H, I]" in t.steps[0]
    assert "Queue: [G, H, I, C]" in t.steps[1]
    assert t.data["level"]["D"] == 3
    t2 = alg.bfs(slide_graph(), "A", "E")
    assert t2.data["path"] == ["A", "I", "E"] and t2.data["order"][-1] == "E"


def test_dfs_stack_and_order():
    g = alg.Graph([], [alg.Edge(a, b) for a, b in [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("C", "E")]])
    t = alg.dfs(g, "A")
    assert t.data["order"] == ["A", "B", "D", "C", "E"]
    assert t.data["finished"] == ["E", "C", "D", "B", "A"]
    assert "Stack: [A, B, D]" in t.steps[2]
    assert any("pop" in s for s in t.steps)
    t2 = alg.dfs(g, "A", "C")
    assert t2.data["path"] == ["A", "B", "D", "C"] and t2.data["stop"] == "target"


# ---------------------------------------------------------------- MST


def test_prim_and_kruskal_agree_on_the_slide_graph():
    p = alg.prim(slide_graph(), "A")
    k = alg.kruskal(slide_graph())
    assert p.data["total"] == k.data["total"] == 28
    assert p.data["order"] == ["A", "I", "E", "G", "F", "H", "B", "C", "D"]
    assert "G 9→3 (via I)" in p.steps[1]
    skipped = [c["edge"] for c in k.data["considered"] if not c["added"]]
    assert skipped == [("E", "F"), ("B", "C")]
    assert len(k.data["edges"]) == 8


# ---------------------------------------------------------------- arrays


def test_sorts_record_every_pass():
    data = [5, 1, 4, 2, 8]
    b = alg.bubble_sort(data)
    assert b.data["passes"] == [[1, 4, 2, 5, 8], [1, 2, 4, 5, 8], [1, 2, 4, 5, 8]] and "stops early" in b.steps[-1]
    i = alg.insertion_sort(data)
    assert i.data["passes"] == [[1, 5, 4, 2, 8], [1, 4, 5, 2, 8], [1, 2, 4, 5, 8], [1, 2, 4, 5, 8]]
    s = alg.selection_sort(data)
    assert s.data["passes"][0] == [1, 5, 4, 2, 8] and s.data["passes"][1] == [1, 2, 4, 5, 8]
    m = alg.merge_sort(data)
    assert m.data["passes"] == [[1, 5, 4, 2, 8], [1, 4, 5, 2, 8], [1, 4, 5, 2, 8], [1, 2, 4, 5, 8]]
    assert "[1, 4, 5] + [2, 8] → [1, 2, 4, 5, 8]" in m.steps[-1]
    assert alg.insertion_sort(alg.parse_values(["S", "O", "R", "T"])).data["sorted"] == ["O", "R", "S", "T"]
    assert alg.parse_values(["3", "1.5", "2"]) == [3, 1.5, 2]


def test_binary_search_steps():
    t = alg.binary_search([1, 3, 5, 7, 9, 11, 13], 11)
    assert [(p["lo"], p["hi"], p["mid"], p["cmp"]) for p in t.data["probes"]] == [(0, 6, 3, "<"), (4, 6, 5, "==")]
    assert t.data["index"] == 5
    miss = alg.binary_search([1, 3, 5, 7, 9, 11, 13], 4)
    assert miss.data["index"] == -1 and [p["mid"] for p in miss.data["probes"]] == [3, 1, 2]
    assert "not in the array" in miss.result


# ---------------------------------------------------------------- TCP


def test_tcp_timeout_halves_threshold_and_restarts_slow_start():
    t = alg.tcp_cwnd(1, 8, [(8, "timeout")], rounds=12)
    assert t.data["cwnd"] == [1, 2, 4, 8, 9, 10, 11, 12, 1, 2, 4, 6]
    rows = t.data["rows"]
    assert rows[3]["phase"] == "congestion avoidance" and rows[8]["ssthresh"] == 6
    assert "TIMEOUT: ssthresh = 12/2 = 6, cwnd = 1 MSS" in t.steps[7]
    assert "capped at ssthresh" in t.steps[10]


def test_tcp_triple_duplicate_ack_reno_and_tahoe():
    reno = alg.tcp_cwnd(1, 8, [(8, "triple_dup_ack")], rounds=11)
    assert reno.data["cwnd"] == [1, 2, 4, 8, 9, 10, 11, 12, 6, 7, 8]
    tahoe = alg.tcp_cwnd(1, 8, [(8, "triple_dup_ack")], rounds=10, variant="tahoe")
    assert tahoe.data["cwnd"][8:] == [1, 2]
    default = alg.tcp_cwnd(1, 16)  # no events: through slow start and a few rounds after
    assert default.data["cwnd"][:6] == [1, 2, 4, 8, 16, 17]


def _procs(*rows: tuple) -> list[alg.Proc]:
    return [alg.Proc(f"P{i}", *row) for i, row in enumerate(rows, 1)]


def test_cpu_scheduling_textbook_examples():
    # Silberschatz, Operating System Concepts, ch. 5 (all arrive at 0 unless given)
    fcfs = alg.cpu_schedule(_procs((0, 24), (0, 3), (0, 3)), "fcfs")
    assert fcfs.data["waiting"] == {"P1": 0, "P2": 24, "P3": 27} and fcfs.data["avg_waiting"] == 17
    sjf = alg.cpu_schedule(_procs((0, 6), (0, 8), (0, 7), (0, 3)), "sjf")
    assert sjf.data["order"] == ["P4", "P1", "P3", "P2"] and sjf.data["avg_waiting"] == 7
    srtf = alg.cpu_schedule(_procs((0, 8), (1, 4), (2, 9), (3, 5)), "srtf")
    assert srtf.data["waiting"] == {"P1": 9, "P2": 0, "P3": 15, "P4": 2} and srtf.data["avg_waiting"] == 6.5
    assert [g[0] for g in srtf.data["gantt"]] == ["P1", "P2", "P4", "P1", "P3"]
    rr = alg.cpu_schedule(_procs((0, 24), (0, 3), (0, 3)), "rr", quantum=4)
    assert rr.data["waiting"] == {"P1": 6, "P2": 4, "P3": 7} and "17/3 = 5.67" in rr.result
    pri = alg.cpu_schedule(_procs((0, 10, 3), (0, 1, 1), (0, 2, 4), (0, 1, 5), (0, 5, 2)), "priority")
    assert pri.data["order"] == ["P2", "P5", "P1", "P3", "P4"] and pri.data["avg_waiting"] == 8.2
    late = alg.cpu_schedule(_procs((2, 3), (10, 1)), "fcfs")  # idle CPU before and between processes
    assert late.data["gantt"] == [("idle", 0.0, 2), ("P1", 2, 5), ("idle", 5, 10), ("P2", 10, 11)]
    with pytest.raises(alg.SolverError):
        alg.cpu_schedule(_procs((0, 1), (0, 2)), "rr")  # no quantum


def test_sjf_gantt_chart_of_the_benchmark_page():
    # samples/bench/images/cs_sjf_gantt.png: P1(0, 1) ... P14(17, 2)
    rows = [(0, 1), (0, 1), (0, 1), (3, 1), (3, 2), (3, 3), (7, 3), (7, 2), (7, 1), (13, 1), (13, 2), (13, 3),
            (17, 1), (17, 2)]
    t = alg.cpu_schedule(_procs(*rows), "sjf")
    assert list(t.data["waiting"].values()) == [0, 1, 2, 0, 1, 3, 5, 3, 2, 2, 3, 8, 1, 2]
    assert t.data["order"][6:9] == ["P9", "P8", "P7"] and "33/14 = 2.36" in t.result
    assert "the shortest burst is P9" in next(s for s in t.steps if s.startswith("t=9:"))


def test_page_replacement_textbook_and_benchmark():
    refs = "7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1".split()  # Silberschatz, 3 frames
    assert [alg.page_replacement(refs, 3, v).data["faults"] for v in ("fifo", "lru", "optimal")] == [15, 12, 9]
    lru = alg.page_replacement(list("ABCDEDF"), 4, "lru")  # samples/bench/images/cs_lru_cache.png
    assert (lru.data["faults"], lru.data["hits"]) == (6, 1)
    assert [e["victim"] for e in lru.data["events"] if e["victim"]] == ["A", "B"]
    assert "replace B, the least recently used (last used at t=1)" in lru.steps[6]
    assert lru.data["frames"] == ["E", "F", "C", "D"]


# ---------------------------------------------------------------- pixel cross-check (fake perception)

W, H = 800, 600
NODES = {"A": (100, 300), "B": (300, 120), "C": (500, 120), "D": (700, 300), "E": (500, 480), "F": (300, 480)}
EDGES = [("A", "B", 4), ("A", "F", 2), ("B", "C", 5), ("B", "F", 1), ("C", "D", 3), ("C", "E", 6), ("E", "D", 2),
         ("F", "E", 8)]
R = 28


def _nbox(x0: float, y0: float, x1: float, y1: float) -> Box:
    return Box(x=x0 / W, y=y0 / H, w=(x1 - x0) / W, h=(y1 - y0) / H)


class _FreeSpace:
    def __init__(self, ink: np.ndarray):
        self.ink = ink

    def ink_fraction(self, box: Box) -> float:
        x0, y0 = int(box.x * W), int(box.y * H)
        crop = self.ink[max(0, y0):max(y0 + 1, int((box.y + box.h) * H)), max(0, x0):max(x0 + 1, int((box.x + box.w) * W))]
        return float(crop.mean()) if crop.size else 1.0

    def place_near(self, target: Box, w: float, h: float, avoid: list[Box] | None = None) -> Box:
        return Box(x=min(max(target.x + target.w + 0.01, 0), 1 - w), y=min(max(target.y, 0), 1 - h), w=w, h=h)


def graph_page(title: str = "Dijkstra's Algorithm", unlabeled: str | None = "F") -> PerceptionResult:
    """A synthetic graph slide: circles joined by straight lines, a weight label beside each edge's middle.
    Regions as perception would report them (the label of `unlabeled` was not read)."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    for a, b, _ in EDGES:
        (ax, ay), (bx, by) = NODES[a], NODES[b]
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        d.line([(ax + ux * R, ay + uy * R), (bx - ux * R, by - uy * R)], fill="black", width=3)
    for x, y in NODES.values():
        d.ellipse([x - R, y - R, x + R, y + R], outline="black", width=3)
    regions = [Region(id="T", kind="text", box=_nbox(250, 20, 550, 60), text=title, source="ocr")]
    for n, (x, y) in NODES.items():
        regions.append(Region(id=f"S{n}", kind="shape", box=_nbox(x - R - 1, y - R - 1, x + R + 1, y + R + 1),
                              text=None if n == unlabeled else n))
    for a, b, w in EDGES:
        (ax, ay), (bx, by) = NODES[a], NODES[b]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        L = math.hypot(bx - ax, by - ay)
        px, py = -(by - ay) / L, (bx - ax) / L  # unit normal
        cx, cy = mx + 20 * px, my + 20 * py
        regions.append(Region(id=f"W{a}{b}", kind="text", box=_nbox(cx - 8, cy - 11, cx + 8, cy + 11), text=str(w),
                              source="ocr", score=0.99))
    # ids in reading order like the real pipeline would not matter here; keep them unique and stable
    ink = np.asarray(img.convert("L")) < 200
    perception = Perception(image_id=f"graph-{title[:4]}-{unlabeled}", width=W, height=H, regions=regions)
    return PerceptionResult(perception=perception, image=img, marked=img, ink=ink, freespace=_FreeSpace(ink))


def model_read(edges=EDGES, unlabeled_id: str | None = "SF", ids: bool = True) -> tuple[list[dict], list[dict]]:
    nodes = [{"id": n, "label": n, "region_id": (f"S{n}" if ids else None) if n != "F" else (unlabeled_id if ids else None)}
             for n in NODES]
    return nodes, [{"a": a, "b": b, "weight": float(w), "directed": False} for a, b, w in edges]


def test_crosscheck_verifies_a_correct_read():
    pr = graph_page()
    nodes, edges = model_read()
    c = check_graph(pr, nodes, edges)
    assert c.nodes_mapped == 6 and c.count("verified") == 8 and c.ok
    assert {n.id: n.how for n in c.nodes}["F"] == "unlabeled"
    assert all(e.line is not None and e.line >= 0.9 for e in c.edges)
    assert {e.name(): e.label_region for e in c.edges}["C-D"] == "WCD"
    assert c.summary() == "6/6 vertices matched to regions, 8/8 edge weights verified against the printed labels"
    assert not c.possible_missing and not c.unmatched_labels


def test_crosscheck_trusts_the_pixels_over_a_misread_weight():
    pr = graph_page()
    nodes, edges = model_read([(a, b, 9 if (a, b) == ("C", "E") else w) for a, b, w in EDGES])
    c = check_graph(pr, nodes, edges)
    ce = next(e for e in c.edges if e.name() == "C-E")
    assert ce.status == "corrected" and ce.weight == 6 and ce.model_weight == 9 and ce.label_region == "WCE"
    assert c.count("verified") == 7 and c.ok and "corrected" in c.summary()
    swapped = [(a, b, {("A", "B"): 2, ("A", "F"): 4}.get((a, b), w)) for a, b, w in EDGES]
    c2 = check_graph(pr, *model_read(swapped))
    assert {e.name(): e.weight for e in c2.edges if e.status == "corrected"} == {"A-B": 4, "A-F": 2}


def test_crosscheck_adds_a_drawn_edge_the_model_missed_and_flags_an_invented_one():
    pr = graph_page()
    nodes, edges = model_read([e for e in EDGES if e[:2] != ("E", "D")] + [("A", "C", 7)])
    c = check_graph(pr, nodes, edges)
    added = [e for e in c.edges if e.status == "added"]
    assert [(e.a, e.b, e.weight) for e in added] == [("E", "D", 2.0)] or [(e.b, e.a, e.weight) for e in added] == [("E", "D", 2.0)]
    invented = next(e for e in c.edges if e.name() == "A-C")
    assert invented.status == "unverified" and invented.line is not None and invented.line < 0.9
    assert not c.ok  # one of 9 edges unconfirmed is more than 10%


def test_crosscheck_finds_vertices_without_model_region_ids():
    pr = graph_page()
    nodes, edges = model_read(ids=False)
    c = check_graph(pr, nodes, edges)
    hows = {n.id: n.how for n in c.nodes}
    assert hows["A"] == "label" and hows["F"] == "eliminated" and c.nodes_mapped == 6 and c.ok
    wrong = [dict(n, region_id="SA") if n["id"] == "B" else n for n in model_read()[0]]  # model named A's circle for B
    c2 = check_graph(pr, wrong, edges)
    assert {n.id: n.region_id for n in c2.nodes}["B"] == "SB"


# ---------------------------------------------------------------- detection


def test_detection_fires_only_on_algorithmic_pages():
    sample = Path(__file__).resolve().parents[2] / "samples" / "quick" / "network_basic.png"
    gt = json.loads(sample.with_suffix(".json").read_text(encoding="utf-8"))
    regs = [Region(id=f"R{i}", kind="shape", box=Box(x=0.1, y=0.1, w=0.1, h=0.1), text=e["name"].split(":")[0])
            for i, e in enumerate(gt["elements"], 1)]
    regs.append(Region(id="R99", kind="text", box=Box(x=0.1, y=0.8, w=0.5, h=0.05),
                       text="A router forwards packets between different networks", source="ocr"))
    plain = PerceptionResult(perception=Perception(image_id="n", width=10, height=10, regions=regs),
                             image=Image.new("RGB", (10, 10)), marked=Image.new("RGB", (10, 10)),
                             ink=np.zeros((10, 10), bool), freespace=None)  # type: ignore[arg-type]
    assert solvers.looks_algorithmic(plain) is None
    assert solvers.looks_algorithmic(plain, "What does the router do?") is None
    assert solvers.looks_algorithmic(plain, "What is the shortest path from the laptop?") == "keyword"
    assert solvers.looks_algorithmic(graph_page()) == "keyword"
    assert solvers.looks_algorithmic(graph_page(title="Example")) == "graph-like"


def text_page(lines: list[str], image_id: str = "text") -> PerceptionResult:
    """A page of OCR text lines, one per row (y grows down the page)."""
    regs = [Region(id=f"R{i}", kind="text", box=_nbox(40, 30 + 36 * i, 400, 56 + 36 * i), text=t, source="ocr")
            for i, t in enumerate(lines, 1)]
    img = Image.new("RGB", (W, H), "white")
    ink = np.zeros((H, W), bool)
    return PerceptionResult(perception=Perception(image_id=image_id, width=W, height=H, regions=regs), image=img,
                            marked=img, ink=ink, freespace=_FreeSpace(ink))


SJF_ROWS = [(0, 1), (0, 1), (0, 1), (3, 1), (3, 2), (3, 3), (7, 3), (7, 2), (7, 1), (13, 1), (13, 2), (13, 3),
            (17, 1), (17, 2)]


def _scheduling_extraction(rows=SJF_ROWS, variant: str = "sjf") -> dict:
    return {"kind": "cpu_scheduling", "variant": variant, "graph": None, "source": None, "target": None, "array": None,
            "search_key": None, "tcp": None, "quantum": None, "pages": None, "assumed": False, "note": None,
            "processes": [{"name": f"P{i}", "arrival": a, "burst": b, "priority": None}
                          for i, (a, b) in enumerate(rows, 1)]}


def test_scheduling_page_is_detected_and_its_rows_confirm_the_extraction():
    lines = ["Process (arrival time, burst time)", " ".join(str(t) for t in range(25))]
    lines += [f"P{i}({a}, {b})" for i, (a, b) in enumerate(SJF_ROWS, 1)]
    page = text_page(lines, "sjf")
    assert solvers.looks_algorithmic(page) == "keyword"
    sim = solvers.build(page, clean(_scheduling_extraction()))
    assert sim is not None and sim.verified and sim.evidence.startswith("14/14 processes")
    assert "33/14 = 2.36" in sim.prompt and "P7 5, P8 3, P9 2," in sim.prompt
    assert "t=9: ready: P7 (burst 3), P8 (burst 2), P9 (burst 1); the shortest burst is P9" in sim.prompt
    misread = [list(r) for r in SJF_ROWS]
    misread[6][1] = 4  # P7's burst read as 4: that row does not confirm it (the axis numbers must not either)
    sim = solvers.build(page, clean(_scheduling_extraction([tuple(r) for r in misread])))
    assert sim is not None and not sim.verified and sim.evidence.startswith("13/14")
    assert solvers.build(page, clean(_scheduling_extraction(variant="lottery"))) is None  # no solver for it


def test_page_replacement_build_and_quantum_physics_is_not_scheduling():
    page = text_page(["LRU cache with 4 slots", "Access sequence: A B C D E D F"], "lru")
    data = clean({"kind": "page_replacement", "variant": "LRU", "pages": {"reference": list("ABCDEDF"), "frames": 4}})
    sim = solvers.build(page, data)
    assert sim is not None and sim.verified and sim.trace.data["faults"] == 6
    assert "t=4: E is not in memory: fault, replace A, the least recently used (last used at t=0)" in sim.prompt
    physics = text_page(["Quantum mechanics: the photon", "E = hf, momentum p = h / lambda"], "physics")
    assert solvers.looks_algorithmic(physics) is None


def test_clean_drops_malformed_scheduling_and_page_data():
    d = clean({"kind": "cpu_scheduling", "processes": [{"name": "P1", "arrival": -2, "burst": 3},
                                                       {"name": "P2", "arrival": 1, "burst": "x"}, "junk",
                                                       {"name": "", "burst": 1}], "quantum": 0,
               "pages": {"reference": "ABC", "frames": True}})
    assert d["processes"] == [{"name": "P1", "arrival": 0.0, "burst": 3.0, "priority": None}]
    assert d["quantum"] is None and d["pages"] is None
    assert solvers.build(text_page(["FCFS"]), d) is None  # one process: nothing to schedule


# ---------------------------------------------------------------- simulation + planner (mocked model)


def _extraction(question_target: str | None = "E") -> dict:
    nodes, edges = model_read()
    return {"kind": "shortest_path", "variant": None, "graph": {"nodes": [{"id": n["id"], "region_id": n["region_id"]}
                                                                          for n in nodes], "edges": edges},
            "source": "A", "target": question_target, "array": None, "search_key": None, "tcp": None,
            "assumed": False, "note": None}


def _lesson_data() -> dict:
    t = {"desc": "vertex B", "ids": ["SB"], "approx": None}
    return {"title": "Shortest path", "summary": "Dijkstra on the page.",
            "steps": [{"title": "Start", "narration": "We start at A and relax its edges.", "sketch": None,
                       "annotations": [{"kind": "label", "color": "red", "target": t, "from_target": None,
                                        "to_target": None, "span": None, "text": "∞→3", "cue": "relax its edges"}]}],
            "quiz": []}


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    solvers.clear_cache()
    monkeypatch.delenv("SIM_SOLVER", raising=False)
    monkeypatch.delenv("SIM_TIMEOUT", raising=False)
    monkeypatch.delenv("SIM_MODEL", raising=False)
    yield
    solvers.clear_cache()


def test_build_runs_the_solver_on_checked_data():
    pr = graph_page()
    sim = solvers.build(pr, solvers.clean(_extraction()))
    assert sim is not None and sim.verified and sim.kind == "shortest_path"
    assert sim.trace.data["dist"]["E"] == 10 and sim.trace.data["path"] == ["A", "F", "E"]
    p = sim.prompt
    assert p.startswith("VERIFIED SIMULATION (computed by code from the graph read off this page")
    assert "Vertex -> region (draw next to these): A=SA, B=SB" in p and "F=SF" in p
    assert "B 4→3 (2+1, shorter than 4" in p
    t = sim.timings()
    assert t["verified_simulation"] == 1.0 and t["sim_edges_verified"] == 8 and t["sim_nodes_mapped"] == 6
    misread = _extraction()
    misread["graph"]["edges"][1]["weight"] = 7.0  # A-F printed 2
    sim2 = solvers.build(pr, solvers.clean(misread))
    assert sim2.trace.data["dist"]["F"] == 2 and "Corrected from the image: edge A-F" in sim2.prompt


def test_build_unweighted_bfs_uses_drawn_lines_and_kruskal_needs_no_start():
    pr = graph_page()
    data = _extraction(question_target=None)
    data.update(kind="bfs", source=None)
    for e in data["graph"]["edges"]:
        e["weight"] = None
    sim = solvers.build(pr, solvers.clean(data))
    assert sim.check is not None and not sim.check.weighted and sim.check.count("line") == 8 and sim.verified
    assert sim.trace.data["order"] == ["A", "B", "F", "C", "E", "D"]
    assert "No start vertex is given, so the run starts at A." in sim.prompt
    assert "8/8 edges confirmed as drawn lines" in sim.evidence
    k = solvers.build(pr, solvers.clean(dict(_extraction(), kind="mst", variant="kruskal", source=None)))
    assert k.trace.data["total"] == 13 and "No start vertex" not in k.prompt  # B-F 1, A-F 2, C-D 3, D-E 2, B-C 5


def test_build_other_kinds():
    pr = graph_page()
    tcp = {"kind": "tcp_cwnd", "variant": None, "graph": None, "source": None, "target": None, "array": None,
           "search_key": None, "tcp": {"initial_cwnd": 1, "ssthresh": 8, "rounds": 10, "events": [{"round": 8, "type": "timeout"}]},
           "assumed": True, "note": "example"}
    sim = solvers.build(pr, solvers.clean(tcp))
    assert sim.assumed and sim.trace.data["cwnd"] == [1, 2, 4, 8, 9, 10, 11, 12, 1, 2]
    assert "illustrative example" in sim.prompt and sim.timings()["sim_assumed"] == 1.0
    arr = dict(tcp, kind="sort", variant="insertion", tcp=None, array=["15", "11", "14"], assumed=False)
    s2 = solvers.build(pr, solvers.clean(arr))
    assert s2.trace.data["sorted"] == [11, 14, 15] and not s2.verified  # the values are not printed on this page
    printed = solvers.build(pr, solvers.clean(dict(arr, array=["5", "1", "4"])))  # the edge labels 5, 1, 4 are
    assert printed.verified and printed.evidence == "3/3 array values found in the page text"
    assert solvers.build(pr, solvers.clean(dict(arr, variant="quick"))) is None  # no solver: the lesson simulates
    assert solvers.build(pr, solvers.clean({"kind": "none"})) is None


def _capture(monkeypatch, extract_fn):
    seen: dict = {}
    monkeypatch.setattr(solvers, "extract", extract_fn)

    def fake_chat(model, system, parts, schema, name, **kw):
        seen["parts"] = parts
        return _lesson_data(), {"input_tokens": 1, "output_tokens": 1}

    def fake_stream(model, system, parts, schema, name, **kw):
        seen["stream_parts"] = parts
        return iter([json.dumps(_lesson_data())])

    monkeypatch.setattr(planner, "chat_json", fake_chat)
    monkeypatch.setattr(planner, "chat_json_stream", fake_stream)
    return seen


def test_plan_and_stream_lesson_get_the_verified_simulation(monkeypatch):
    pr = graph_page()
    calls = []

    def fake_extract(pr_, question, model):
        calls.append((question, model))
        return _extraction(), {"seconds": 0.01}

    seen = _capture(monkeypatch, fake_extract)
    ctx = LessonContext(question="how to get the shortest path from A to E")
    lesson = planner.plan_lesson(pr, model="test-model", context=ctx)
    text = seen["parts"][-1]
    assert "VERIFIED SIMULATION" in text and "STUDENT QUESTION" in text
    assert text.index("STUDENT QUESTION") < text.index("VERIFIED SIMULATION")
    assert "Teach the simulation exactly as the code computed it." in text
    assert lesson.timings["verified_simulation"] == 1.0 and lesson.timings["sim_edges_verified"] == 8
    assert lesson.warnings[0].startswith("Verified simulation computed by code: Dijkstra's algorithm from A")
    events = list(planner.stream_lesson(pr, model="test-model", context=ctx))
    assert "VERIFIED SIMULATION" in seen["stream_parts"][-1]
    assert events[-1]["lesson"]["timings"]["verified_simulation"] == 1.0
    assert calls == [("how to get the shortest path from A to E", "test-model")]  # cached per image + question


def test_non_algorithmic_page_makes_no_extraction_and_keeps_the_prompt(monkeypatch):
    pr = graph_page(title="Our team photo", unlabeled=None)
    pr.perception.regions = [r for r in pr.perception.regions if r.kind != "text" or r.id == "T"]  # no numbers

    def boom(*a, **k):
        raise AssertionError("extraction must not run on a non-algorithmic page")

    seen = _capture(monkeypatch, boom)
    assert solvers.looks_algorithmic(pr) is None
    lesson = planner.plan_lesson(pr, model="test-model")
    assert seen["parts"][-1] == prompts.lesson_parts(pr, None)[-1]
    assert "verified_simulation" not in lesson.timings and not any("simulation" in w for w in lesson.warnings)


def test_extraction_failure_leaves_the_lesson_unchanged(monkeypatch):
    pr = graph_page()

    def fail(*a, **k):
        raise LLMError("OpenAI call failed after 4 attempts")

    seen = _capture(monkeypatch, fail)
    lesson = planner.plan_lesson(pr, model="test-model")
    assert "SIMULATION" not in seen["parts"][-1] and "verified_simulation" not in lesson.timings
    assert lesson.steps and lesson.steps[0].annotations
    monkeypatch.setenv("SIM_SOLVER", "0")
    monkeypatch.setattr(solvers, "extract", lambda *a, **k: (_extraction(), {}))
    assert solvers.simulation_for(pr, None, "m") is None  # switched off


def test_slow_extraction_times_out_then_serves_the_next_lesson(monkeypatch):
    pr = graph_page()
    release = threading.Event()

    def slow(*a, **k):
        release.wait(5)
        return _extraction(), {"seconds": 3.0}

    monkeypatch.setattr(solvers, "extract", slow)
    monkeypatch.setenv("SIM_TIMEOUT", "0.05")
    t0 = time.perf_counter()
    assert solvers.simulation_for(pr, None, "m") is None
    assert time.perf_counter() - t0 < 2
    release.set()
    monkeypatch.setenv("SIM_TIMEOUT", "5")
    sim = solvers.simulation_for(pr, None, "m")
    assert sim is not None and sim.extract_seconds == 3.0
