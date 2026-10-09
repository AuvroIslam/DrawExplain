"""Deterministic solvers that produce step-by-step traces of classic algorithms.

Pure Python, no I/O. Every solver returns a Trace: the setup, one line per iteration (with the old->new
values the iteration changes) and the result, plus machine-readable `data` for tests and checks.
Conventions (stated in every trace so the narration can say them): ties are broken alphabetically
(numerically for numeric labels), neighbours are visited in that same order.
"""
from __future__ import annotations

import math
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

INF = math.inf
ARROW = "→"  # ->
CHECK = "✓"  # check mark
_NUM = re.compile(r"^-?\d+(?:\.\d+)?$")


class SolverError(ValueError):
    """The extracted data cannot be simulated (missing source, negative weight, ...)."""


@dataclass
class Trace:
    kind: str  # shortest_path | bfs | dfs | mst | sort | binary_search | tcp_cwnd
    algorithm: str  # human name, e.g. "Dijkstra's algorithm from A to E"
    setup: list[str]  # inputs and the initial state
    steps: list[str]  # one line per iteration, in order
    result: str  # the final answer in one or two sentences
    data: dict[str, Any] = field(default_factory=dict)  # machine-readable final state
    notes: list[str] = field(default_factory=list)  # conventions and assumptions

    def text(self) -> str:
        lines = [f"Algorithm: {self.algorithm}."]
        lines += self.notes
        lines += self.setup
        lines += self.steps
        lines.append(f"Result: {self.result}")
        return "\n".join(lines)


# ---------------------------------------------------------------- formatting


def fmt(x: Any) -> str:
    """5.0 -> "5", inf -> "∞", 2.5 -> "2.5"."""
    if x is None:
        return "?"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, (int, float)):
        if isinstance(x, float):
            if math.isinf(x):
                return "∞" if x > 0 else "-∞"
            if x.is_integer():
                return str(int(x))
            return f"{x:g}"
        return str(x)
    return str(x)


def node_key(n: Any) -> tuple:
    """Natural order: numeric labels by value, then text labels alphabetically (case-insensitive)."""
    s = str(n)
    if _NUM.match(s):
        return (0, float(s), "")
    return (1, s.lower(), s)


def parse_values(values: Iterable[Any]) -> list[Any]:
    """Array values as printed -> numbers when every value is numeric, else stripped strings."""
    raw = [str(v).strip() for v in values if str(v).strip()]
    nums = []
    for v in raw:
        t = v.replace(",", ".") if v.count(",") == 1 and "." not in v else v
        if not _NUM.match(t):
            return raw
        f = float(t)
        nums.append(int(f) if f.is_integer() else f)
    return nums


def _list(values: Sequence[Any]) -> str:
    return "[" + ", ".join(fmt(v) for v in values) + "]"


# ---------------------------------------------------------------- graphs


@dataclass
class Edge:
    a: str
    b: str
    w: float | None = None
    directed: bool = False

    def name(self) -> str:
        return f"{self.a}{'->' if self.directed else '-'}{self.b}"


class Graph:
    def __init__(self, nodes: Iterable[str], edges: Iterable[Edge]):
        self.edges = [e for e in edges if e.a != e.b]
        names = {str(n) for n in nodes} | {e.a for e in self.edges} | {e.b for e in self.edges}
        self.nodes = sorted(names, key=node_key)
        self._out: dict[str, list[tuple[str, float | None, Edge]]] = {n: [] for n in self.nodes}
        for e in self.edges:
            self._out[e.a].append((e.b, e.w, e))
            if not e.directed:
                self._out[e.b].append((e.a, e.w, e))
        for n in self.nodes:
            self._out[n].sort(key=lambda t: (node_key(t[0]), t[1] if t[1] is not None else 0))

    @property
    def weighted(self) -> bool:
        return any(e.w is not None for e in self.edges)

    @property
    def directed(self) -> bool:
        return any(e.directed for e in self.edges)

    def out(self, u: str) -> list[tuple[str, float | None, Edge]]:
        """(neighbour, weight, edge) leaving u, neighbours in natural order."""
        return self._out.get(u, [])

    def neighbours(self, u: str) -> list[str]:
        seen: list[str] = []
        for v, _, _ in self.out(u):
            if v not in seen:
                seen.append(v)
        return seen

    def has(self, n: str | None) -> bool:
        return n is not None and n in self._out


