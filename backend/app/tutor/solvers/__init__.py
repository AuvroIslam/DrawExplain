"""Solver-backed simulations: the language model READS the algorithm's data off the page, deterministic
code RUNS the algorithm, and the pixels CHECK what the model read.

    sim = simulation_for(pr, context, model)   # None when the page is not algorithmic or anything fails
    sim.prompt                                 # "VERIFIED SIMULATION ..." block for the lesson prompt
    sim.timings(), sim.note                    # lesson-level indicator (Lesson.timings / Lesson.warnings)

Flow: looks_algorithmic (regex + region structure, no model call) -> extract (one strict-JSON call,
reasoning low, cached per image + question) -> check_graph (graph kinds: vertices -> regions, edge weights
-> numeric OCR labels next to each edge, lines in the ink mask; processes: name + arrival + burst on one
printed row) -> solver (Dijkstra, BFS, DFS, Prim, Kruskal, sorts, binary search, TCP cwnd, CPU scheduling,
page replacement) -> prompt block.

Environment (read here, all optional):
    SIM_SOLVER=0        switch the feature off (default on)
    SIM_MODEL=...       model for the extraction call (default: the lesson's model)
    SIM_TIMEOUT=12      seconds a lesson waits for the extraction before going on without it
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.tutor.solvers.algorithms import (
    SORTS,
    Edge,
    Graph,
    Proc,
    SolverError,
    Trace,
    bfs,
    binary_search,
    cpu_schedule,
    dfs,
    dijkstra,
    fmt,
    kruskal,
    node_key,
    page_replacement,
    parse_values,
    prim,
    tcp_cwnd,
)
from app.tutor.solvers.crosscheck import GraphCheck, check_graph
from app.tutor.solvers.extract import clean, extract, looks_algorithmic

if TYPE_CHECKING:
    from app.perception.types import PerceptionResult
    from app.tutor.context import LessonContext

log = logging.getLogger("app.tutor.solvers")

__all__ = ["Simulation", "simulation_for", "build", "looks_algorithmic", "clear_cache"]

GRAPH_KINDS = ("shortest_path", "bfs", "dfs", "mst")
DEFAULT_TIMEOUT = 12.0
MAX_CACHED = 256  # simulations kept in memory (per image + question + model)
NAMES = {"shortest_path": "Dijkstra's algorithm", "bfs": "breadth-first search", "dfs": "depth-first search",
         "mst": "minimum spanning tree", "sort": "sorting", "binary_search": "binary search",
         "tcp_cwnd": "TCP congestion window", "cpu_scheduling": "CPU scheduling", "page_replacement": "page replacement"}


@dataclass
class Simulation:
    kind: str
    trace: Trace
    data: dict[str, Any]  # the cleaned extraction
    check: GraphCheck | None = None
    verified: bool = False  # inputs confirmed by the pixels (or an example the page does not contradict)
    assumed: bool = False  # the example data was invented (the page gives only rules)
    evidence: str = ""  # one line: what was checked against the image
    extras: list[str] = field(default_factory=list)  # region maps and corrections for the prompt
    extract_seconds: float = 0.0
    cached: bool = False

    @property
    def prompt(self) -> str:
        what = "the graph read off this page" if self.check is not None else (
            "the rules on this page and an illustrative example" if self.assumed else "the data read off this page")
        if self.verified:
            head = (f"VERIFIED SIMULATION (computed by code from {what}; follow it exactly, one or two iterations "
                    "per step, writing these values on the board next to the right elements; never contradict it)")
        else:
            head = (f"SIMULATION (computed by code from {what}; parts of the data could not be confirmed on the "
                    "image, but the computation is exact: follow it exactly, one or two iterations per step, writing "
                    "these values on the board next to the right elements; never contradict it)")
        lines = [head]
        if self.evidence:
            lines.append(f"Checked against the image: {self.evidence}.")
        lines += self.extras
        lines.append(self.trace.text())
        lines.append(_how_to_teach(self))
        return "\n".join(lines)

    @property
    def note(self) -> str:
        label = "Verified simulation" if self.verified else "Simulation"
        n = len(self.trace.steps)
        text = f"{label} computed by code: {self.trace.algorithm} ({n} step{'s' if n != 1 else ''})"
        if self.evidence:
            text += f"; checked against the image: {self.evidence}"
        if self.assumed:
            text += "; illustrative example (the page gives no numbers)"
        return text + "."

    def timings(self) -> dict[str, float]:
        t: dict[str, float] = {"verified_simulation": 1.0 if self.verified else 0.0,
                               "sim_steps": float(len(self.trace.steps)),
                               "sim_extract": round(self.extract_seconds, 3)}
        if self.cached:
            t["sim_cached"] = 1.0
        if self.assumed:
            t["sim_assumed"] = 1.0
        c = self.check
        if c is not None:
            t.update({"sim_nodes": float(len(c.nodes)), "sim_nodes_mapped": float(c.nodes_mapped),
                      "sim_edges": float(len(c.edges)), "sim_edges_verified": float(c.count("verified")),
                      "sim_edges_corrected": float(c.count("corrected")), "sim_edges_added": float(c.count("added")),
                      "sim_edges_confirmed": float(c.confirmed)})
        return t


_FIT = ("A lesson step shows at most 4 drawings, so spend them on the values: ")


def _how_to_teach(sim: Simulation) -> str:
    if sim.kind in GRAPH_KINDS:
        return ("How to teach it: go through these iterations in this order, one per step (two short ones may share a "
                "step; one that changes more than 3 values continues in the next step). " + _FIT +
                "exactly ONE label per vertex whose value changes, next to its region from the map above, written like "
                "\"B ∞→5\" or \"G 9→4\" (no extra arrow per relaxation), and a circle or a \"✓\" label on the vertex "
                "that is finalized; say which rule makes each choice; then state the result.")
    if sim.kind == "tcp_cwnd":
        return ("How to teach it: walk through these rounds in order (a few rounds per step). " + _FIT +
                "short labels such as \"cwnd 1→2→4→8\" or \"ssthresh = 6\" next to the rule on the page that produces "
                "them (slow start, additive increase, the loss rule)"
                + ("; say once that the numbers are an example" if sim.assumed else "") + "; then state the result.")
    if sim.kind == "cpu_scheduling":
        return ("How to teach it: go through the scheduling decisions in this order (one or two per step): which "
                "processes are ready and which rule picks the next one. " + _FIT +
                "a label with each process's waiting time next to its row or bar on the page, written like \"P7 wait 5\" "
                "(or its run, \"P9 9-10\"); finish with the total and the average waiting time"
                + ("; say once that the numbers are an example" if sim.assumed else "") + ".")
    if sim.kind == "page_replacement":
        return ("How to teach it: go through the references in order (a few per step): hit or fault and, for a fault "
                "with all frames full, which page leaves and why. " + _FIT +
                "labels such as \"E: fault, evicts A\" or \"D: hit\" next to the reference or frame on the page; finish "
                "with the number of faults and hits.")
    return ("How to teach it: walk through these steps in order (one or two per lesson step). " + _FIT +
            "short labels with the values (the array after each pass, lo/hi/mid) next to the data on the page; "
            "then state the result.")


# ---------------------------------------------------------------- building a simulation from extracted data


def _vertex(name: str | None, g: Graph) -> str | None:
    if not name:
        return None
    if g.has(name):
        return name
    bare = re.sub(r"^(?:vertex|node|city|router)\s+", "", name.strip(), flags=re.I).strip(" .'\"")
    for n in g.nodes:
        if n.lower() == bare.lower():
            return n
    return None


def _found_in_text(values: list[Any], text: str) -> int:
    tokens = re.findall(r"-?\d+(?:\.\d+)?|[A-Za-z]+", text)
    pool: dict[str, int] = {}
    for t in tokens:
        pool[t.lower()] = pool.get(t.lower(), 0) + 1
    hits = 0
    for v in values:
        k = fmt(v).lower()
        if pool.get(k, 0) > 0:
            pool[k] -= 1
            hits += 1
    return hits


def build(pr: "PerceptionResult", data: dict[str, Any]) -> Simulation | None:
    """Cleaned extraction -> checked inputs -> solver trace. None when there is nothing to run."""
    kind = data.get("kind") or "none"
    variant = (data.get("variant") or "").lower()
    if kind == "none":
        return None
    if kind in GRAPH_KINDS:
        g = data.get("graph") or {}
        if not g.get("edges"):
            return None
        check = check_graph(pr, g.get("nodes") or [], g["edges"])
        graph = Graph([n["id"] for n in g.get("nodes") or []], [Edge(e.a, e.b, e.weight, e.directed) for e in check.edges])
        if len(graph.nodes) < 2:
            return None
        source = _vertex(data.get("source"), graph)
        target = _vertex(data.get("target"), graph)
        extras: list[str] = []
        if source is None:
            source = graph.nodes[0]
            if not (kind == "mst" and "kruskal" in variant):
                extras.append(f"No start vertex is given, so the run starts at {source}.")
        if kind == "shortest_path":
            trace = dijkstra(graph, source, target)
        elif kind == "bfs":
            trace = bfs(graph, source, target)
        elif kind == "dfs":
            trace = dfs(graph, source, target)
        else:
            trace = kruskal(graph) if "kruskal" in variant else prim(graph, source)
        nmap = check.node_map()
        if nmap:
            extras.append("Vertex -> region (draw next to these): "
                          + ", ".join(f"{k}={nmap[k]}" for k in sorted(nmap, key=node_key)))
        # listings in a fixed order and orientation (not the model's), so a page always gives the same prompt
        def ends(e: Any) -> tuple[str, str]:
            return (e.a, e.b) if e.directed else tuple(sorted((e.a, e.b), key=node_key))  # type: ignore[return-value]

        def ename(e: Any) -> str:
            a, b = ends(e)
            return f"{a}{'->' if e.directed else '-'}{b}"

        ordered = sorted(check.edges, key=lambda e: (node_key(ends(e)[0]), node_key(ends(e)[1])))
        labelled = [e for e in ordered if e.label_region]
        if labelled:
            extras.append("Edge -> its weight label region: "
                          + ", ".join(f"{ename(e)} ({fmt(e.weight)})={e.label_region}" for e in labelled))
        extras += [f"Corrected from the image: edge {ename(e)}: {e.note}." for e in ordered
                   if e.status in ("corrected", "added")]
        unconfirmed = [ename(e) for e in ordered if e.status == "unverified"]
        if unconfirmed:
            extras.append(f"Not confirmed on the image (read by the model): {', '.join(unconfirmed)}.")
        return Simulation(kind, trace, data, check=check, verified=check.ok, evidence=check.summary(), extras=extras)

    if kind in ("sort", "binary_search"):
        values = parse_values(data.get("array") or [])
        if len(values) < 2:
            return None
        found = _found_in_text(values, " ".join(r.text or "" for r in pr.perception.regions if r.kind == "text"))
        evidence = f"{found}/{len(values)} array values found in the page text"
        assumed = bool(data.get("assumed"))
        verified = found == len(values) or assumed
        if kind == "sort":
            name = next((k for k in SORTS if k in variant), None)
            if name is None:
                return None  # quicksort, heapsort, ...: no solver, let the lesson simulate it
            trace = SORTS[name](values)
        else:
            keys = parse_values([data.get("search_key") or ""])
            if not keys or isinstance(keys[0], str) != isinstance(values[0], str):
                return None
            trace = binary_search(values, keys[0])
        return Simulation(kind, trace, data, verified=verified, assumed=assumed, evidence=evidence)

    if kind == "tcp_cwnd":
        t = data.get("tcp") or {"initial_cwnd": 1.0, "ssthresh": 8.0, "rounds": None, "events": []}
        assumed = bool(data.get("assumed")) or data.get("tcp") is None
        trace = tcp_cwnd(t["initial_cwnd"], t["ssthresh"], t.get("events") or [], t.get("rounds"),
                         "tahoe" if "tahoe" in variant else "reno")
        evidence = ""
        verified = True
        if not assumed:
            nums = [t["initial_cwnd"], t["ssthresh"]]
            found = _found_in_text(nums, " ".join(r.text or "" for r in pr.perception.regions if r.kind == "text"))
            evidence = f"{found}/2 starting values (cwnd, ssthresh) found in the page text"
            verified = found == 2
        extras = []
        if assumed:
            extras.append("The page gives the rules but no numbers, so this is an illustrative example: say so.")
        return Simulation(kind, trace, data, verified=verified, assumed=assumed, evidence=evidence, extras=extras)

    if kind == "cpu_scheduling":
        procs = data.get("processes") or []
        scheduler = _scheduler(variant)
        if len(procs) < 2 or scheduler is None:
            return None
        trace = cpu_schedule([Proc(p["name"], p["arrival"], p["burst"], p["priority"]) for p in procs], scheduler,
                             data.get("quantum"))
        assumed = bool(data.get("assumed"))
        confirmed = _process_rows(pr, procs)
        evidence = f"{confirmed}/{len(procs)} processes printed with these arrival and burst times"
        extras = ["The page gives the rules but no numbers, so this is an illustrative example: say so."] if assumed else []
        return Simulation(kind, trace, data, verified=confirmed == len(procs) or assumed, assumed=assumed,
                          evidence=evidence, extras=extras)

    if kind == "page_replacement":
        pages = data.get("pages") or {}
        refs = pages.get("reference") or []
        policy = ("lru" if re.search(r"lru|least", variant) else "opt" if re.search(r"opt|belady", variant)
                  else "fifo" if re.search(r"fifo|first", variant) else None)
        if len(refs) < 2 or policy is None:
            return None
        trace = page_replacement(refs, pages["frames"], policy)
        assumed = bool(data.get("assumed"))
        found = _found_in_text(refs, " ".join(r.text or "" for r in pr.perception.regions if r.kind == "text"))
        return Simulation(kind, trace, data, verified=found == len(refs) or assumed, assumed=assumed,
                          evidence=f"{found}/{len(refs)} references found in the page text")
    return None


def _scheduler(variant: str) -> str | None:
    """The extraction's variant ("sjf", "Round Robin", "non-preemptive priority", ...) -> a cpu_schedule name."""
    v = re.sub(r"[-_]", " ", variant.lower())
    preemptive = "preempt" in v and "non" not in v
    if re.search(r"round|\brr\b", v):
        return "rr"
    if "priority" in v:
        return "priority_preemptive" if preemptive else "priority"
    if "srtf" in v or "remaining" in v or (preemptive and re.search(r"sjf|shortest", v)):
        return "srtf"
    if re.search(r"sjf|shortest|\bspn\b", v):
        return "sjf"
    if re.search(r"fcfs|first come|fifo", v):
        return "fcfs"
    return None


