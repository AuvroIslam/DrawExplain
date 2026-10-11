"""Cross-check a graph read by the model against the pixels (perception regions + ink mask).

- Vertices must map to regions: the shape whose OCR text is the vertex label (or the region the model
  named, when that shape has no readable text).
- Edge weights must exist as numeric OCR text regions lying next to the segment between the two vertex
  shapes. A matching label confirms the weight ("verified"); a different, unambiguous label next to that
  segment wins over the model's reading ("corrected": trust the pixels).
- A straight ink line between two vertices that the model did not list, with a free weight label next to
  it, is added ("added"); without a label it is only reported.
Everything here is deterministic and cheap (no model call).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.tutor.solvers.algorithms import fmt

NUM = re.compile(r"^-?\d+(?:[.,]\d+)?$")
MAX_NODE_AREA = 0.06  # a vertex shape covers at most this fraction of the page
LINE_INK = 0.9  # share of samples along a segment that must have ink for "a line is drawn there"
ADD_LINE_INK = 0.95  # stricter, to add an edge the model did not list
CORRECT_MIN_SCORE = 0.85  # OCR confidence needed to overrule the model's weight
CLEAR_NEAREST = 1.3  # a label overrules only if its nearest edge is this much nearer than the next one
_CONFUSE = str.maketrans({"0": "o", "1": "i", "l": "i", "|": "i", "8": "b", "5": "s", "6": "g", "2": "z"})

Pt = tuple[float, float]


@dataclass
class NodeMatch:
    id: str
    label: str
    region_id: str | None = None
    how: str = "missing"  # label | label~ | unlabeled | relabeled | text | model | missing
    center: Pt | None = None  # pixels
    radius: float = 0.0  # pixels


@dataclass
class EdgeCheck:
    a: str
    b: str
    weight: float | None  # the weight used by the solver (pixels win when they disagree)
    model_weight: float | None
    directed: bool = False
    status: str = "unverified"  # verified | corrected | added | line | unverified
    label_region: str | None = None
    line: float | None = None  # share of the straight segment covered by ink
    note: str = ""

    def name(self) -> str:
        return f"{self.a}-{self.b}"


@dataclass
class GraphCheck:
    nodes: list[NodeMatch]
    edges: list[EdgeCheck]
    weighted: bool
    unmatched_labels: list[str] = field(default_factory=list)  # numeric labels near the graph explained by no edge
    possible_missing: list[str] = field(default_factory=list)  # ink lines between vertices with no edge listed
    notes: list[str] = field(default_factory=list)

    @property
    def nodes_mapped(self) -> int:
        return sum(1 for n in self.nodes if n.region_id is not None and n.how != "missing")

    def count(self, *statuses: str) -> int:
        return sum(1 for e in self.edges if e.status in statuses)

    @property
    def confirmed(self) -> int:
        """Edges whose existence and weight the pixels back up."""
        if self.weighted:
            return self.count("verified", "corrected", "added")
        return self.count("verified", "line", "added")

    @property
    def ok(self) -> bool:
        """Every vertex found and at most one edge (and at most 10%) left unconfirmed."""
        unconfirmed = len(self.edges) - self.confirmed
        return (self.nodes_mapped == len(self.nodes) and len(self.edges) > 0
                and unconfirmed <= max(0, min(1, int(0.1 * len(self.edges)))))

    def summary(self) -> str:
        parts = [f"{self.nodes_mapped}/{len(self.nodes)} vertices matched to regions"]
        if self.weighted:
            parts.append(f"{self.count('verified')}/{len(self.edges)} edge weights verified against the printed labels")
            if self.count("corrected"):
                parts.append(f"{self.count('corrected')} corrected from the image")
            if self.count("added"):
                parts.append(f"{self.count('added')} missing edge(s) added from the image")
        else:
            parts.append(f"{self.confirmed}/{len(self.edges)} edges confirmed as drawn lines")
        return ", ".join(parts)

    def node_map(self) -> dict[str, str]:
        return {n.id: n.region_id for n in self.nodes if n.region_id}


# ---------------------------------------------------------------- helpers


def _norm(s: str | None) -> str:
    return re.sub(r"[^0-9a-z]", "", (s or "").lower())


def same_label(text: str | None, label: str | None) -> str | None:
    """"exact" when the OCR text is the label, "approx" for a short label read with a look-alike
    character (0/O, 1/I, 8/B, ...), else None."""
    a, b = _norm(text), _norm(label)
    if not a or not b:
        return None
    if a == b:
        return "exact"
    if len(b) <= 3 and len(a) == len(b) and a.translate(_CONFUSE) == b.translate(_CONFUSE):
        return "approx"
    return None


def number(text: str | None) -> float | None:
    t = (text or "").strip().replace(" ", "")
    if not NUM.match(t):
        return None
    try:
        return float(t.replace(",", "."))
    except ValueError:
        return None


def _px(box: Any, W: int, H: int) -> tuple[float, float, float, float]:
    return box.x * W, box.y * H, (box.x + box.w) * W, (box.y + box.h) * H


def _center(b: tuple[float, float, float, float]) -> Pt:
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def _seg_dist(p: Pt, a: Pt, b: Pt) -> tuple[float, float]:
    """(distance from p to segment ab, projection parameter t in [0, 1])."""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    if L2 <= 1e-9:
        return math.hypot(p[0] - ax, p[1] - ay), 0.0
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy)), t


def _shrink(a: Pt, b: Pt, ra: float, rb: float) -> tuple[Pt, Pt]:
    """The visible part of an edge: from the boundary of one vertex to the boundary of the other."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L <= ra + rb + 4:
        return a, b
    ux, uy = dx / L, dy / L
    return (a[0] + ux * ra, a[1] + uy * ra), (b[0] - ux * rb, b[1] - uy * rb)


