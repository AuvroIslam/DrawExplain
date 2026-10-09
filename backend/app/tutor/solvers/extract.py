"""Detection (cheap, no model call) and extraction (one strict-JSON model call) of an algorithm's data.

The model only READS the page (which algorithm, which graph / array / parameters); code then runs the
algorithm. The extraction never simulates anything itself. Which label belongs to which edge is not asked
for: the cross-check finds it geometrically (and the shorter answer keeps the call fast).
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from app.tutor import llm, prompts

if TYPE_CHECKING:
    from app.perception.types import PerceptionResult

KINDS = ["shortest_path", "bfs", "dfs", "mst", "sort", "binary_search", "tcp_cwnd", "cpu_scheduling",
         "page_replacement", "none"]

# words that by themselves mean "a procedure with concrete state is taught here"
_STRONG = re.compile(
    r"dijkstra|bellman|kruskal|\bprim'?s?\b|spanning|shortest|cheapest\s+path|breadth[\s-]*first|depth[\s-]*first"
    r"|\bbfs\b|\bdfs\b|\bmst\b|traversal|travers(e|ing)|\bsort(s|ed|ing)?\b|bubble|insertion\s+sort|selection\s+sort"
    r"|merge\s*sort|quick\s*sort|binary\s+search|\bcwnd\b|cong\s*win|congestion|ssthresh|slow\s*start|\baimd\b"
    r"|additive\s+increase|multiplicative\s+decrease|relax(ation|ed|ing)?\b"
    r"|\bfcfs\b|first[\s-]*come|\bsjf\b|\bsrtf\b|round[\s-]*robin|time\s*(?:quantum|slice)|burst\s*time|gantt"
    r"|turnaround|cpu\s*schedul|page[\s-]*(?:replacement|faults?)|\blru\b|least[\s-]*recently[\s-]*used|belady"
    r"|reference\s+string",
    re.I,
)
# weaker words: only count for a question, or on a page that also looks like a graph / an array
_WEAK = re.compile(
    r"algorithm|graph|path|tree|search|vertex|vertices|edges?\b|nodes?\b|queue|stack|array|window|threshold"
    r"|time-?out|iteration|trace|simulat|step\s+by\s+step|\brun\b|order|visit|waiting\s+time|schedul",
    re.I,
)
_SHORT_LABEL = re.compile(r"^[A-Za-z0-9]{1,3}$")
_NUMERIC = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def page_text(pr: "PerceptionResult") -> str:
    return " ".join(r.text for r in pr.perception.regions if r.kind == "text" and r.text)


def looks_algorithmic(pr: "PerceptionResult", question: str | None = None) -> str | None:
    """Why this page/question may need a simulation ("keyword", "question", "graph-like"), or None.
    Only this page's OCR text and the question count (a document title such as "... Congestion Control"
    would make every page of the deck look algorithmic)."""
    text = page_text(pr)
    q = question or ""
    if _STRONG.search(text) or _STRONG.search(q):
        return "keyword"
    regions = pr.perception.regions
    short_shapes = sum(1 for r in regions if r.kind == "shape" and r.text and _SHORT_LABEL.match(r.text.strip()))
    numbers = sum(1 for r in regions if r.kind == "text" and r.text and _NUMERIC.match(r.text.strip()))
    graph_like = short_shapes >= 4 and numbers >= 2
    if graph_like and (_WEAK.search(text) or _WEAK.search(q) or numbers >= 4):
        return "graph-like"
    if q and _WEAK.search(q) and (graph_like or numbers >= 4 or _WEAK.search(text)):
        return "question"
    return None


SYSTEM = """You read a study page (a lecture slide, a textbook figure, notes) and extract the concrete data of the algorithm or protocol example it shows, exactly as printed, so that CODE can run the algorithm step by step. Do not run or simulate anything yourself and do not compute results.

What you receive:
- ORIGINAL image: the untouched page. Read the data from it.
- MARKED image: the same page with candidate regions outlined and tagged R1, R2, ... (found by OCR and OpenCV).
- REGION LIST: one line per region: id | kind | rough position | the text OCR read inside it.
- STUDENT QUESTION (optional): what the student wants computed.