_TOKEN = re.compile(r"[A-Za-z]+\d*|\d+(?:\.\d+)?")


def _process_rows(pr: "PerceptionResult", procs: list[dict[str, Any]]) -> int:
    """How many processes appear with their name, arrival and burst on one printed row of the page: one OCR
    line such as "P7(7, 3)" or a table row "P7 | 7 | 3" (text whose middle lies in the name's row band)."""
    texts = [r for r in pr.perception.regions if r.kind == "text" and r.text]
    confirmed = 0
    for p in procs:
        name = str(p["name"]).lower()
        need = [fmt(p["arrival"]), fmt(p["burst"])]
        for r in texts:
            if name not in (t.lower() for t in _TOKEN.findall(r.text or "")):
                continue
            pad = 0.25 * r.box.h
            row = " ".join(x.text or "" for x in texts if r.box.y - pad <= x.box.y + x.box.h / 2 <= r.box.y + r.box.h + pad)
            pool = [t for t in _TOKEN.findall(row) if t[0].isdigit()]
            if all(pool.count(v) >= need.count(v) for v in need):
                confirmed += 1
                break
    return confirmed


# ---------------------------------------------------------------- cached, time-boxed entry point

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sim-extract")
_lock = threading.Lock()
_cache: dict[tuple, Future] = {}


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _timeout() -> float:
    try:
        return max(0.0, float(os.getenv("SIM_TIMEOUT", str(DEFAULT_TIMEOUT))))
    except ValueError:
        return DEFAULT_TIMEOUT