def _need(g: Graph, node: str | None, what: str) -> str:
    if node is None or not g.has(node):
        raise SolverError(f"{what} {node!r} is not a vertex of the graph")
    return node


def _path(prev: dict[str, str | None], target: str) -> list[str]:
    path, cur, seen = [], target, set()
    while cur is not None and cur not in seen:
        seen.add(cur)
        path.append(cur)
        cur = prev.get(cur)
    return path[::-1]


def _ties(cands: list[str], value: dict[str, float], best: str) -> str:
    same = [v for v in cands if value[v] == value[best]]
    if len(same) < 2:
        return ""
    return f" ({', '.join(same)} tie at {fmt(value[best])}; ties go in alphabetical order, so {best})"


def dijkstra(g: Graph, source: str, target: str | None = None) -> Trace:
    source = _need(g, source, "source")
    if target is not None:
        target = _need(g, target, "target")
    if not g.weighted:
        g = Graph(g.nodes, [Edge(e.a, e.b, 1.0, e.directed) for e in g.edges])
        unweighted = True
    else:
        unweighted = False
    missing = [e.name() for e in g.edges if e.w is None]
    if missing:
        raise SolverError(f"edges without a weight: {', '.join(missing)}")
    if any(e.w < 0 for e in g.edges):  # type: ignore[operator]
        raise SolverError("Dijkstra's algorithm needs non-negative edge weights")

    dist: dict[str, float] = {v: INF for v in g.nodes}
    prev: dict[str, str | None] = {v: None for v in g.nodes}
    dist[source] = 0.0
    done: list[str] = []
    steps: list[str] = []
    iterations: list[dict[str, Any]] = []
    stop = "all"
    while True:
        cands = [v for v in g.nodes if v not in done and dist[v] < INF]
        if not cands:
            if len(done) < len(g.nodes):
                stop = "unreachable"
            break
        u = min(cands, key=lambda v: (dist[v], node_key(v)))
        done.append(u)
        k = len(done)
        rec: dict[str, Any] = {"select": u, "dist": dist[u], "relax": []}
        iterations.append(rec)
        head = (f"Iteration {k}: the unvisited vertex with the smallest distance is {u} ({fmt(dist[u])})"
                f"{_ties(cands, dist, u)}, so {u} is finalized {CHECK}.")
        if target is not None and u == target:
            stop = "target"
            steps.append(f"{head} {u} is the target, so the algorithm stops here: its distance {fmt(dist[u])} is final.")
            break
        parts = []
        for v, w, e in g.out(u):
            if v in done:
                continue
            cand = dist[u] + float(w)  # type: ignore[arg-type]
            old = dist[v]
            label = f"{u}-{v} ({fmt(w)})"
            if cand < old:
                dist[v], prev[v] = cand, u
                rec["relax"].append({"node": v, "old": old, "new": cand, "weight": w, "improved": True})
                why = "" if math.isinf(old) else f", shorter than {fmt(old)}"
                parts.append(f"{label}: {v} {fmt(old)}{ARROW}{fmt(cand)} ({fmt(dist[u])}+{fmt(w)}{why}; "
                             f"predecessor {u})")
            else:
                rec["relax"].append({"node": v, "old": old, "new": old, "weight": w, "improved": False})
                parts.append(f"{label}: {v} stays {fmt(old)} ({fmt(dist[u])}+{fmt(w)} = {fmt(cand)} is not shorter)")
        if parts:
            steps.append(f"{head} Relax its edges: " + "; ".join(parts) + ".")
        else:
            steps.append(f"{head} It has no edges to unvisited vertices, so nothing changes.")
        if len(done) == len(g.nodes):
            break

    final = ", ".join(f"{v}={fmt(dist[v])}{' ' + CHECK if v in done else ''}" for v in g.nodes)
    data: dict[str, Any] = {"dist": dict(dist), "prev": dict(prev), "done": list(done), "order": list(done),
                            "iterations": iterations, "stop": stop}
    if target is not None:
        if dist[target] < INF and target in done:
            path = _path(prev, target)
            ws = [_edge_weight(g, a, b) for a, b in zip(path, path[1:])]
            sums = " + ".join(fmt(w) for w in ws)
            result = (f"shortest path {f' {ARROW} '.join(path)} with total cost {fmt(dist[target])}"
                      f"{f' ({sums})' if len(ws) > 1 else ''}. Distances when the algorithm stops: {final}.")
            data["path"] = path
        else:
            result = f"{target} cannot be reached from {source}. Distances when the algorithm stops: {final}."
            data["path"] = []
        name = f"Dijkstra's algorithm from {source}, stopping as soon as {target} is finalized"
    else:
        preds = ", ".join(f"{v}<-{prev[v]}" for v in g.nodes if prev[v] is not None)
        result = f"final shortest distances from {source}: {final}. Predecessors: {preds or 'none'}."
        name = f"Dijkstra's algorithm from {source} to every vertex"
    notes = ["Rules: start with distance 0 at the source and ∞ everywhere else; each iteration finalizes the "
             "unvisited vertex with the smallest tentative distance (ties alphabetical) and relaxes every edge "
             "from it to an unvisited vertex (new = its distance + edge weight, kept if smaller)."]
    if unweighted:
        notes.append("The graph has no printed weights, so every edge counts 1.")
    setup = [f"Start: dist {source}=0, every other vertex ∞; nothing finalized."]
    return Trace("shortest_path", name, setup, steps, result, data, notes)