kind = which procedure to run:
- shortest_path: shortest / cheapest path or distances in a weighted graph (Dijkstra).
- bfs, dfs: breadth-first / depth-first search or traversal of a graph or tree.
- mst: minimum spanning tree (variant "prim" or "kruskal", as the page or question says; default "prim").
- sort: sorting an array (variant "bubble", "insertion", "selection" or "merge").
- binary_search: searching a sorted array for a key.
- tcp_cwnd: how TCP's congestion window (cwnd) changes over transmission rounds: slow start, congestion avoidance / additive increase, timeouts, triple duplicate ACKs (variant "tahoe" or "reno"; default "reno").
- cpu_scheduling: CPU scheduling of processes: order, Gantt chart, waiting / turnaround times (variant "fcfs", "sjf" = non-preemptive shortest job first, "srtf" = preemptive shortest remaining time first, "rr" = round robin, "priority" = non-preemptive priority, "priority_preemptive").
- page_replacement: page or cache replacement for a sequence of references: hits, faults / misses, which page is evicted (variant "fifo", "lru" or "optimal").
- none: anything else: pages that only define terms or discuss properties (fairness, throughput or delay curves, complexity, proofs), a network or system diagram with no procedure to run, data that cannot be read, or a STUDENT QUESTION that asks why / what-is rather than for a result the procedure computes.
Choose a procedure only when running it step by step is what the page shows or what the question asks for. If the STUDENT QUESTION asks for something one of these computes (a path, distances, a visiting order, a spanning tree, the sorted array, how the window changes over time), use that kind; if it asks something conceptual, use none. Without a question, use what the page teaches.

Data (fill what the kind needs, null otherwise):
- graph (shortest_path, bfs, dfs, mst): EVERY vertex and EVERY edge drawn on the page.
  nodes: id = the vertex label exactly as printed (e.g. "A", "3", "s"); region_id = the region tagged on that vertex's circle or box in the MARKED image (or on its label text), null if none.
  edges: one entry per line drawn between two vertices: a, b = vertex ids; weight = the number printed next to THAT line (null when the graph has no weights); directed = true only when the line has an arrowhead (pointing from a to b).
  Follow every line from one end to the other; do not skip, merge or invent edges. Read each weight from the label closest to the middle of its own line.