def _run(pr: "PerceptionResult", question: str | None, model: str) -> Simulation | None:
    t0 = time.perf_counter()
    raw, meta = extract(pr, question, model)  # LLMError propagates: the caller forgets the key, a later lesson retries
    data = clean(raw)
    seconds = float(meta.get("original_seconds") or meta.get("seconds") or (time.perf_counter() - t0))
    try:
        sim = build(pr, data)
    except SolverError as exc:
        log.info("simulation skipped for %s: %s", pr.perception.image_id, exc)
        return None
    except Exception:  # a bug here must not make every later lesson on this page re-run the extraction
        log.exception("simulation build failed for %s", pr.perception.image_id)
        return None
    if sim is None:
        log.info("no simulation for %s (kind %s)", pr.perception.image_id, data.get("kind"))
        return None
    sim.extract_seconds, sim.cached = seconds, bool(meta.get("cached"))
    log.info("simulation for %s: %s, %d steps, %s (extract %.1fs)", pr.perception.image_id, sim.trace.algorithm,
             len(sim.trace.steps), sim.evidence or "no image check", seconds)
    return sim


def simulation_for(pr: "PerceptionResult", context: "LessonContext | None" = None,
                   model: str | None = None) -> Simulation | None:
    """The simulation for this page (and the student's question), or None. Never raises; waits at most
    SIM_TIMEOUT seconds (a late result is still cached for the next lesson on this page)."""
    try:
        if os.getenv("SIM_SOLVER", "1") == "0":
            return None
        question = context.question if context is not None else None
        why = looks_algorithmic(pr, question)
        if why is None:
            return None
        from app import config

        model = os.getenv("SIM_MODEL") or model or config.OPENAI_MODEL
        p = pr.perception
        key = (p.image_id, p.width, p.height, len(p.regions), " ".join((question or "").lower().split()), model)
        with _lock:
            fut = _cache.get(key)
            if fut is None:
                while len(_cache) >= MAX_CACHED:  # oldest first (dicts keep insertion order)
                    del _cache[next(iter(_cache))]
                fut = _pool.submit(_run, pr, question, model)
                _cache[key] = fut
                log.info("simulation extraction started for %s (%s)", p.image_id, why)
    except Exception:
        log.exception("simulation setup failed")
        return None
    try:
        return fut.result(timeout=_timeout())
    except FutureTimeout:
        log.warning("simulation extraction for %s still running after %.0fs; lesson goes on without it",
                    pr.perception.image_id, _timeout())
        return None
    except Exception as exc:
        with _lock:
            if _cache.get(key) is fut:
                del _cache[key]
        log.warning("simulation skipped for %s: %s: %s", pr.perception.image_id, type(exc).__name__,
                    str(exc).splitlines()[0][:200] if str(exc) else "")
        return None