def _edge_weight(g: Graph, a: str, b: str) -> float | None:
    best = None
    for v, w, _ in g.out(a):
        if v == b and w is not None and (best is None or w < best):
            best = w
    return best


def bfs(g: Graph, source: str, target: str | None = None) -> Trace:
    source = _need(g, source, "source")
    if target is not None:
        target = _need(g, target, "target")
    queue: deque[str] = deque([source])
    seen = {source}
    parent: dict[str, str | None] = {source: None}
    level = {source: 0}
    order: list[str] = []
    steps: list[str] = []
    stop = "all"
    while queue:
        u = queue.popleft()
        order.append(u)
        head = f"Step {len(order)}: dequeue {u} and visit it (visit order: {', '.join(order)})."
        if target is not None and u == target:
            stop = "target"
            steps.append(f"{head} {u} is the target, so the search stops. Queue left: {_list(list(queue))}.")
            break
        added = []
        for v in g.neighbours(u):
            if v not in seen:
                seen.add(v)
                parent[v], level[v] = u, level[u] + 1
                queue.append(v)
                added.append(v)
        if added:
            steps.append(f"{head} Enqueue its unvisited neighbours {', '.join(added)} (level {level[u] + 1}, parent {u}). "
                         f"Queue: {_list(list(queue))}.")
        else:
            steps.append(f"{head} No unvisited neighbours to add. Queue: {_list(list(queue))}.")
    data: dict[str, Any] = {"order": order, "parent": parent, "level": level, "stop": stop}
    if target is not None:
        if target in parent:
            path = _path(parent, target)
            data["path"] = path
            result = (f"visit order {', '.join(order)}; {target} is reached in {level[target]} edge(s) by the path "
                      f"{f' {ARROW} '.join(path)}.")
        else:
            data["path"] = []
            result = f"visit order {', '.join(order)}; {target} cannot be reached from {source}."
        name = f"breadth-first search from {source} until {target} is dequeued"
    else:
        result = f"visit order {', '.join(order)}" + (
            f"; not reached: {', '.join(v for v in g.nodes if v not in parent)}." if len(parent) < len(g.nodes) else ".")
        name = f"breadth-first search from {source}"
    notes = ["Rules: a FIFO queue; mark a vertex when it is enqueued; neighbours are taken in alphabetical order."]
    setup = [f"Start: queue [{source}], {source} marked as seen."]
    return Trace("bfs", name, setup, steps, result, data, notes)