- source: the start vertex: from the question ("from A"), else the one the page names, else null. target: the destination vertex when the question asks about reaching one vertex, else null.
- array (sort, binary_search): the values exactly as printed, in order, as strings. search_key: the value searched for (binary_search), else null.
- tcp (tcp_cwnd): initial_cwnd and ssthresh in MSS; events: [{round, type}] with type "timeout" or "triple_dup_ack", meaning the loss is detected during that transmission round (round 1 = the first round trip); rounds: how many rounds to simulate (enough to answer the question: usually through the event and 3-4 rounds after it). Use the page's numbers when it gives them. When the page gives only the rules, choose a small illustrative example instead: initial_cwnd 1, ssthresh 8, and (if the question or page involves a loss) one event a few rounds after cwnd passes ssthresh, e.g. a timeout in round 8; then set assumed = true.
- processes (cpu_scheduling): one entry per process exactly as printed: name ("P1"), arrival time (0 when the page gives none), burst / service time, priority (null unless the page gives one). quantum: the round robin time quantum, else null.
- pages (page_replacement): reference = the referenced pages or blocks in order, as strings ("7", "A"); frames = the number of frames / cache slots.
- assumed: true when any of the data is invented rather than printed on the page (say what in note).
- note: one short sentence about anything uncertain, else null."""


def _nullable(t: str) -> dict:
    return {"type": [t, "null"]}


SCHEMA: dict = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": KINDS},
        "variant": _nullable("string"),
        "graph": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"id": {"type": "string"}, "region_id": _nullable("string")},
                                "required": ["id", "region_id"],
                                "additionalProperties": False,
                            },
                        },
                        "edges": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"a": {"type": "string"}, "b": {"type": "string"},
                                               "weight": _nullable("number"), "directed": {"type": "boolean"}},
                                "required": ["a", "b", "weight", "directed"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["nodes", "edges"],
                    "additionalProperties": False,
                },
                {"type": "null"},
            ]
        },
        "source": _nullable("string"),
        "target": _nullable("string"),
        "array": {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]},
        "search_key": _nullable("string"),
        "tcp": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "initial_cwnd": {"type": "number"},
                        "ssthresh": {"type": "number"},
                        "rounds": _nullable("integer"),
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"round": {"type": "integer"},
                                               "type": {"type": "string", "enum": ["timeout", "triple_dup_ack"]}},
                                "required": ["round", "type"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["initial_cwnd", "ssthresh", "rounds", "events"],
                    "additionalProperties": False,
                },
                {"type": "null"},
            ]
        },
        "processes": {
            "anyOf": [
                {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "arrival": {"type": "number"},
                                       "burst": {"type": "number"}, "priority": _nullable("number")},
                        "required": ["name", "arrival", "burst", "priority"],
                        "additionalProperties": False,
                    },
                },
                {"type": "null"},
            ]
        },
        "quantum": _nullable("number"),
        "pages": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {"reference": {"type": "array", "items": {"type": "string"}},
                                   "frames": {"type": "integer"}},
                    "required": ["reference", "frames"],
                    "additionalProperties": False,
                },
                {"type": "null"},
            ]
        },
        "assumed": {"type": "boolean"},
        "note": _nullable("string"),
    },
    "required": ["kind", "variant", "graph", "source", "target", "array", "search_key", "tcp", "processes", "quantum",
                 "pages", "assumed", "note"],
    "additionalProperties": False,
}


def extraction_parts(pr: "PerceptionResult", question: str | None) -> list:
    n = len(pr.perception.regions)
    q = (f"STUDENT QUESTION: {json.dumps(question, ensure_ascii=False)}\n\n" if question else
         "No student question: use what the page teaches.\n\n")
    return [
        *prompts._image_parts(pr),
        f"REGION LIST ({n} regions):\n{prompts.region_lines(pr)}\n\n{q}Extract the data for the code to run.",
    ]


def extract(pr: "PerceptionResult", question: str | None, model: str) -> tuple[dict, dict]:
    """One strict-JSON model call (reasoning effort low). Raises llm.LLMError on failure."""
    return llm.chat_json(model, SYSTEM, extraction_parts(pr, question), SCHEMA, "algorithm_data",
                         reasoning_effort="low")


# ---------------------------------------------------------------- normalisation


def clean(data: Any) -> dict:
    """Defensive copy of the model's answer with predictable types (never raises)."""
    d = data if isinstance(data, dict) else {}
    kind = d.get("kind") if d.get("kind") in KINDS else "none"
    out: dict[str, Any] = {"kind": kind, "variant": _s(d.get("variant")), "source": _s(d.get("source")),
                           "target": _s(d.get("target")), "search_key": _s(d.get("search_key")),
                           "assumed": bool(d.get("assumed")), "note": _s(d.get("note"))}
    g = d.get("graph") if isinstance(d.get("graph"), dict) else None
    if g is not None:
        nodes, edges = [], []
        for n in g.get("nodes") or []:
            if isinstance(n, dict) and _s(n.get("id")):
                nodes.append({"id": _s(n.get("id")), "label": _s(n.get("label")) or _s(n.get("id")),
                              "region_id": (_s(n.get("region_id")) or "").upper() or None})
        for e in g.get("edges") or []:
            if isinstance(e, dict) and _s(e.get("a")) and _s(e.get("b")):
                w = e.get("weight")
                edges.append({"a": _s(e.get("a")), "b": _s(e.get("b")),
                              "weight": float(w) if isinstance(w, (int, float)) and not isinstance(w, bool) else None,
                              "directed": bool(e.get("directed"))})
        out["graph"] = {"nodes": nodes, "edges": edges}
    else:
        out["graph"] = None
    arr = d.get("array")
    out["array"] = [str(v) for v in arr if str(v).strip()] if isinstance(arr, list) else None
    t = d.get("tcp") if isinstance(d.get("tcp"), dict) else None
    if t is not None:
        events = []
        for ev in t.get("events") or []:
            if isinstance(ev, dict) and isinstance(ev.get("round"), int) and ev.get("type") in ("timeout", "triple_dup_ack"):
                events.append((int(ev["round"]), str(ev["type"])))
        out["tcp"] = {"initial_cwnd": _num(t.get("initial_cwnd"), 1.0), "ssthresh": _num(t.get("ssthresh"), 8.0),
                      "rounds": t.get("rounds") if isinstance(t.get("rounds"), int) else None, "events": events}
    else:
        out["tcp"] = None
    procs = []
    raw_procs = d.get("processes") if isinstance(d.get("processes"), list) else []
    for p in raw_procs:
        if isinstance(p, dict) and _s(p.get("name")) and _real(p.get("burst")) is not None:
            procs.append({"name": _s(p.get("name")), "arrival": max(_real(p.get("arrival")) or 0.0, 0.0),
                          "burst": _real(p.get("burst")), "priority": _real(p.get("priority"))})
    out["processes"] = procs or None
    q = _real(d.get("quantum"))
    out["quantum"] = q if q is not None and q > 0 else None
    pg = d.get("pages") if isinstance(d.get("pages"), dict) else {}
    raw_refs = pg.get("reference") if isinstance(pg.get("reference"), list) else []
    refs = [str(v).strip() for v in raw_refs if str(v).strip()]
    frames = pg.get("frames")
    out["pages"] = ({"reference": refs, "frames": int(frames)}
                    if refs and isinstance(frames, int) and not isinstance(frames, bool) and frames > 0 else None)
    return out


def _real(v: Any) -> float | None:
    """A JSON number as float (None for null, booleans, strings and non-finite values)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if f == f and abs(f) != float("inf") else None


def _s(v: Any) -> str | None:
    if v is None:
        return None
    t = " ".join(str(v).split())
    return t or None


def _num(v: Any, default: float) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if f > 0 else default