_ANGLES = np.radians(np.arange(-60, 61, 10))


class _InkProbe:
    """Share of points along a segment that have ink within a few pixels."""

    def __init__(self, ink: np.ndarray | None, tol: int):
        self.mask = None
        if ink is None or getattr(ink, "ndim", 0) != 2 or not ink.any():
            return
        try:
            import cv2

            k = 2 * tol + 1
            self.mask = cv2.dilate(ink.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
        except Exception:  # the probe is optional
            self.mask = None

    def _cover(self, ax: np.ndarray, ay: np.ndarray, bx: np.ndarray, by: np.ndarray) -> np.ndarray:
        H, W = self.mask.shape  # type: ignore[union-attr]
        L = float(np.max(np.hypot(bx - ax, by - ay)))
        ts = np.linspace(0.1, 0.9, max(8, int(L / 3)))
        xs = np.clip(np.round(ax[:, None] + ts[None, :] * (bx - ax)[:, None]).astype(int), 0, W - 1)
        ys = np.clip(np.round(ay[:, None] + ts[None, :] * (by - ay)[:, None]).astype(int), 0, H - 1)
        return self.mask[ys, xs].mean(axis=1)  # type: ignore[index]

    def edge(self, ca: Pt, ra: float, cb: Pt, rb: float) -> tuple[float | None, tuple[Pt, Pt]]:
        """Best straight line from the boundary of vertex a to the boundary of vertex b (edges are often
        drawn between boundary points rather than through the centres): (ink coverage, segment)."""
        direct = _shrink(ca, cb, ra, rb)
        if self.mask is None:
            return None, direct
        phi = math.atan2(cb[1] - ca[1], cb[0] - ca[0])
        da, db = np.meshgrid(_ANGLES, _ANGLES, indexing="ij")
        da, db = da.ravel(), db.ravel()
        ax, ay = ca[0] + ra * np.cos(phi + da), ca[1] + ra * np.sin(phi + da)
        bx, by = cb[0] + rb * np.cos(phi + math.pi + db), cb[1] + rb * np.sin(phi + math.pi + db)
        cov = self._cover(ax, ay, bx, by)
        i = int(np.argmax(cov))
        centre = (da == 0) & (db == 0)
        j = int(np.argmax(centre))
        if cov[i] <= cov[j] + 0.05:  # prefer the centre line unless another line is clearly better
            i = j
        return float(cov[i]), ((float(ax[i]), float(ay[i])), (float(bx[i]), float(by[i])))


# ---------------------------------------------------------------- vertices


def _match_nodes(pr: Any, nodes: list[dict]) -> list[NodeMatch]:
    W, H = pr.width, pr.height
    regions = pr.perception.regions
    byid = {r.id: r for r in regions}

    def vertex_shape(r: Any) -> bool:
        return r.kind == "shape" and r.box.w * r.box.h <= MAX_NODE_AREA

    def as_vertex(r: Any) -> Any:
        """A text inside a small shape stands for that shape (the label inside a circle)."""
        if r.kind == "text" and r.parent_id and r.parent_id in byid and vertex_shape(byid[r.parent_id]):
            return byid[r.parent_id]
        return r

    def label_of(r: Any) -> str | None:
        if r.text:
            return r.text
        kids = [k.text for k in regions if k.parent_id == r.id and k.kind == "text" and k.text]
        return " ".join(kids) if kids else None

    def search(label: str) -> list[tuple[Any, str]]:
        found: list[tuple[Any, str]] = []
        for r in regions:
            if vertex_shape(r):
                m = same_label(label_of(r), label)
                if m:
                    found.append((r, m))
        if not found:
            for r in regions:
                if r.kind == "text" and same_label(r.text, label) == "exact":
                    found.append((as_vertex(r), "exact"))
        exact = [f for f in found if f[1] == "exact"]
        return exact or found

    out: list[NodeMatch] = []
    used: dict[str, NodeMatch] = {}
    for n in nodes:
        nid = str(n.get("id") or "").strip()
        label = str(n.get("label") or nid).strip() or nid
        m = NodeMatch(id=nid, label=label)
        rid = str(n.get("region_id") or "").strip().upper() or None
        cand = as_vertex(byid[rid]) if rid and rid in byid else None
        chosen, how = None, "missing"
        if cand is not None:
            hit = same_label(label_of(cand), label) or same_label(label_of(cand), nid)
            if hit:
                chosen, how = cand, ("label" if hit == "exact" else "label~")
            elif cand.kind == "shape" and not label_of(cand):
                chosen, how = cand, "unlabeled"
        if chosen is None:
            found = search(label) or (search(nid) if nid != label else [])
            free = [f for f in found if f[0].id not in used]
            if len(free) == 1:
                chosen = free[0][0]
                how = ("relabeled" if cand is not None else "label") if free[0][1] == "exact" else "label~"
                if chosen.kind == "text":
                    how = "text"
            elif cand is not None and vertex_shape(cand):
                chosen, how = cand, "model"  # the model's region, unconfirmed by text
        if chosen is not None and chosen.id in used:
            other = used[chosen.id]
            rank = {"label": 0, "relabeled": 1, "text": 1, "label~": 2, "unlabeled": 3, "model": 4}
            if rank.get(how, 9) < rank.get(other.how, 9):
                other.region_id, other.how, other.center = None, "missing", None
            else:
                chosen, how = None, "missing"
        if chosen is not None:
            b = _px(chosen.box, W, H)
            m.region_id, m.how = chosen.id, how
            m.center = _center(b)
            m.radius = min(b[2] - b[0], b[3] - b[1]) / 2 if chosen.kind == "shape" else max(b[2] - b[0], b[3] - b[1]) / 2
            used[chosen.id] = m
        out.append(m)

    # one vertex left whose label OCR could not read (a thin "I"): the one unlabeled vertex-sized shape left
    missing = [m for m in out if m.region_id is None]
    sizes = sorted(byid[m.region_id].box.w * byid[m.region_id].box.h for m in out
                   if m.region_id and byid[m.region_id].kind == "shape")
    if len(missing) == 1 and len(sizes) >= 2:
        med = sizes[len(sizes) // 2]
        spare = [r for r in regions if vertex_shape(r) and r.id not in used and not label_of(r)
                 and 0.5 * med <= r.box.w * r.box.h <= 2.0 * med and r.parent_id is None]
        if len(spare) == 1:
            m, r = missing[0], spare[0]
            b = _px(r.box, W, H)
            m.region_id, m.how, m.center, m.radius = r.id, "eliminated", _center(b), min(b[2] - b[0], b[3] - b[1]) / 2
    return out


# ---------------------------------------------------------------- edges


def check_graph(pr: Any, nodes: list[dict], edges: list[dict]) -> GraphCheck:
    """nodes: [{id, label, region_id}], edges: [{a, b, weight, directed}] as read by the model."""
    W, H = pr.width, pr.height
    regions = pr.perception.regions
    matches = _match_nodes(pr, nodes)
    by_node = {m.id: m for m in matches}
    weighted = any(e.get("weight") is not None for e in edges)

    node_rids = {m.region_id for m in matches if m.region_id}
    node_boxes = [_px(r.box, W, H) for r in regions if r.id in node_rids]

    def inside_node(p: Pt) -> bool:
        return any(b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3] for b in node_boxes)

    labels = []  # numeric text regions that are not vertex labels
    for r in regions:
        if r.kind != "text" or r.id in node_rids:
            continue
        v = number(r.text)
        if v is None:
            continue
        b = _px(r.box, W, H)
        c = _center(b)
        if inside_node(c):
            continue
        labels.append({"id": r.id, "value": v, "center": c, "h": b[3] - b[1], "score": float(r.score or 0.0)})

    radii = sorted(m.radius for m in matches if m.center is not None)
    r_med = radii[len(radii) // 2] if radii else 0.02 * max(W, H)
    hs = sorted(lb["h"] for lb in labels)
    text_h = hs[len(hs) // 2] if hs else 0.02 * H
    tol = max(1.8 * r_med, 3.0 * text_h)
    probe = _InkProbe(getattr(pr, "ink", None), max(2, int(round(min(W, H) / 400))))

    checks: list[EdgeCheck] = []
    segs: list[tuple[Pt, Pt] | None] = []
    seen_pairs: set[frozenset[str]] = set()
    for e in edges:
        a, b = str(e.get("a") or "").strip(), str(e.get("b") or "").strip()
        if not a or not b or a == b:
            continue
        w = e.get("weight")
        w = float(w) if isinstance(w, (int, float)) and math.isfinite(w) else None
        ec = EdgeCheck(a=a, b=b, weight=w, model_weight=w, directed=bool(e.get("directed")))
        ma, mb = by_node.get(a), by_node.get(b)
        seen_pairs.add(frozenset((a, b)))
        if ma is None or mb is None or ma.center is None or mb.center is None:
            ec.note = "a vertex of this edge was not found on the image"
            checks.append(ec)
            segs.append(None)
            continue
        ec.line, seg = probe.edge(ma.center, ma.radius, mb.center, mb.radius)
        if ec.line is not None and ec.line < LINE_INK:
            seg = _shrink(ma.center, mb.center, ma.radius, mb.radius)  # no clear line: measure to the centre line
        checks.append(ec)
        segs.append(seg)

    def dist(lb: dict, seg: tuple[Pt, Pt] | None) -> float:
        return _seg_dist(lb["center"], *seg)[0] if seg is not None else math.inf

    # 1) labels that confirm the model's weight, nearest pairs first
    used_labels: set[str] = set()
    if weighted:
        pairs = sorted(((dist(lb, s), i, lb["id"]) for i, s in enumerate(segs) for lb in labels
                        if checks[i].weight is not None and lb["value"] == checks[i].weight), key=lambda t: t[0])
        for d, i, lid in pairs:
            if d > tol or checks[i].status == "verified" or lid in used_labels:
                continue
            checks[i].status, checks[i].label_region = "verified", lid
            used_labels.add(lid)

        # 2) a different label right next to an unconfirmed edge: the pixels win
        free = [lb for lb in labels if lb["id"] not in used_labels]
        cands = []
        for lb in free:
            ds = sorted((dist(lb, s), i) for i, s in enumerate(segs) if s is not None)
            if not ds or ds[0][0] > tol:
                continue
            d0, i0 = ds[0]
            d1 = ds[1][0] if len(ds) > 1 else math.inf
            if checks[i0].status != "unverified" or d1 < CLEAR_NEAREST * d0 or lb["score"] < CORRECT_MIN_SCORE:
                continue
            cands.append((d0, i0, lb))
        for d0, i0, lb in sorted(cands, key=lambda t: t[0]):
            ec = checks[i0]
            if ec.status != "unverified" or lb["id"] in used_labels:
                continue
            used_labels.add(lb["id"])
            ec.status, ec.label_region = "corrected", lb["id"]
            ec.note = (f"the model read {fmt(ec.model_weight)}, the label next to this edge on the image says "
                       f"{fmt(lb['value'])} ({lb['id']})")
            ec.weight = lb["value"]
    for ec in checks:  # unweighted graphs: a drawn line is the evidence
        if ec.status == "unverified" and ec.line is not None and ec.line >= LINE_INK:
            ec.status = "line" if not weighted else ec.status
        if ec.status == "unverified" and not ec.note:
            if weighted:
                ec.note = "no matching weight label found next to this edge"
            elif ec.line is not None:
                ec.note = f"no straight line found between the vertices ({ec.line:.0%} ink)"

    # 3) straight lines between vertices the model did not connect
    result = GraphCheck(nodes=matches, edges=checks, weighted=weighted)
    placed = [m for m in matches if m.center is not None]
    for i, ma in enumerate(placed):
        for mb in placed[i + 1:]:
            if frozenset((ma.id, mb.id)) in seen_pairs:
                continue
            cov, seg = probe.edge(ma.center, ma.radius, mb.center, mb.radius)  # type: ignore[arg-type]
            if cov is None or cov < ADD_LINE_INK:
                continue
            if any(_seg_dist(o.center, *seg)[0] < 1.2 * o.radius for o in placed  # type: ignore[arg-type]
                   if o is not ma and o is not mb):
                continue  # passes through another vertex: that is two edges, not one
            name = f"{ma.id}-{mb.id}"
            if not weighted:
                result.possible_missing.append(name)
                continue
            near = []
            for lb in labels:
                if lb["id"] in used_labels:
                    continue
                d = _seg_dist(lb["center"], *seg)[0]
                others = [dist(lb, s) for s in segs if s is not None]
                if d <= tol and all(d * CLEAR_NEAREST <= o for o in others) and lb["score"] >= CORRECT_MIN_SCORE:
                    near.append((d, lb))
            if not near:
                result.possible_missing.append(name)
                continue
            d, lb = min(near, key=lambda t: t[0])
            used_labels.add(lb["id"])
            checks.append(EdgeCheck(a=ma.id, b=mb.id, weight=lb["value"], model_weight=None, status="added",
                                    label_region=lb["id"], line=cov,
                                    note=f"drawn on the image with weight {fmt(lb['value'])} ({lb['id']}) but not "
                                         f"listed by the model"))
            segs.append(seg)

    # 4) numeric labels next to the graph that no edge explains
    if weighted:
        for lb in labels:
            if lb["id"] in used_labels:
                continue
            if any(dist(lb, s) <= tol for s in segs if s is not None):
                result.unmatched_labels.append(f"{fmt(lb['value'])} ({lb['id']})")
    for ec in checks:
        if ec.status in ("corrected", "added"):
            result.notes.append(f"edge {ec.name()}: {ec.note}")
    return result