def dfs(g: Graph, source: str, target: str | None = None) -> Trace:
    """Recursive depth-first search shown with its explicit stack (the current path)."""
    source = _need(g, source, "source")
    if target is not None:
        target = _need(g, target, "target")
    visited = {source}
    order = [source]
    parent: dict[str, str | None] = {source: None}
    stack: list[tuple[str, list[str]]] = [(source, g.neighbours(source))]
    events: list[tuple[str, str, list[str]]] = [("visit", source, [source])]
    finished: list[str] = []
    stop = "all"
    if target == source:
        stop = "target"
    while stack and stop == "all":
        u, nbrs = stack[-1]
        nxt = next((v for v in nbrs if v not in visited), None)
        if nxt is None:
            stack.pop()
            finished.append(u)
            events.append(("back", u, [s for s, _ in stack]))
            continue
        visited.add(nxt)
        parent[nxt] = u
        order.append(nxt)
        stack.append((nxt, g.neighbours(nxt)))
        events.append(("visit", nxt, [s for s, _ in stack]))
        if target is not None and nxt == target:
            stop = "target"
    steps: list[str] = []
    i = 0
    while i < len(events):
        kind, node, st = events[i]
        n = len(steps) + 1
        if kind == "visit":
            if parent.get(node) is None:
                steps.append(f"Step {n}: start at {node}: visit it and push it. Stack: {_list(st)}.")
            else:
                steps.append(f"Step {n}: from {parent[node]} go to {node}, its first unvisited neighbour (alphabetical): "
                             f"visit it and push it. Stack: {_list(st)}.")
            i += 1
            continue
        backs = [node]
        while i + 1 < len(events) and events[i + 1][0] == "back":
            i += 1
            backs.append(events[i][1])
        st = events[i][2]
        who = ", ".join(backs)
        where = f"back to {st[-1]}" if st else "the stack is empty"
        steps.append(f"Step {n}: {who} {'has' if len(backs) == 1 else 'have'} no unvisited neighbours left: "
                     f"pop {'it' if len(backs) == 1 else 'them'} ({where}). Stack: {_list(st)}.")
        i += 1
    if stop == "target" and target is not None:
        steps.append(f"{target} is the target, so the search stops.")
    data: dict[str, Any] = {"order": order, "parent": parent, "finished": finished, "stop": stop}
    if target is not None:
        path = _path(parent, target) if target in parent else []
        data["path"] = path
        result = (f"visit order {', '.join(order)}; " + (f"found {target} along {f' {ARROW} '.join(path)}."
                                                          if path else f"{target} cannot be reached from {source}."))
        name = f"depth-first search from {source} until {target} is found"
    else:
        result = f"visit order {', '.join(order)}."
        name = f"depth-first search from {source}"
    notes = ["Rules: go to the first unvisited neighbour (alphabetical order) as deep as possible; when a vertex has "
             "none left, pop it and back up. The stack holds the current path."]
    setup = [f"Start: stack [{source}]."]
    return Trace("dfs", name, setup, steps, result, data, notes)


def prim(g: Graph, start: str | None = None) -> Trace:
    if not g.nodes:
        raise SolverError("empty graph")
    start = _need(g, start or g.nodes[0], "start")
    if any(e.w is None for e in g.edges):
        raise SolverError("a minimum spanning tree needs a weight on every edge")
    und = Graph(g.nodes, [Edge(e.a, e.b, e.w, False) for e in g.edges])
    key: dict[str, float] = {v: INF for v in und.nodes}
    parent: dict[str, str | None] = {v: None for v in und.nodes}
    key[start] = 0.0
    tree: list[str] = []
    chosen: list[tuple[str, str, float]] = []
    steps: list[str] = []
    while True:
        cands = [v for v in und.nodes if v not in tree and key[v] < INF]
        if not cands:
            break
        u = min(cands, key=lambda v: (key[v], node_key(v)))
        tree.append(u)
        if parent[u] is None:
            head = f"Step {len(tree)}: start the tree at {u}."
        else:
            chosen.append((parent[u], u, key[u]))
            head = (f"Step {len(tree)}: the cheapest edge from the tree to a new vertex is {parent[u]}-{u} ({fmt(key[u])})"
                    f"{_ties(cands, key, u)}: add {u} to the tree.")
        ups = []
        for v, w, _ in und.out(u):
            if v in tree:
                continue
            if float(w) < key[v]:  # type: ignore[arg-type]
                ups.append(f"{v} {fmt(key[v])}{ARROW}{fmt(w)} (via {u})")
                key[v], parent[v] = float(w), u  # type: ignore[arg-type]
        steps.append(head + (f" Update the cheapest known connection of each outside vertex: {'; '.join(ups)}."
                             if ups else " No outside vertex gets a cheaper connection."))
    total = sum(w for _, _, w in chosen)
    data = {"edges": chosen, "total": total, "order": tree,
            "spanning": len(tree) == len(und.nodes)}
    edges_txt = ", ".join(f"{a}-{b} ({fmt(w)})" for a, b, w in chosen)
    result = f"minimum spanning tree edges {edges_txt}; total weight {fmt(total)}."
    if len(tree) < len(und.nodes):
        result += f" Not connected to: {', '.join(v for v in und.nodes if v not in tree)}."
    notes = ["Rules (Prim): grow one tree; each step adds the cheapest edge joining the tree to a vertex outside it "
             "(ties alphabetical); keep for every outside vertex its cheapest known connection."]
    setup = [f"Start: connection cost {start}=0, every other vertex ∞."]
    return Trace("mst", f"Prim's minimum spanning tree from {start}", setup, steps, result, data, notes)


def kruskal(g: Graph) -> Trace:
    if any(e.w is None for e in g.edges):
        raise SolverError("a minimum spanning tree needs a weight on every edge")
    parent = {v: v for v in g.nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def norm(e: Edge) -> tuple[str, str]:
        return (e.a, e.b) if node_key(e.a) <= node_key(e.b) else (e.b, e.a)

    order = sorted(g.edges, key=lambda e: (float(e.w), node_key(norm(e)[0]), node_key(norm(e)[1])))  # type: ignore[arg-type]
    need = len(g.nodes) - 1
    chosen: list[tuple[str, str, float]] = []
    considered: list[dict[str, Any]] = []
    steps: list[str] = []
    for e in order:
        if len(chosen) >= need:
            break
        a, b = norm(e)
        ra, rb = find(a), find(b)
        n = len(steps) + 1
        if ra != rb:
            parent[rb] = ra
            chosen.append((a, b, float(e.w)))  # type: ignore[arg-type]
            considered.append({"edge": (a, b), "w": e.w, "added": True})
            steps.append(f"Step {n}: next cheapest edge {a}-{b} ({fmt(e.w)}) joins two different trees: add it "
                         f"({len(chosen)} of {need} edges).")
        else:
            considered.append({"edge": (a, b), "w": e.w, "added": False})
            steps.append(f"Step {n}: next cheapest edge {a}-{b} ({fmt(e.w)}): {a} and {b} are already connected, "
                         f"so it would close a cycle: skip it.")
    total = sum(w for _, _, w in chosen)
    edges_txt = ", ".join(f"{a}-{b} ({fmt(w)})" for a, b, w in chosen)
    result = f"minimum spanning tree edges {edges_txt}; total weight {fmt(total)}."
    if len(chosen) < need:
        result += " The graph is not connected, so this is a spanning forest."
    sorted_txt = ", ".join(f"{norm(e)[0]}-{norm(e)[1]} {fmt(e.w)}" for e in order)
    notes = ["Rules (Kruskal): take the edges from cheapest to most expensive (ties alphabetical); add an edge unless "
             "its ends are already connected (that would close a cycle); stop at n-1 edges."]
    setup = [f"Edges sorted by weight: {sorted_txt}."]
    data = {"edges": chosen, "total": total, "considered": considered}
    return Trace("mst", "Kruskal's minimum spanning tree", setup, steps, result, data, notes)


# ---------------------------------------------------------------- arrays


def _check_comparable(values: list[Any]) -> list[Any]:
    if not values:
        raise SolverError("empty array")
    if len(values) > 40:
        raise SolverError("array too long to trace on a whiteboard")
    return values


def bubble_sort(values: Sequence[Any]) -> Trace:
    a = _check_comparable(list(values))
    n = len(a)
    steps: list[str] = []
    passes: list[list[Any]] = []
    for i in range(n - 1):
        swaps = []
        for j in range(n - 1 - i):
            if a[j] > a[j + 1]:
                swaps.append(f"{fmt(a[j])}<->{fmt(a[j + 1])}")
                a[j], a[j + 1] = a[j + 1], a[j]
        passes.append(list(a))
        if swaps:
            steps.append(f"Pass {i + 1}: compare neighbours left to right, swapping when the left one is larger "
                         f"(swaps: {', '.join(swaps)}). Array: {_list(a)}; {fmt(a[n - 1 - i])} is now in its final place.")
        else:
            steps.append(f"Pass {i + 1}: no swaps, so the array is sorted and bubble sort stops early. Array: {_list(a)}.")
            break
    notes = ["Rules (bubble sort): each pass compares neighbours left to right and swaps them when the left one is "
             "larger, so the largest remaining value moves to the end; stop after a pass without swaps."]
    return Trace("sort", "bubble sort", [f"Start: {_list(values)}."], steps, f"sorted array {_list(a)}.",
                 {"passes": passes, "sorted": list(a)}, notes)


def insertion_sort(values: Sequence[Any]) -> Trace:
    a = _check_comparable(list(values))
    steps: list[str] = []
    passes: list[list[Any]] = []
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
        shifted = i - (j + 1)
        passes.append(list(a))
        how = (f"shift {shifted} larger value{'s' if shifted != 1 else ''} right and insert it at position {j + 1}"
               if shifted else "it is already in place")
        steps.append(f"Step {i}: take {fmt(key)} (index {i}); {how}. Array: {_list(a)} (first {i + 1} sorted).")
    notes = ["Rules (insertion sort): take the next value and slide it left past every larger value in the sorted prefix."]
    return Trace("sort", "insertion sort", [f"Start: {_list(values)}."], steps, f"sorted array {_list(a)}.",
                 {"passes": passes, "sorted": list(a)}, notes)


def selection_sort(values: Sequence[Any]) -> Trace:
    a = _check_comparable(list(values))
    n = len(a)
    steps: list[str] = []
    passes: list[list[Any]] = []
    for i in range(n - 1):
        m = min(range(i, n), key=lambda k: (a[k], k))
        if m != i:
            what = f"swap it with {fmt(a[i])} at index {i}"
            a[i], a[m] = a[m], a[i]
        else:
            what = "it is already at the front, no swap"
        passes.append(list(a))
        steps.append(f"Pass {i + 1}: the smallest value in indices {i}..{n - 1} is {fmt(a[i])} (index {m}); {what}. "
                     f"Array: {_list(a)}.")
    notes = ["Rules (selection sort): each pass finds the smallest value of the unsorted part and swaps it to the front "
             "of that part."]
    return Trace("sort", "selection sort", [f"Start: {_list(values)}."], steps, f"sorted array {_list(a)}.",
                 {"passes": passes, "sorted": list(a)}, notes)


def merge_sort(values: Sequence[Any]) -> Trace:
    a = _check_comparable(list(values))
    steps: list[str] = []
    passes: list[list[Any]] = []

    def sort(lo: int, hi: int) -> None:  # a[lo:hi]
        if hi - lo <= 1:
            return
        mid = (lo + hi - 1) // 2 + 1  # left half gets the extra element (CLRS split)
        sort(lo, mid)
        sort(mid, hi)
        left, right = a[lo:mid], a[mid:hi]
        merged: list[Any] = []
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        merged += left[i:] + right[j:]
        a[lo:hi] = merged
        passes.append(list(a))
        steps.append(f"Merge {len(steps) + 1}: {_list(left)} + {_list(right)} {ARROW} {_list(merged)}. Array: {_list(a)}.")

    sort(0, len(a))
    notes = ["Rules (merge sort): split in halves (left half gets the extra element), sort each half, then merge by "
             "repeatedly taking the smaller front value. Merges are listed in the order they happen."]
    return Trace("sort", "merge sort", [f"Start: {_list(values)}."], steps, f"sorted array {_list(a)}.",
                 {"passes": passes, "sorted": list(a)}, notes)


SORTS = {"bubble": bubble_sort, "insertion": insertion_sort, "selection": selection_sort, "merge": merge_sort}


def binary_search(values: Sequence[Any], key: Any) -> Trace:
    a = _check_comparable(list(values))
    notes = ["Rules (binary search): lo = 0, hi = n-1; while lo <= hi: mid = (lo + hi) // 2; equal -> found; "
             "a[mid] < key -> lo = mid + 1; a[mid] > key -> hi = mid - 1."]
    if any(x > y for x, y in zip(a, a[1:])):
        a = sorted(a)
        notes.append(f"The array is not sorted on the page, so it is sorted first: {_list(a)}.")
    lo, hi = 0, len(a) - 1
    steps: list[str] = []
    probes: list[dict[str, Any]] = []
    found = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        v = a[mid]
        rec = {"lo": lo, "hi": hi, "mid": mid, "value": v}
        if v == key:
            rec["cmp"] = "=="
            found = mid
            steps.append(f"Step {len(steps) + 1}: lo={lo} hi={hi} mid={mid}; a[{mid}] = {fmt(v)} equals {fmt(key)}: found.")
            probes.append(rec)
            break
        if v < key:
            rec["cmp"] = "<"
            steps.append(f"Step {len(steps) + 1}: lo={lo} hi={hi} mid={mid}; a[{mid}] = {fmt(v)} < {fmt(key)}, "
                         f"so search the right half: lo = {mid + 1}.")
            lo = mid + 1
        else:
            rec["cmp"] = ">"
            steps.append(f"Step {len(steps) + 1}: lo={lo} hi={hi} mid={mid}; a[{mid}] = {fmt(v)} > {fmt(key)}, "
                         f"so search the left half: hi = {mid - 1}.")
            hi = mid - 1
        probes.append(rec)
    if found < 0:
        steps.append(f"Step {len(steps) + 1}: lo={lo} > hi={hi}: the range is empty, so {fmt(key)} is not in the array.")
        result = f"{fmt(key)} is not in the array ({len(probes)} comparisons)."
    else:
        result = f"{fmt(key)} found at index {found} after {len(probes)} comparison{'s' if len(probes) != 1 else ''}."
    setup = [f"Array (indices 0..{len(a) - 1}): {_list(a)}; key {fmt(key)}."]
    return Trace("binary_search", f"binary search for {fmt(key)}", setup, steps, result,
                 {"probes": probes, "index": found, "array": a}, notes)


# ---------------------------------------------------------------- TCP congestion window


def _half(x: float) -> float:
    h = x / 2
    return float(math.floor(h)) if x == int(x) else h


def tcp_cwnd(initial: float = 1, ssthresh: float = 8, events: Iterable[tuple[int, str]] = (),
             rounds: int | None = None, variant: str = "reno") -> Trace:
    """cwnd (in MSS) per transmission round: slow start doubles it each RTT up to ssthresh, congestion
    avoidance adds 1 per RTT; a timeout sets ssthresh = cwnd/2 and cwnd = 1; three duplicate ACKs set
    ssthresh = cwnd/2 and cwnd = ssthresh (Reno; Tahoe goes back to 1)."""
    initial, ssthresh = float(initial), float(ssthresh)
    if initial <= 0 or ssthresh <= 0:
        raise SolverError("cwnd and ssthresh must be positive")
    evs: dict[int, str] = {}
    for r, kind in events:
        r = int(r)
        if r >= 1 and kind in ("timeout", "triple_dup_ack"):
            evs.setdefault(r, kind)
    variant = (variant or "reno").lower()
    if rounds is None or rounds < 1:
        if evs:
            rounds = max(evs) + 4
        else:
            rounds, c = 1, initial
            while c < ssthresh and rounds < 30:
                c, rounds = min(2 * c, ssthresh), rounds + 1
            rounds += 3
    rounds = int(min(max(rounds, 1), 30))
    cwnd, th = initial, ssthresh
    rows: list[dict[str, Any]] = []
    steps: list[str] = []
    for r in range(1, rounds + 1):
        phase = "slow start" if cwnd < th else "congestion avoidance"
        ev = evs.get(r)
        row: dict[str, Any] = {"round": r, "cwnd": cwnd, "ssthresh": th, "phase": phase, "event": ev}
        rows.append(row)
        line = f"Round {r}: cwnd = {fmt(cwnd)} MSS, ssthresh = {fmt(th)} ({phase})"
        if ev == "timeout":
            new_th = max(_half(cwnd), 1.0)
            line += (f" -> TIMEOUT: ssthresh = {fmt(cwnd)}/2 = {fmt(new_th)}, cwnd = 1 MSS; slow start begins again.")
            th, cwnd = new_th, 1.0
        elif ev == "triple_dup_ack":
            new_th = max(_half(cwnd), 1.0)
            if variant == "tahoe":
                line += f" -> 3 DUPLICATE ACKs (Tahoe): ssthresh = {fmt(cwnd)}/2 = {fmt(new_th)}, cwnd = 1 MSS."
                th, cwnd = new_th, 1.0
            else:
                line += (f" -> 3 DUPLICATE ACKs (Reno): ssthresh = {fmt(cwnd)}/2 = {fmt(new_th)}, cwnd = ssthresh = "
                         f"{fmt(new_th)} MSS; congestion avoidance continues from there.")
                th, cwnd = new_th, new_th
        elif cwnd < th:
            nxt = min(2 * cwnd, th)
            capped = " (capped at ssthresh)" if 2 * cwnd > th else ""
            switch = "; it reaches ssthresh, so congestion avoidance starts next" if nxt >= th else ""
            line += f": every ACK adds 1 MSS, so next round cwnd = {fmt(nxt)}{capped}{switch}."
            cwnd = nxt
        else:
            line += f": additive increase, +1 MSS per RTT, so next round cwnd = {fmt(cwnd + 1)}."
            cwnd += 1
        steps.append(line)
    seq = ", ".join(fmt(r["cwnd"]) for r in rows)
    result = f"cwnd per round (MSS): {seq}."
    if evs:
        result += " " + "; ".join(f"{'timeout' if k == 'timeout' else '3 duplicate ACKs'} in round {r}"
                                  for r, k in sorted(evs.items()) if r <= rounds) + "."
    notes = ["Rules: slow start doubles cwnd every round trip (+1 MSS per ACK) until it reaches ssthresh; then "
             "congestion avoidance adds 1 MSS per round trip; timeout: ssthresh = cwnd/2, cwnd = 1 MSS; "
             "3 duplicate ACKs: ssthresh = cwnd/2, cwnd = ssthresh" + (" (Tahoe: cwnd = 1)." if variant == "tahoe" else
                                                                         " (Reno).")]
    setup = [f"Start: cwnd = {fmt(initial)} MSS, ssthresh = {fmt(ssthresh)} MSS."]
    return Trace("tcp_cwnd", "TCP congestion window (slow start, congestion avoidance, multiplicative decrease)",
                 setup, steps, result, {"rows": rows, "cwnd": [r["cwnd"] for r in rows]}, notes)
