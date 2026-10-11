"""Lesson-quality benchmark: does the tutor teach the procedure on the page correctly?

Three fixed study pages, each with a focus question. Every (case, run) is one real lesson from
POST /api/lessons, made by a fresh child process with its own temporary DATA_DIR, LLM_CACHE=0 and
STUDYLENS_WARMUP=0, so uploads, scans, cached model answers and already-taught lessons never leak from
one run into the next, and run-to-run variation is real. Each lesson JSON (plus latency) is saved,
then scored by small regex checks (one documented function per check) on what the student hears and
sees:

    step narrations + text written on the board (labels, arrow captions) + the margin sketch

lower-cased, with unicode arrows / "-->" / "=>" normalised to "->" and dashes to "-". A board text
attached to a region whose OCR text is a single letter (the graph nodes A..I) is read with that letter
in front ("b: ∞ -> 5", "a -> ?: +1"), because on the board the note belongs to that node.
Step titles, the summary and the quiz are not checked.

Runs against ANY backend version: a git worktree of an old commit or the working tree.
From the repo root, with the backend venv:

    backend/.venv/Scripts/python backend/scripts/eval_lessons.py --backend <dir>/backend --version L2 \
        [--runs 3] [--cases dijkstra_AtoE,tcp_cwnd] [--jobs 3] [--note "what changed"]
    ... --version L2 --rescore             re-run the checks on the saved lessons (no API calls, no cost)
    ... --summary L0 L2 [--summary-out samples/eval/lessons_summary.md]
    ... --score-lesson lesson.json --cases dijkstra_AtoE [--perception perception.json]

Writes samples/eval/lessons/<version>/: <case>_run<k>.json (lesson, latency, checks with the matched
evidence), results.json (scores only) and transcripts.md (every lesson, readable, with its marks).
Completed runs are skipped when the command is repeated (pass --force to redo them), so a failed run
can be retried without paying for the others again.

Bench cases. Besides the three core cases above (hand-written check functions), every file
samples/bench/cases/*.json is a case, read from disk at run time (new files are picked up on the next
command):

    {"id": "math_quadratic", "topic": "math", "image": "images/x.png" (or "pdf": "pdfs/y.pdf", "page": 3),
     "question": "...", "reference_answer": "...", "source_url": "...", "license": "...", "author": "...",
     "checks": [{"name": "...", "description": "...", "all": ["regex", ...], "any": ["regex", ...], "min_any": 1}]}

The file path is relative to samples/bench/. An image is uploaded with POST /api/images, a PDF with
POST /api/documents and one page perceived. Each check runs its regexes case-insensitively on the same
normalised text as the core checks (without the node-letter prefix); it passes when every "all" regex
matches and at least min_any (default 1 when "any" is given) of the "any" regexes match.

    ... --bench        only the bench cases          ... --all       core + bench cases
    ... --cases "math_*,cs_dfs"   names or shell-style patterns     ... --list    show every case
--summary also writes a per-topic table (core cases have the topic "core").
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "samples" / "eval" / "lessons"
DEFAULT_SUMMARY = ROOT / "samples" / "eval" / "lessons_summary.md"
BENCH_DIR = ROOT / "samples" / "bench"
BENCH_CASES_DIR = BENCH_DIR / "cases"
CHILD_TIMEOUT_S = 900


@dataclass(frozen=True)
class BenchCheck:
    """A declarative check of a bench case (see the module docstring)."""

    name: str
    description: str
    all: tuple[str, ...]
    any: tuple[str, ...]
    min_any: int


@dataclass(frozen=True)
class Case:
    name: str
    source: Path
    page: int | None  # PDF page, opened in reader mode (upload + perceive one page); None = image upload
    question: str
    topic: str = "core"
    checks: tuple[BenchCheck, ...] = field(default=(), compare=False)  # bench cases only
    case_file: Path | None = field(default=None, compare=False)  # bench cases only


CASES: dict[str, Case] = {c.name: c for c in [
    Case("dijkstra_AtoE", ROOT / "dijkstra-slides.pdf", 3, "how to get the shortest path from A to E"),
    Case("tcp_cwnd", ROOT / "L11 TCP Error Control & Congestion Control.pptx.pdf", 31,
         "How does the congestion window change from the start until a timeout?"),
    Case("flowchart_invalid_twice", ROOT / "samples" / "synthetic" / "clean" / "flowchart_loop.png", None,
         "What happens if the input is invalid twice?"),
]}


# ================================================================ bench cases: samples/bench/cases/*.json

RE_FLAGS = re.IGNORECASE
_BENCH: dict[str, Case] | None = None


def _bench_source(rel: str, case_file: Path) -> Path:
    """The case's image / PDF: relative to samples/bench/ (else to the case file, else to the repo root)."""
    p = Path(rel)
    if p.is_absolute():
        return p
    for base in (BENCH_DIR, case_file.parent, ROOT):
        if (base / p).is_file():
            return (base / p).resolve()
    return BENCH_DIR / p


def load_bench_case(path: Path) -> Case:
    """One bench case file -> Case; ValueError / re.error says what is wrong with it."""
    d = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError("not a JSON object")
    name = str(d.get("id") or path.stem).strip()
    if name in CASES:
        raise ValueError(f"id {name!r} is a core case")
    rel = d.get("pdf") or d.get("image") or d.get("document") or d.get("file")
    if not rel:
        raise ValueError("no 'image' or 'pdf' file")
    source = _bench_source(str(rel), path)
    if not source.is_file():
        raise ValueError(f"file not found: {source}")
    is_pdf = source.suffix.lower() == ".pdf" or str(d.get("kind") or d.get("type") or "").lower() == "pdf"
    question = str(d.get("question") or "").strip()
    if not question:
        raise ValueError("no question")
    checks: list[BenchCheck] = []
    for i, c in enumerate(d.get("checks") or [], 1):
        all_, any_ = tuple(map(str, c.get("all") or ())), tuple(map(str, c.get("any") or ()))
        if not all_ and not any_:
            raise ValueError(f"check {i} has no 'all' or 'any' regexes")
        for p in all_ + any_:
            try:
                re.compile(p, RE_FLAGS)
            except re.error as exc:
                raise ValueError(f"check {i}: bad regex {p!r}: {exc}") from None
        min_any = int(c["min_any"]) if c.get("min_any") is not None else (1 if any_ else 0)
        if min_any > len(any_):
            raise ValueError(f"check {i}: min_any {min_any} > {len(any_)} 'any' regexes")
        checks.append(BenchCheck(str(c.get("name") or f"check{i}"), " ".join(str(c.get("description") or "").split()),
                                 all_, any_, min_any))
    if not checks:
        raise ValueError("no checks")
    if len({c.name for c in checks}) != len(checks):
        raise ValueError("two checks have the same name")
    return Case(name, source, int(d.get("page") or 1) if is_pdf else None, question,
                topic=str(d.get("topic") or name.split("_")[0]).strip().lower(), checks=tuple(checks), case_file=path)


def bench_cases() -> dict[str, Case]:
    """Every valid bench case, read once per process (cases written later are picked up by the next command).
    A broken file is reported on stderr and skipped."""
    global _BENCH
    if _BENCH is None:
        _BENCH = {}
        for path in sorted(BENCH_CASES_DIR.glob("*.json")):
            try:
                case = load_bench_case(path)
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                print(f"skipping bench case {path.name}: {exc}", file=sys.stderr)
                continue
            if case.name in _BENCH:
                print(f"skipping bench case {path.name}: id {case.name!r} already used", file=sys.stderr)
                continue
            _BENCH[case.name] = case
        _BENCH = dict(sorted(_BENCH.items(), key=lambda kv: (kv[1].topic, kv[0])))
    return _BENCH


def all_cases() -> dict[str, Case]:
    """Core cases first, then the bench cases by topic and id."""
    return {**CASES, **bench_cases()}


def get_case(name: str) -> Case:
    case = all_cases().get(name)
    if case is None:
        raise SystemExit(f"unknown case {name!r}")
    return case


def has_checks(name: str | None) -> bool:
    return name in CHECKS or name in bench_cases()


def case_topic(name: str | None, rows: list[dict] | None = None) -> str:
    """A case's topic: as recorded with its runs, else from the case definition ("core" for the core cases)."""
    for r in rows or []:
        if r.get("topic"):
            return str(r["topic"])
    case = all_cases().get(name or "")
    return case.topic if case else str(name or "?").split("_")[0]


def case_order() -> dict[str, int]:
    return {name: i for i, name in enumerate(all_cases())}


# ================================================================ text the checks read

_ARROW_RE = re.compile(r"\s*(?:-{1,3}>|={1,2}>|[→⟶➝➔➜➞⇒⟹↦⇨⭢])\s*")
_DASH_RE = re.compile(r"[‐‑‒–—―−]")
_LETTER_RE = re.compile(r"[A-Za-z]")


def norm(text: str) -> str:
    """Lower-case; unicode arrows, "-->", "->" and "=>" become " -> "; dashes "-"; curly quotes straight."""
    t = unicodedata.normalize("NFKC", text or "").replace("⁄", "/")  # NFKC turns ½ into 1⁄2
    t = t.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = _ARROW_RE.sub(" -> ", _DASH_RE.sub("-", t))
    return re.sub(r"[ \t]+", " ", t).strip()


def _letters(ids: list[str] | None, regions: dict[str, str]) -> str:
    out: list[str] = []
    for rid in ids or []:
        t = (regions.get(rid) or "").strip().lower()
        if _LETTER_RE.fullmatch(t) and t not in out:
            out.append(t)
    return "+".join(out)


def board_text(ann: dict, regions: dict[str, str]) -> str:
    """The text a drawing writes on the board, prefixed by the node letter(s) it is attached to."""
    text = " ".join(str(ann.get("text") or "").split())
    if not text:
        return ""
    if ann.get("kind") == "arrow":
        src, dst = _letters(ann.get("from_ids"), regions), _letters(ann.get("to_ids"), regions)
        return f"{src or '?'} -> {dst or '?'}: {text}" if (src or dst) else text
    target = _letters(ann.get("target_ids"), regions)
    return f"{target}: {text}" if target else text


_SKETCH_TOKEN = re.compile(
    r"(?P<id>\b[A-Za-z_]\w*\b)\s*(?:"
    r"\[+\(?/?\\?\"?(?P<l1>[^\]\"]*?)\"?\\?/?\)?\]+"  # A[label], A[[label]], A[(label)], A[/label/]
    r"|\(+\[?\"?(?P<l2>[^)\"]*?)\"?\]?\)+"  # A(label), A((label)), A([label])
    r"|\{+\"?(?P<l3>[^}\"]*?)\"?\}+"  # A{label}, A{{label}}
    r"|>\"?(?P<l4>[^\]\"]*?)\"?\])"  # A>label]
    r"|\|\s*\"?(?P<edge>[^|\"]*?)\"?\s*\|"  # -->|edge label|
    r"|(?P<ref>\b[A-Za-z_]\w*\b)"  # a node referenced by id only
)


def sketch_lines(source: str) -> list[str]:
    """The Mermaid sketch as the student sees it: node labels instead of node ids, edge labels in brackets
    ("A[Read input] --> B{Valid?}" -> "Read input --> Valid?", "B -->|No| C" -> "Valid? --> (No) Show error")."""
    lines = [ln.strip() for ln in source.splitlines() if ln.strip()]
    labels: dict[str, str] = {}
    for ln in lines:
        for m in _SKETCH_TOKEN.finditer(ln):
            if m.group("id"):
                labels.setdefault(m.group("id"), next(g for g in m.group("l1", "l2", "l3", "l4") if g is not None))

    def render(m: re.Match) -> str:
        if m.group("id"):
            return next(g for g in m.group("l1", "l2", "l3", "l4") if g is not None)
        if m.group("edge") is not None:
            return f"({m.group('edge')}) "
        return labels.get(m.group("ref"), m.group("ref"))

    return [_SKETCH_TOKEN.sub(render, ln) for ln in lines
            if not re.match(r"(?i)^(?:flowchart|graph)\b|^(?:classDef|class|style|linkStyle|%%)", ln)]


def step_text(step: dict, regions: dict[str, str]) -> str:
    """Narration, then one line per board text, then the sketch; normalised line by line."""
    lines = [str(step.get("narration") or "")]
    lines += [b for b in (board_text(a, regions) for a in step.get("annotations") or []) if b]
    if step.get("sketch"):
        lines += sketch_lines(str(step["sketch"]))
    return "\n".join(n for n in (norm(line) for line in "\n".join(lines).split("\n")) if n)


@dataclass
class Doc:
    """One lesson as the checks see it: a normalised text per step."""

    steps: list[str]

    @property
    def full(self) -> str:
        return "\n\n".join(self.steps)

    @property
    def last(self) -> str:
        return self.steps[-1] if self.steps else ""


def lesson_doc(lesson: dict, regions: dict[str, str] | None = None) -> Doc:
    return Doc([step_text(s, regions or {}) for s in lesson.get("steps") or []])


# ================================================================ regex helpers

Hit = tuple[bool, str]  # (passed, evidence: the matched text, or what is missing)

S = r"[^.\n]"  # any character that stays inside one sentence / one board line
NUMBER = r"(?<![\w./])(\d+)(?![\d/]|[.,]\d)"  # a whole number (not part of 18, 1/2, 1.5)


def node(x: str) -> str:
    """A one-letter node name ("b", "a's"), not the pronoun in "i'll" / "i'm" and not "e.g."."""
    return rf"(?<![\w']){x}(?!\w|'(?:ll|m|ve|d|re)\b|\.\w)"


def num(n: int | str) -> str:
    """The number n on its own: "5" in "b = 5" or "∞ -> 5", not in "15", "1/2" or "1.5"."""
    return rf"(?<![\w./]){n}(?![\d/]|[.,]\d)"


def near(a: str, b: str, gap: int = 30) -> str:
    """a, then b at most `gap` characters later in the same sentence."""
    return rf"(?:{a}){S}{{0,{gap}}}?(?:{b})"


NODES = "abcdefghi"  # the vertices of the Dijkstra slide


def gap_without(x: str, gap: int) -> str:
    """Up to `gap` characters of one sentence that name no node other than x: in "a to b to c costs 12" the
    12 is not b's value, and "pick i -> set e" is about i."""
    others = NODES.replace(x, "")
    return rf"(?:(?!(?<![\w'])[{others}](?![\w']))[^.\n]){{0,{gap}}}?"


def pair(x: str, n: int) -> str:
    """Node x stated with value n, with no other node in between: "b gets 5", "b = 5", "b: ∞ -> 5", "5 for b"."""
    return rf"{node(x)}{gap_without(x, 30)}{num(n)}|{num(n)}{gap_without(x, 12)}{node(x)}"


def first(text: str, *patterns: str) -> str | None:
    """The first match of the first pattern that matches, else None."""
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def all_of(*parts: str | None) -> Hit:
    return all(p is not None for p in parts), " | ".join(p if p is not None else "MISSING" for p in parts)


def hit(evidence: str | None) -> Hit:
    return evidence is not None, evidence if evidence is not None else "MISSING"


def number_runs(text: str, max_gap: int = 20) -> Iterator[tuple[list[int], str]]:
    """Numbers written one after another in one sentence ("1 -> 2 -> 4", "8, 9, 10", "a[1] -> b[2]"):
    (values, the text they span); consecutive numbers at most `max_gap` characters apart."""
    for sentence in re.split(r"(?<!\d)\.(?!\d)|\n", text):
        run: list[re.Match] = []
        for m in re.finditer(NUMBER, sentence):
            if run and m.start() - run[-1].end() > max_gap:
                if len(run) >= 3:
                    yield [int(r.group(1)) for r in run], sentence[run[0].start():run[-1].end()]
                run = []
            run.append(m)
        if len(run) >= 3:
            yield [int(r.group(1)) for r in run], sentence[run[0].start():run[-1].end()]


def sequence(text: str, step: Callable[[int], int], min_start: int) -> str | None:
    """First run of 3+ numbers where each one is step(previous), starting at >= min_start."""
    for values, span in number_runs(text):
        for i in range(len(values) - 2):
            a, b, c = values[i:i + 3]
            if a >= min_start and b == step(a) and c == step(b):
                return span
    return None


# ================================================================ checks: dijkstra_AtoE
# Correct run: A=0, others ∞; relax A: B=5, I=1, G=9, H=18; pick I: C=7, G 9->4, E=3; pick E (3) = final;
# path A-I-E.

INFINITY = r"∞|infinit|\binf\b"
PICK = (r"\b(?:pick|choos|chose|select|settl|lock|visit|finali[sz]|extract|pop|remov)\w*"
        r"|\b(?:smallest|closest|cheapest|lowest|minimum)\b")
DONE = (r"✓|\bdone\b|\bsettled\b|\bfinal(?:i[sz]ed)?\b|\bfinished\b|\blocked\b|\bvisited\b|\bpermanent\b"
        r"|\bfixed\b|\bis (?:the )?next\b|\bcomes next\b|\bis (?:now )?(?:the )?smallest\b|\bhas the smallest\b"
        r"|\b(?:is|gets) (?:chosen|picked|selected|settled|extracted|popped)\b")
HOP = r"[ \t]*(?:->|-|,|\bto\b|\bthen(?: to)?\b|\band then\b|\bvia\b)[ \t]*(?:\(?\d+\)?[ \t]*(?:->|-)[ \t]*)?"
BACK = rf"{S}{{0,12}}?\b(?:via|from)\b{S}{{0,4}}?"


def settled(x: str) -> list[str]:
    """Node x picked / settled / marked done: "dijkstra picks ... i", "settle i", "i ✓", "i is final"."""
    return [rf"(?:{PICK}){gap_without(x, 50)}{node(x)}", rf"{node(x)}{gap_without(x, 30)}(?:{DONE})"]


def dijkstra_init(d: Doc) -> Hit:
    """The other vertices start at infinity ("∞", "infinity") AND the source A starts at 0."""
    return all_of(first(d.full, INFINITY), first(d.full, pair("a", 0), near(node("a"), r"\bzero\b")))


def dijkstra_relax_A(d: Doc) -> Hit:
    """Relaxing A's edges gives B 5, G 9, H 18 and I 1: at least 3 of these 4 (node, value) pairs are stated."""
    found = [first(d.full, pair(x, n)) for x, n in (("b", 5), ("g", 9), ("h", 18), ("i", 1))]
    return sum(f is not None for f in found) >= 3, " | ".join(f or "MISSING" for f in found)


G_9_TO_4 = [
    rf"{node('g')}{gap_without('g', 40)}{num(9)}{S}{{0,15}}?{num(4)}",  # "g: 9 -> 4", "g improves from 9 to 4"
    rf"{node('g')}{gap_without('g', 40)}{num(4)}{S}{{0,30}}?(?:instead of|better than|beat\w*|down from|from"
    rf"|replac\w*|was|than|improv\w*|cheaper|over){S}{{0,10}}?{num(9)}",  # "g becomes 4, better than 9"
]


def dijkstra_relax_I_all(d: Doc) -> Hit:
    """Relaxing I's edges is complete, not only the edge towards E: C 7 AND G improves 9 -> 4 AND E 3."""
    return all_of(first(d.full, pair("c", 7)), first(d.full, *G_9_TO_4), first(d.full, pair("e", 3)))


def dijkstra_order(d: Doc) -> Hit:
    """I is picked / settled / marked done before E is declared final (Dijkstra's own processing order)."""
    text = d.full
    i_done = [m for p in settled("i") for m in re.finditer(p, text)]
    e_final = [m for p in settled("e") + [rf"\bstop\w*{gap_without('e', 40)}{node('e')}"] for m in re.finditer(p, text)]
    if not i_done or not e_final:
        return False, f"I settled: {i_done[0].group(0) if i_done else 'MISSING'} | E final: " \
                      f"{e_final[0].group(0) if e_final else 'MISSING'}"
    i_first = min(i_done, key=lambda m: m.start())
    e_last = max(e_final, key=lambda m: m.start())
    return i_first.start() < e_last.start(), f"{i_first.group(0)} ... {e_last.group(0)}"


def dijkstra_answer(d: Doc) -> Hit:
    """The final step states the path A-I-E ("A -> I -> E", "A to I to E", both hops "A to I" and "I to E",
    or backwards "E via I, I from A") AND the total 3."""
    last = d.last
    path = first(last, rf"{node('a')}{HOP}{node('i')}{HOP}{node('e')}")
    if path is None:
        hops = (first(last, rf"{node('a')}{HOP}{node('i')}"), first(last, rf"{node('i')}{HOP}{node('e')}"))
        back = (first(last, rf"{node('e')}{BACK}{node('i')}"), first(last, rf"{node('i')}{BACK}{node('a')}"))
        for a, b in (hops, back):
            if a and b:
                path = f"{a} + {b}"
                break
    total = first(last, near(r"\b(?:total|cost|distance|length|sum|weight|answer|shortest|equals|makes|gives|of|is)\b|=",
                             num(3), 20),
                  near(num(3), r"\b(?:total|altogether|units?)\b", 10))
    return all_of(path, total)


# ================================================================ checks: tcp_cwnd

START = r"\b(?:start\w*|begin\w*|initial\w*|at first|first)\b"
ONE_MSS = (r"(?<![\w./])(?:1|one)[ \t]*(?:mss|segments?|packets?|max(?:imum)? segment)\b"
           r"|\b(?:cwnd|congwin|window)[ \t]*(?:=|:|is|of|at|to)[ \t]*(?:just |only |exactly )?(?:1|one)(?![\d/]|[.,]\d|\w)")
THRESHOLD_VALUE = [
    r"\b(?:ss)?thresh\w*[ \t]*(?:\(\w+\)[ \t]*)?(?:=|:|is|of|at|to|becomes|reaches|hits|drops to|set to|is set to|is now|now"
    r"|->|\(|, say|, e\.g\.)?[ \t]*(?:about |say |e\.g\. |only |just |exactly )?" + NUMBER
    + r"(?![ \t]*(?:dup|duplicate|acks?\b|rtt|per\b))",
    NUMBER + r"[ \t]*(?:mss|segments?|packets?)?[ \t]*(?:is|as|=|becomes)[ \t]*(?:the |our |a )?(?:new )?(?:ss)?thresh",
]
PER_RTT = (r"\b(?:per|each|every|a|an|one|over (?:a|one|each|the)|for each)[ \t]+(?:rtt|round[ -]?trips?|rounds?)\b"
           r"|\b(?:one|a|each|every|per)[ \t]+(?:full[ \t]+|whole[ \t]+)?window(?:'s worth)?[ \t]+of[ \t]+acks\b")
PLUS_ONE = (r"(?:\+[ \t]*|\bplus[ \t]+|\bby[ \t]+|\badds?[ \t]+|\badding[ \t]+)(?:only[ \t]+|just[ \t]+|about[ \t]+)?(?:1|one)(?![\d/]|[.,]\d)"
            r"(?:[ \t]*(?:mss|segments?|packets?))?")
STRICT_PLUS_ONE = r"\+[ \t]*1(?![\d/]|[.,]\d)|\bplus (?:1|one)\b(?!/)|\bby (?:1|one)(?![\d/]|[.,]\d|\w)"
GROWS_ONE = (r"\b(?:grow\w*|add\w*|increas\w*|gains?|rises?)\b[^\d\n]{0,12}?(?<![\w./])(?:1|one)(?![\d/]|[.,]\d|\w)"
             r"(?![ \t]*(?:to|->|,)[ \t]*\d)")
TIMEOUT = r"time-?[ \t]?outs?\b|timed out|timer (?:expires|runs out|fires)|\brto\b"
HALVES = [near(r"\b(?:ss)?thresh\w*", r"\bhalf\b|\bhalve[sd]?\b|halving|1/2|/[ \t]*2\b|÷[ \t]*2|divided by (?:2|two)", 50),
          near(r"\bhalf\b|\bhalve[sd]?\b|halving|1/2", r"\b(?:ss)?thresh\w*", 40)]
RESET_VERB = r"\b(?:back|reset\w*|drops?|dropped|falls?|fell|collaps\w*|returns?|crash\w*|cut\w*|goes|down)\b"
RESET_TO_1 = [
    near(r"\b(?:cwnd|congwin|window)\b", rf"(?:{RESET_VERB}|=|:){S}{{0,25}}?(?<![\w./])(?:1|one)(?![\d/]|[.,]\d|\w)", 50),
    rf"{RESET_VERB}[ \t]+(?:all the way[ \t]+)?(?:back[ \t]+)?(?:down[ \t]+)?to[ \t]+(?:just[ \t]+|only[ \t]+)?(?:1|one)(?![\d/]|[.,]\d|\w)",
    # the window named between verb and value: "resets CongWin to 1 MSS", "drops the window back to one"
    rf"{RESET_VERB}[ \t]+(?:the[ \t]+|its[ \t]+)?(?:cwnd|congwin|(?:congestion[ \t]+)?window)[ \t]+"
    r"(?:all the way[ \t]+)?(?:back[ \t]+)?(?:down[ \t]+)?to[ \t]+(?:just[ \t]+|only[ \t]+)?(?:1|one)(?![\d/]|[.,]\d|\w)",
    # a board transition that ends at 1: "cwnd 12->1"
    r"\b(?:cwnd|congwin|window)\b[ \t:=]*(?<![\w./])\d+(?![\d/]|[.,]\d)[ \t]*->[ \t]*1(?![\d/]|[.,]\d|\w)",
]


def halving_numbers(text: str) -> str | None:
    """A threshold written as old -> new with new = old / 2 ("ssthresh 16 -> 8")."""
    for m in re.finditer(rf"\b(?:ss)?thresh\w*{S}{{0,30}}?{NUMBER}[ \t]*(?:->|to)[ \t]*{NUMBER}", text):
        if int(m.group(2)) * 2 == int(m.group(1)):
            return m.group(0)
    return None


def tcp_starts_at_1(d: Doc) -> Hit:
    """The congestion window starts at 1 MSS: a start word, then "1 MSS" / "cwnd = 1" in the same sentence."""
    return hit(first(d.full, near(START, ONE_MSS, 60)))


def tcp_doubling(d: Doc) -> Hit:
    """An explicit doubling sequence of 3+ numbers in one sentence or board note: "1, 2, 4", "2 -> 4 -> 8"."""
    return hit(sequence(d.full, lambda v: 2 * v, 1))


def tcp_concrete_threshold(d: Doc) -> Hit:
    """A concrete numeric ssthresh / threshold value is used ("threshold = 8", "ssthresh of 16 MSS"); "½ CongWin"
    alone does not count."""
    return hit(first(d.full, *THRESHOLD_VALUE))


ONE_UNIT = r"(?<![\w./])(?:1|one)[ \t]*(?:mss|segments?|packets?)\b"


def tcp_additive(d: Doc) -> Hit:
    """After the threshold the window grows linearly, +1 per RTT: "+1 MSS per RTT", "+1/RTT", "one segment every
    round trip", "over one RTT (or one full window of ACKs) it grows by 1 MSS", a +1 sequence such as "8 -> 9 -> 10",
    or "linear" with "+1" in one sentence."""
    return hit(first(d.full, near(PLUS_ONE, PER_RTT, 6), near(ONE_UNIT, PER_RTT, 6),
                     r"\+[ \t]*1[ \t]*(?:mss|segments?)?[ \t]*/[ \t]*(?:rtt|round)",
                     near(PER_RTT, GROWS_ONE, 30),
                     near(r"\blinear\w*|\badditive\w*", STRICT_PLUS_ONE, 60),
                     near(STRICT_PLUS_ONE, r"\blinear\w*|\badditive\w*", 60))
               or sequence(d.full, lambda v: v + 1, 2))


def tcp_timeout(d: Doc) -> Hit:
    """On a timeout the threshold is halved AND cwnd goes back to 1, both stated in the step(s) that mention
    the timeout."""
    text = "\n\n".join(s for s in d.steps if re.search(TIMEOUT, s))
    if not text:
        return False, "no step mentions a timeout"
    return all_of(first(text, *HALVES) or halving_numbers(text), first(text, *RESET_TO_1))


# ================================================================ checks: flowchart_invalid_twice

READ_INPUT = r"\bread\w*[ \t]+(?:[\w']+[ \t]+){0,2}?input\b|\binput[ \t]+(?:is[ \t]+)?read\b"
INVALID = (r"\binvalid\b|\bnot valid\b|\bisn't valid\b|\bfails?\b|\bfailed\b|\bno\b(?![ \t]+errors?\b)|\bbad\b"
           r"|\bwrong\b")
CONDITION = r"\bonly\b|\buntil\b|\bunless\b|\bonce\b|\bwhen\b|\bif\b|\bfinally\b|\beventually\b|\bas soon as\b"
VALID_YES = r"(?<!not )(?<!n't )\bvalid\b|\byes\b"
EXIT = r"\bprocess\w*|\bend\b|\bexit\w*|\bescap\w*|\bleav\w*"


def flowchart_path(d: Doc) -> Hit:
    """The lesson walks from Read input into the Valid? decision (in that order, within one step)."""
    return hit(next((m for s in d.steps if (m := first(s, rf"(?:{READ_INPUT})[\s\S]{{0,200}}?\b(?:valid|decision|diamond)\b"))),
                    None))


def flowchart_no_branch(d: Doc) -> Hit:
    """An invalid input takes the No branch to Show error (invalid / No, then error, in one sentence)."""
    return hit(first(d.full, near(INVALID, r"\berror", 60)))


def flowchart_loop_back(d: Doc) -> Hit:
    """After the error the flow returns to Read input ("back to Read input", "loops to Read input", "read input
    again")."""
    return hit(first(d.full, near(r"\bback\b|\breturn\w*|\bloop\w*|\bagain\b|\bsends?\b|\bjumps?\b", READ_INPUT, 40),
                     rf"(?:{READ_INPUT})[ \t]+again", r"\b(?:back|return\w*)[ \t]+to[ \t]+(?:the[ \t]+)?input\b"))


def flowchart_twice(d: Doc) -> Hit:
    """The second attempt / second error is shown explicitly ("second try", "2nd error", "attempt 2", "invalid
    again", "another error"); the question's own word "twice" does not count."""
    return hit(first(d.full, r"\bsecond\b|\b2nd\b|\b(?:attempt|try|round|pass|input|loop|iteration)[ \t]*#?[ \t]*2\b"
                             r"|\banother[ \t]+(?:error|invalid|bad|failed)|\b(?:invalid|fails?|failed|error|wrong)[ \t]+again\b"))


def flowchart_exit(d: Doc) -> Hit:
    """Only a valid input (the Yes branch) reaches Process data / End: a condition word, valid / yes, then
    process / end / exit in one sentence ("only a Yes ... Process data", "once it is valid ... End")."""
    return hit(first(d.full, near(near(CONDITION, VALID_YES, 30), EXIT, 60),
                     near(EXIT, near(r"\bonly\b|\bonce\b|\bwhen\b|\bif\b|\buntil\b", VALID_YES, 30), 40)))


CHECKS: dict[str, list[tuple[str, Callable[[Doc], Hit]]]] = {
    "dijkstra_AtoE": [("init", dijkstra_init), ("relax_A", dijkstra_relax_A), ("relax_I_all", dijkstra_relax_I_all),
                      ("order", dijkstra_order), ("answer", dijkstra_answer)],
    "tcp_cwnd": [("starts_at_1", tcp_starts_at_1), ("doubling", tcp_doubling),
                 ("concrete_threshold", tcp_concrete_threshold), ("additive", tcp_additive),
                 ("timeout", tcp_timeout)],
    "flowchart_invalid_twice": [("path", flowchart_path), ("no_branch", flowchart_no_branch),
                                ("loop_back", flowchart_loop_back), ("twice", flowchart_twice),
                                ("exit", flowchart_exit)],
}


def bench_check(check: BenchCheck, text: str) -> Hit:
    """Every "all" regex matches AND at least min_any of the "any" regexes match (case-insensitive)."""
    ok, evidence = True, []
    for i, p in enumerate(check.all, 1):
        m = re.search(p, text, RE_FLAGS)
        ok = ok and m is not None
        evidence.append(m.group(0) if m else f"MISSING all[{i}]")
    if check.any:
        found = [m.group(0) for p in check.any if (m := re.search(p, text, RE_FLAGS))]
        ok = ok and len(found) >= check.min_any
        evidence += found[:3] if len(found) >= check.min_any else \
            [f"MISSING any: {len(found)} of {len(check.any)} matched, need {check.min_any}"] + found[:3]
    return ok, " | ".join(evidence)


def score_bench(case: Case, lesson: dict) -> dict[str, Any]:
    """score() for a bench case: its declarative checks on the lesson text (no node-letter prefixes)."""
    doc = lesson_doc(lesson, None)
    checks = {}
    for check in case.checks:
        ok, evidence = bench_check(check, doc.full)
        checks[check.name] = {"pass": bool(ok), "evidence": evidence}
    passed = sum(c["pass"] for c in checks.values())
    return {"checks": checks, "passed": passed, "total": len(checks), "score": round(passed / len(checks), 3),
            "all_passed": passed == len(checks), "checked_text": doc.full}


def score(case: str, lesson: dict, regions: dict[str, str] | None) -> dict[str, Any]:
    """{checks: {name: {pass, evidence}}, passed, total, score, all_passed, checked_text}."""
    if case not in CHECKS:
        return score_bench(get_case(case), lesson)
    doc = lesson_doc(lesson, regions)
    checks = {}
    for name, fn in CHECKS[case]:
        ok, evidence = fn(doc)
        checks[name] = {"pass": bool(ok), "evidence": evidence}
    passed = sum(c["pass"] for c in checks.values())
    return {"checks": checks, "passed": passed, "total": len(checks), "score": round(passed / len(checks), 3),
            "all_passed": passed == len(checks), "checked_text": doc.full}


def describe_check(fn: Callable) -> str:
    return " ".join((fn.__doc__ or "").split())


# ================================================================ child: one lesson in a fresh process

def child_main(args: argparse.Namespace) -> int:
    backend = Path(args.backend).resolve()
    sys.path.insert(0, str(backend))
    out: dict[str, Any] = {"ok": False}
    try:
        import app

        app_file = Path(app.__file__).resolve()
        out["app_file"] = str(app_file)
        if not app_file.is_relative_to(backend):
            raise RuntimeError(f"imported app from {app_file}, not from {backend}")
        from fastapi.testclient import TestClient

        from app import config
        from app import main as api

        out.update(model_default=config.OPENAI_MODEL, reasoning_effort=config.OPENAI_REASONING_EFFORT,
                   llm_cache=bool(config.LLM_CACHE), data_dir=str(config.DATA_DIR))
        case = get_case(args.cases)
        with TestClient(api.app, raise_server_exceptions=False) as client:
            t0 = time.perf_counter()
            if case.page is None:
                r = client.post("/api/images", files={"file": (case.source.name, case.source.read_bytes(),
                                                               _image_type(case.source))})
            else:
                r = client.post("/api/documents",
                                files={"file": (case.source.name, case.source.read_bytes(), "application/pdf")})
                _expect(r, "document upload")
                r = client.post(f"/api/documents/{r.json()['doc_id']}/pages/{case.page}/perceive")
            _expect(r, "perception")
            perception = r.json()
            out["perceive_s"] = round(time.perf_counter() - t0, 3)
            regions = perception.get("regions") or []
            out["perception"] = {k: perception.get(k) for k in ("image_id", "width", "height", "doc_id", "page",
                                                                "source_pages", "timings")}
            out["perception"]["regions"] = len(regions)
            out["regions"] = {r["id"]: r["text"] for r in regions if r.get("text")}
            if args.dry_run:
                out["ok"] = True
                return 0
            request = {"image_id": perception["image_id"], "question": case.question}
            out["request"] = request
            t1 = time.perf_counter()
            r = client.post("/api/lessons", json=request)
            out["lesson_s"] = round(time.perf_counter() - t1, 3)
            out["status"] = r.status_code
            _expect(r, "lesson")
            out["lesson"] = r.json()
            out["ok"] = True
    except Exception as exc:  # recorded in the result; the parent decides what to do
        out["error"] = f"{type(exc).__name__}: {exc}"[:600]
    finally:
        try:
            from app.tutor import llm

            out["llm_stats"] = dict(llm.stats)
        except Exception:
            pass
        Path(args.result).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if out["ok"] else 1


def _image_type(path: Path) -> str:
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}.get(
        path.suffix.lower(), "image/png")


def _expect(r: Any, what: str) -> None:
    if r.status_code != 200:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text[:300]
        raise RuntimeError(f"{what} failed: HTTP {r.status_code}: {detail}")


# ================================================================ parent: runs, files, transcripts

def read_env_value(name: str) -> str:
    """A value from the repo-root .env (else the environment). Never printed."""
    try:
        lines = (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return os.environ.get(name, "")


_SECRETS: list[str] = []


def scrub(text: str) -> str:
    for s in _SECRETS:
        if s:
            text = text.replace(s, "***")
    return re.sub(r"\b(?:sk|xi)[-_][-_A-Za-z0-9*]{8,}", "***", text)


def child_env() -> dict[str, str]:
    key = read_env_value("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY is not set in .env or the environment")
    _SECRETS.append(key)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "DATA_DIR")}
    env.update(OPENAI_API_KEY=key, LLM_CACHE="0", STUDYLENS_WARMUP="0", SERVE_FRONTEND="0", PYTHONUTF8="1",
               PYTHONIOENCODING="utf-8")
    return env


def backend_info(backend: Path) -> dict[str, Any]:
    def git(*a: str) -> str:
        try:
            return subprocess.run(["git", "--no-optional-locks", "-C", str(backend), *a], capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    return {"path": str(backend), "commit": git("rev-parse", "--short", "HEAD"),
            "subject": git("log", "-1", "--format=%s"), "dirty": bool(git("status", "--porcelain", "--", "."))}


def run_file(out_dir: Path, case: str, run: int) -> Path:
    return out_dir / f"{case}_run{run}.json"


def run_one(args: argparse.Namespace, env: dict[str, str], info: dict, out_dir: Path, case: str, run: int) -> dict:
    tmp_root = Path(args.tmp) if args.tmp else None
    if tmp_root:
        tmp_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f"eval_{args.version}_{case}_{run}_", dir=tmp_root))
    result_path, log_path = tmp / "result.json", tmp / "child.log"
    cmd = [sys.executable, str(Path(__file__).resolve()), "--child", "--backend", info["path"], "--cases", case,
           "--result", str(result_path)] + (["--dry-run"] if args.dry_run else [])
    started = datetime.now().astimezone()
    print(f"[{args.version}] {case} run {run}: started {started:%H:%M:%S}", flush=True)
    try:
        with open(log_path, "wb") as log:
            proc = subprocess.run(cmd, env=dict(env, DATA_DIR=str(tmp / "data")), stdout=log, stderr=subprocess.STDOUT,
                                  timeout=CHILD_TIMEOUT_S)
        code: int | str = proc.returncode
    except subprocess.TimeoutExpired:
        code = "timeout"
    try:
        raw = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {"ok": False, "error": f"child produced no result (exit {code})"}
    if not raw.get("ok"):
        try:
            raw["log_tail"] = scrub("\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
        except OSError:
            pass
        raw["error"] = scrub(str(raw.get("error") or f"exit {code}"))
    c = get_case(case)
    record: dict[str, Any] = {
        "version": args.version, "note": args.note, "case": case, "topic": c.topic, "run": run, "question": c.question,
        "source": c.source.name, "page": c.page, "backend": info, "started": started.isoformat(timespec="seconds"),
        "finished": datetime.now().astimezone().isoformat(timespec="seconds"), "jobs": args.jobs,
        "dry_run": bool(args.dry_run), **raw,
    }
    if record.get("ok") and record.get("lesson"):
        record.update(score(case, record["lesson"], record.get("regions")))
    if not args.dry_run:
        run_file(out_dir, case, run).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    status = (f"{record['passed']}/{record['total']} checks, lesson {record.get('lesson_s')} s" if "passed" in record
              else ("perception ok, " + f"{record.get('perception', {}).get('regions')} regions, "
                    f"{record.get('perceive_s')} s") if record.get("ok") else f"FAILED: {record.get('error')}")
    print(f"[{args.version}] {case} run {run}: {status}", flush=True)
    return record


def load_runs(out_dir: Path) -> list[dict]:
    runs = []
    for path in sorted(out_dir.glob("*_run*.json")):
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            print(f"skipping unreadable {path}", file=sys.stderr)
    order = case_order()
    return sorted(runs, key=lambda r: (order.get(r.get("case"), len(order)), str(r.get("case")), r.get("run", 0)))


def write_version_files(out_dir: Path, version: str, audited: str | None = None) -> list[dict]:
    """(Re)score every saved run of a version, then write results.json and transcripts.md. `audited` records that
    the verdicts were checked by hand (kept across later rescoring until replaced)."""
    try:
        audited = audited or json.loads((out_dir / "results.json").read_text(encoding="utf-8")).get("audited")
    except (OSError, ValueError):
        pass
    runs = load_runs(out_dir)
    for rec in runs:
        if rec.get("ok") and rec.get("lesson") and has_checks(rec.get("case")):
            rec.update(score(rec["case"], rec["lesson"], rec.get("regions")))
            run_file(out_dir, rec["case"], rec["run"]).write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                                  encoding="utf-8")
    rows = []
    for rec in runs:
        lesson = rec.get("lesson") or {}
        timings = lesson.get("timings") or {}
        rows.append({
            "case": rec.get("case"), "topic": case_topic(rec.get("case"), [rec]), "run": rec.get("run"),
            "ok": bool(rec.get("ok")), "error": rec.get("error"),
            "score": rec.get("score"), "passed": rec.get("passed"), "total": rec.get("total"),
            "all_passed": rec.get("all_passed"),
            "checks": {k: v["pass"] for k, v in (rec.get("checks") or {}).items()},
            "lesson_s": rec.get("lesson_s"), "perceive_s": rec.get("perceive_s"), "steps": len(lesson.get("steps") or []),
            "model": lesson.get("model"), "llm_s": timings.get("llm"), "input_tokens": timings.get("input_tokens"),
            "output_tokens": timings.get("output_tokens"), "warnings": len(lesson.get("warnings") or []),
            "started": rec.get("started"),
        })
    first_rec = runs[0] if runs else {}
    results = {"version": version, "note": first_rec.get("note"), "backend": first_rec.get("backend"),
               "updated": datetime.now().astimezone().isoformat(timespec="seconds"), "audited": audited, "runs": rows}
    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "transcripts.md").write_text(transcripts(version, runs), encoding="utf-8")
    return rows


def _md(text: str) -> str:
    return " ".join(str(text or "").split()).replace("|", "\\|")


def transcripts(version: str, runs: list[dict]) -> str:
    first_rec = runs[0] if runs else {}
    b = first_rec.get("backend") or {}
    out = [f"# Lesson transcripts: {version}", "",
           f"Backend {b.get('commit', '?')} ({b.get('subject', '')}){' + uncommitted changes' if b.get('dirty') else ''}."
           + (f" {first_rec.get('note')}." if first_rec.get("note") else ""),
           "Every lesson of the benchmark, as the student hears it (narration) and sees it (board text, sketch), "
           "with the automatic checks. Board texts attached to a lettered node show the letter first. "
           "Made by backend/scripts/eval_lessons.py.", ""]
    for rec in runs:
        case, lesson = rec.get("case"), rec.get("lesson") or {}
        out.append(f"## {case}, run {rec.get('run')}")
        out.append("")
        out.append(f"Question: \"{rec.get('question')}\" ({rec.get('source')}" + (f", page {rec['page']}" if rec.get("page") else "") + ")")
        if not rec.get("ok"):
            out += ["", f"FAILED: {rec.get('error')}", ""]
            continue
        marks = ", ".join(f"{k} {'PASS' if v['pass'] else 'FAIL'}" for k, v in (rec.get("checks") or {}).items())
        out.append(f"Score {rec.get('passed')}/{rec.get('total')} ({marks}). Lesson {rec.get('lesson_s')} s, "
                   f"{len(lesson.get('steps') or [])} steps, model {lesson.get('model')}.")
        out.append("")
        out.append(f"**{_md(lesson.get('title'))}**: {_md(lesson.get('summary'))}")
        out.append("")
        regions = rec.get("regions") or {}
        for s in lesson.get("steps") or []:
            out.append(f"{s.get('index')}. **{_md(s.get('title'))}**: {_md(s.get('narration'))}")
            board = [board_text(a, regions) for a in s.get("annotations") or []]
            board = [f"`{_md(t)}`" for t in board if t]
            if board:
                out.append(f"   - board: {' · '.join(board)}")
            if s.get("sketch"):
                out.append(f"   - sketch: `{_md(s['sketch'].replace(chr(10), ' ; '))}`")
        failed = {k: v["evidence"] for k, v in (rec.get("checks") or {}).items() if not v["pass"]}
        if failed:
            out.append("")
            out.append("Missing: " + "; ".join(f"{k}: {_md(v)}" for k, v in failed.items()))
        out.append("")
    return "\n".join(out) + "\n"


def run_version(args: argparse.Namespace) -> int:
    backend = Path(args.backend).resolve()
    if not (backend / "app" / "main.py").is_file():
        raise SystemExit(f"{backend} is not a backend/ directory (no app/main.py)")
    cases = _cases(args.cases, _scope(args))
    out_dir = Path(args.out).resolve() if args.out else DEFAULT_OUT / args.version
    out_dir.mkdir(parents=True, exist_ok=True)
    run_ids = [int(x) for x in args.run_ids.split(",")] if args.run_ids else list(range(1, args.runs + 1))
    info = backend_info(backend)
    env = child_env()
    todo = []
    for run in run_ids:
        for case in cases:
            path = run_file(out_dir, case, run)
            if not args.force and not args.dry_run and path.is_file():
                try:
                    if json.loads(path.read_text(encoding="utf-8")).get("ok"):
                        print(f"[{args.version}] {case} run {run}: already done, skipped ({path.name})")
                        continue
                except (OSError, ValueError):
                    pass
            todo.append((case, run))
    print(f"[{args.version}] backend {info['commit']} {info['subject']!r}{' (dirty)' if info['dirty'] else ''}: "
          f"{len(todo)} lesson(s) to make, {args.jobs} at a time", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        records = list(pool.map(lambda t: run_one(args, env, info, out_dir, *t), todo))
    if not args.dry_run:
        write_version_files(out_dir, args.version)
    return 0 if all(r.get("ok") for r in records) else 1


def _scope(args: argparse.Namespace) -> str:
    return "all" if getattr(args, "all", False) else "bench" if getattr(args, "bench", False) else "core"


def _cases(spec: str | None, scope: str = "core") -> list[str]:
    """Case names from --cases (names or shell-style patterns such as "math_*", looked up among core + bench
    cases), else every case of the scope: core (default), bench (--bench) or all (--all)."""
    known = all_cases()
    pool = {"core": list(CASES), "bench": list(bench_cases()), "all": list(known)}[scope]
    specs = [c.strip() for c in (spec or "").split(",") if c.strip()]
    if not specs:
        if not pool:
            raise SystemExit(f"no {scope} cases (bench cases live in {BENCH_CASES_DIR})")
        return pool
    names: list[str] = []
    unknown = []
    for s in specs:
        hits = [n for n in known if fnmatch.fnmatchcase(n, s)] if any(ch in s for ch in "*?[") else \
            ([s] if s in known else [])
        if not hits:
            unknown.append(s)
        names += [h for h in hits if h not in names]
    if unknown:
        raise SystemExit(f"unknown case(s) {unknown}; known: {list(known)}")
    return names


# ================================================================ summary across versions

def _mean(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def _fmt(v: float | None, digits: int = 2, suffix: str = "") -> str:
    return "n/a" if v is None else f"{v:.{digits}f}{suffix}"


def _version_dir(spec: str) -> Path:
    p = Path(spec)
    return p.resolve() if p.is_dir() else DEFAULT_OUT / spec


def _excerpt(runs: list[dict]) -> tuple[dict, dict] | None:
    """A typical Dijkstra run (score closest to the version's mean, earliest run on ties) and the step in which
    it first works out E's distance (else its last step)."""
    ok = [r for r in runs if r.get("ok") and r.get("lesson")]
    if not ok:
        return None
    mean = statistics.fmean(r["score"] for r in ok)
    rec = min(ok, key=lambda r: (abs(r["score"] - mean), r["run"]))
    steps = rec["lesson"].get("steps") or []
    regions = rec.get("regions") or {}
    chosen = next((s for s in steps if re.search(pair("e", 3), step_text(s, regions))), steps[-1] if steps else None)
    return (rec, chosen) if chosen else None


def _check_names(case: str, rows: list[dict]) -> list[str]:
    """The check names of a case: core functions, else the bench case file, else as recorded in its runs."""
    if case in CHECKS:
        return [n for n, _ in CHECKS[case]]
    if case in bench_cases():
        return [k.name for k in bench_cases()[case].checks]
    names: list[str] = []
    for r in rows:
        names += [n for n in (r.get("checks") or {}) if n not in names]
    return names


def _case_where(case: str, records: list[dict]) -> tuple[str, str]:
    """(question, where the page comes from) of a case, for the summary."""
    c = all_cases().get(case)
    if case in CASES:
        return c.question, f"{c.source.name}, page {c.page}" if c.page else f"samples/synthetic/clean/{c.source.name}"
    if c is not None:
        rel = c.source.relative_to(ROOT).as_posix() if c.source.is_relative_to(ROOT) else str(c.source)
        return c.question, rel + (f", page {c.page}" if c.page else "")
    rec = next((r for r in records if r.get("case") == case), {})
    return str(rec.get("question") or "?"), str(rec.get("source") or "?") + (f", page {rec['page']}" if rec.get("page") else "")


def _score_cell(rows: list[dict], pct: bool = False) -> str:
    """Mean score and runs passing every check, e.g. "0.80 (2/3 all)"; rows are ok runs."""
    if not rows:
        return "n/a"
    share = sum(bool(r["all_passed"]) for r in rows)
    return f"{_fmt(_mean([r['score'] for r in rows]))} ({share}/{len(rows)} all{f', {share / len(rows):.0%}' if pct else ''})"


def build_summary(specs: list[str]) -> str:
    versions = []
    for spec in specs:
        d = _version_dir(spec)
        if not (d / "results.json").is_file():
            raise SystemExit(f"no results.json in {d}; run the benchmark for {spec} first")
        results = json.loads((d / "results.json").read_text(encoding="utf-8"))
        versions.append((results.get("version") or spec, d, results, load_runs(d)))

    # the core cases (always, as before), then every other case that has runs in one of the versions, by topic
    case_rows = {}
    for _, _, res, _ in versions:
        for r in res["runs"]:
            case_rows.setdefault(r.get("case"), []).append(r)
    topic_of = {c: ("core" if c in CASES else case_topic(c, case_rows.get(c))) for c in [*CASES, *case_rows] if c}
    order = case_order()
    cases = list(CASES) + sorted((c for c in case_rows if c and c not in CASES),
                                 key=lambda c: (topic_of[c], order.get(c, len(order)), c))
    n_bench = len(cases) - len(CASES)

    records = [rec for *_, runs in versions for rec in runs]
    models = sorted({r.get("model") for _, _, res, _ in versions for r in res["runs"] if r.get("model")})
    efforts = sorted({str(rec.get("reasoning_effort")) for rec in records if rec.get("reasoning_effort")})
    dates = sorted({(r.get("started") or "")[:10] for _, _, res, _ in versions for r in res["runs"] if r.get("started")})
    jobs = sorted({rec.get("jobs") for rec in records if rec.get("jobs")})
    spans = [(min(r["started"] for r in runs), max(r.get("finished") or r["started"] for r in runs))
             for *_, runs in versions if runs and all(r.get("started") for r in runs)]
    together = len(spans) > 1 and max(s for s, _ in spans) < min(f for _, f in spans)
    conditions = (f" Lessons were made {', '.join(map(str, jobs))} at a time per version"
                  + (", with the versions running at the same time, so their latencies are comparable" if together else "")
                  + ".") if jobs else ""
    pages = ("Three fixed pages with a focus question each" if not n_bench else
             f"{len(cases)} fixed pages with a focus question each (the {len(CASES)} core cases with hand-written "
             f"checks, plus {n_bench} bench cases from `samples/bench/cases/` with declarative regex checks)")
    out = ["# Lesson-quality benchmark", "",
           f"Does the tutor teach the procedure on the page correctly? {pages}; "
           "every run is a real lesson from `POST /api/lessons`, scored by automatic fact checks "
           "(`backend/scripts/eval_lessons.py`). "
           f"Model {', '.join(models) or '?'}" + (f" (reasoning effort {', '.join(efforts)})" if efforts else "")
           + "; LLM cache off and a fresh data dir per run, so the runs are independent; "
           f"run on {', '.join(dates) or '?'}.{conditions}", "",
           "| version | backend commit | what it adds | lessons | verdicts checked by hand |", "|---|---|---|---|---|"]
    for label, d, res, runs in versions:
        n_ok = sum(1 for r in res["runs"] if r["ok"])
        backends: dict[tuple, int] = {}  # every backend state the version's runs were made with, in order
        for rec in runs or [res]:
            b = rec.get("backend") or {}
            key = (b.get("commit", "?"), _md(b.get("subject")), bool(b.get("dirty")))
            backends[key] = backends.get(key, 0) + 1
        made_with = "; ".join(f"`{c}` {s}{' (+ uncommitted changes)' if dirty else ''}"
                              + (f" ({n} runs)" if len(backends) > 1 else "")
                              for (c, s, dirty), n in backends.items())
        out.append(f"| {label} | {made_with} "
                   f"| {_md(res.get('note') or '')} | {n_ok} ok / {len(res['runs'])} | {_md(res.get('audited') or 'no')} |")
    out += ["", "## Overview: mean score (share of checks passed) and runs passing every check", "",
            "| case | " + " | ".join(label for label, *_ in versions) + " |",
            "|---|" + "---|" * len(versions)]
    for case in cases:
        cells = []
        for _, _, res, _ in versions:
            rows = [r for r in res["runs"] if r["case"] == case and r["ok"]]
            if not rows:
                cells.append("n/a")
                continue
            cells.append(f"{_fmt(_mean([r['score'] for r in rows]))} ({sum(bool(r['all_passed']) for r in rows)}/{len(rows)} all)")
        out.append(f"| {case} | " + " | ".join(cells) + " |")
    all_cells = []
    for _, _, res, _ in versions:
        rows = [r for r in res["runs"] if r["ok"] and r.get("score") is not None]
        all_cells.append(f"{_fmt(_mean([r['score'] for r in rows]))} ({sum(bool(r['all_passed']) for r in rows)}/{len(rows)} all)"
                         if rows else "n/a")
    out.append("| **all cases** | " + " | ".join(f"**{c}**" for c in all_cells) + " |")

    topics = sorted({topic_of[c] for c in cases}, key=lambda t: (t != "core", t))
    out += ["", "## Per topic: mean score and runs passing every check", "",
            "Every run counts once (mean over the runs of the topic's cases); \"k/n all\" = runs passing every check. "
            "Core = the three original cases.", "",
            "| topic | cases | " + " | ".join(label for label, *_ in versions) + " |",
            "|---|---|" + "---|" * len(versions)]
    for topic in topics:
        names = {c for c in cases if topic_of[c] == topic}
        cells = [_score_cell([r for r in res["runs"] if r["case"] in names and r["ok"] and r.get("score") is not None], True)
                 for _, _, res, _ in versions]
        out.append(f"| {topic} | {len(names)} | " + " | ".join(cells) + " |")
    if n_bench:
        bench_names = {c for c in cases if c not in CASES}
        cells = [_score_cell([r for r in res["runs"] if r["case"] in bench_names and r["ok"] and r.get("score") is not None], True)
                 for _, _, res, _ in versions]
        out.append(f"| *all bench* | {len(bench_names)} | " + " | ".join(cells) + " |")
    cells = [_score_cell([r for r in res["runs"] if r["ok"] and r.get("score") is not None], True) for _, _, res, _ in versions]
    out.append(f"| **all** | {len(cases)} | " + " | ".join(f"**{c}**" for c in cells) + " |")

    for (la, _, ra, _), (lb, _, rb, _) in zip(versions, versions[1:]):
        out += ["", f"## What changed from {la} to {lb}", ""]
        for case in cases:
            a = [r for r in ra["runs"] if r["case"] == case and r["ok"]]
            b = [r for r in rb["runs"] if r["case"] == case and r["ok"]]
            if not a or not b:
                continue
            moved = []
            for name in _check_names(case, a + b):
                ca, cb = sum(bool(r["checks"].get(name)) for r in a), sum(bool(r["checks"].get(name)) for r in b)
                if ca / len(a) != cb / len(b):
                    moved.append(f"`{name}` {ca}/{len(a)} -> {cb}/{len(b)}")
            sa, sb = _mean([r["score"] for r in a]), _mean([r["score"] for r in b])
            alla, allb = sum(bool(r["all_passed"]) for r in a), sum(bool(r["all_passed"]) for r in b)
            out.append(f"- **{case}**: mean score {_fmt(sa)} -> {_fmt(sb)}, all checks {alla}/{len(a)} -> {allb}/{len(b)}; "
                       + (f"checks that moved: {', '.join(moved)}." if moved else "no check moved."))

    for case in cases:
        names = _check_names(case, case_rows.get(case) or [])
        question, where = _case_where(case, records)
        heading = case if case in CASES else f"{case} ({topic_of[case]})"
        out += ["", f"## {heading}", "", f"Question: \"{question}\" ({where}).", "",
                "| version | runs | mean score | scores per run | all checks pass | " + " | ".join(names)
                + " | mean steps | mean lesson latency |",
                "|---|---|---|---|---|" + "---|" * len(names) + "---|---|"]
        for label, _, res, _ in versions:
            rows = [r for r in res["runs"] if r["case"] == case]
            ok = [r for r in rows if r["ok"]]
            failed = len(rows) - len(ok)
            if not ok:
                out.append(f"| {label} | {len(rows)} ({failed} failed) | n/a |" + " |" * (len(names) + 4))
                continue
            counts = [f"{sum(bool(r['checks'].get(n)) for r in ok)}/{len(ok)}" for n in names]
            share = sum(bool(r["all_passed"]) for r in ok)
            per_run = ", ".join("{passed}/{total}".format(**r) for r in sorted(ok, key=lambda r: r["run"]))
            out.append(
                f"| {label} | {len(ok)}{f' (+{failed} failed)' if failed else ''} | {_fmt(_mean([r['score'] for r in ok]))} | "
                f"{per_run} | {share}/{len(ok)} ({share / len(ok):.0%}) | "
                + " | ".join(counts)
                + f" | {_fmt(_mean([r['steps'] for r in ok]), 1)} | {_fmt(_mean([r['lesson_s'] for r in ok]), 1, ' s')} |")
        if case == "dijkstra_AtoE":
            out += ["", "Verbatim excerpts (a typical run of each version: the step where it first works out E's "
                        "distance; board texts after the narration):", ""]
            for label, _, _, runs in versions:
                ex = _excerpt([r for r in runs if r.get("case") == case])
                if ex is None:
                    continue
                rec, step = ex
                board = [board_text(a, rec.get("regions") or {}) for a in step.get("annotations") or []]
                board_s = " · ".join(f"`{_md(t)}`" for t in board if t)
                out.append(f"- **{label}**, run {rec['run']} (score {rec['passed']}/{rec['total']}), step {step.get('index')} "
                           f"of {len(rec['lesson'].get('steps') or [])}: \"{_md(step.get('narration'))}\""
                           + (f" Board: {board_s}" if board_s else ""))

    out += ["", "## How the checks work", "",
            "Each check is a small regex function in `backend/scripts/eval_lessons.py`, run on the step narrations, "
            "the text written on the board (labels and arrow captions; a note attached to a lettered graph node is "
            "read with the letter first, e.g. `b: ∞ -> 5`, and `?` marks an arrow end whose region has no one-letter "
            "OCR text: on the Dijkstra slide the OCR does not read the I inside its circle) and the margin sketch "
            "(node labels, not Mermaid ids), lower-cased, with arrows (→, -->, =>) normalised to `->`. "
            "Score = checks passed / checks of the case. Each run file stores the matched evidence of every check, "
            "so a pass or fail can be audited (the versions table says which versions had every verdict checked by "
            "hand). Step titles, summary and quiz are not checked.", ""]
    for case in CASES:
        out.append(f"- **{case}**")
        for name, fn in CHECKS[case]:
            out.append(f"  - `{name}`: {describe_check(fn)}")
    if n_bench:
        out += ["", "Bench cases (`samples/bench/cases/<case>.json`) use declarative checks instead: case-insensitive "
                    "regexes over the same normalised text (without the node-letter prefix). A check passes when every "
                    "`all` regex matches and at least `min_any` (default 1) of its `any` regexes match. Each case file "
                    "also holds a reference answer and the image's source and license.", ""]
        for case in cases[len(CASES):]:
            c = bench_cases().get(case)
            out.append(f"- **{case}** ({topic_of[case]})" + ("" if c else ": case file no longer present"))
            for k in c.checks if c else ():
                out.append(f"  - `{k.name}`: {_md(k.description) or '(no description)'}")
    out += ["", "## Files", ""]
    for label, d, _, _ in versions:
        rel = d.relative_to(ROOT).as_posix() if d.is_relative_to(ROOT) else str(d)
        out.append(f"- `{rel}/`: every lesson (`<case>_run<k>.json`: lesson JSON, latency, region texts, checks with "
                   f"evidence), `results.json` (scores), `transcripts.md` (all lessons, readable)")
    out += ["", "Reproduce: `backend/.venv/Scripts/python backend/scripts/eval_lessons.py --backend <worktree>/backend "
                "--version <label> --runs 3" + (" --all" if n_bench else "") + "`, then `--summary "
                + " ".join(label for label, *_ in versions) + "`; "
                "`--rescore` re-scores saved lessons for free.", ""]
    return "\n".join(out)


# ================================================================ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", help="backend/ directory of the version to test (put first on sys.path)")
    ap.add_argument("--version", help="label of the version, e.g. L2 (output folder name)")
    ap.add_argument("--runs", type=int, default=3, help="runs per case (default 3)")
    ap.add_argument("--run-ids", help="explicit run numbers, e.g. 4 or 2,3 (overrides --runs)")
    ap.add_argument("--cases", help=f"comma-separated case names or patterns (\"math_*\"), core ({', '.join(CASES)}) or "
                                    "bench (samples/bench/cases/*.json); default: every case of the scope")
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--bench", action="store_true", help="run the bench cases only (samples/bench/cases/*.json)")
    scope.add_argument("--all", action="store_true", help="run the core cases and the bench cases")
    ap.add_argument("--list", action="store_true", help="list every case (core + bench) with its topic and checks")
    ap.add_argument("--out", help="output folder (default samples/eval/lessons/<version>/)")
    ap.add_argument("--jobs", type=int, default=1, help="lessons made in parallel (default 1)")
    ap.add_argument("--note", default="", help="what this version changes (shown in the summary)")
    ap.add_argument("--tmp", help="parent folder for the per-run temporary DATA_DIRs (default: system temp)")
    ap.add_argument("--force", action="store_true", help="redo runs that already have a result")
    ap.add_argument("--dry-run", action="store_true", help="upload + perceive only, no lesson (free); nothing saved")
    ap.add_argument("--rescore", action="store_true", help="re-run the checks on the saved lessons of --version")
    ap.add_argument("--audited", help="with --rescore: record that every verdict was checked by hand (short note)")
    ap.add_argument("--summary", nargs="+", metavar="VERSION", help="write the comparison of these versions")
    ap.add_argument("--summary-out", default=str(DEFAULT_SUMMARY), help="where --summary writes")
    ap.add_argument("--score-lesson", help="score one lesson JSON file (needs --cases)")
    ap.add_argument("--perception", help="with --score-lesson: perception JSON for the region texts")
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--result", help=argparse.SUPPRESS)
    for stream in (sys.stdout, sys.stderr):  # help / questions / evidence hold ∞, Ω, ₂...: never crash on a cp1252 console
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    args = ap.parse_args()

    if args.child:
        return child_main(args)
    if args.list:
        for name, c in all_cases().items():
            checks = [n for n, _ in CHECKS[name]] if name in CHECKS else [k.name for k in c.checks]
            src = c.source.relative_to(ROOT).as_posix() if c.source.is_relative_to(ROOT) else str(c.source)
            print(f"{name} [{c.topic}] {src}{f' p{c.page}' if c.page else ''}: \"{c.question}\" -> {', '.join(checks)}")
        return 0
    if args.score_lesson:
        case = _cases(args.cases)
        if len(case) != 1:
            raise SystemExit("--score-lesson needs exactly one case in --cases")
        blob = json.loads(Path(args.score_lesson).read_text(encoding="utf-8"))
        lesson = blob.get("lesson", blob)  # a saved run file or a bare lesson
        regions = blob.get("regions") if isinstance(blob.get("regions"), dict) else None
        if args.perception:
            p = json.loads(Path(args.perception).read_text(encoding="utf-8"))
            regions = {r["id"]: r["text"] for r in p.get("regions", []) if r.get("text")}
        result = score(case[0], lesson, regions)
        result.pop("checked_text")
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0
    if args.summary:
        text = build_summary(args.summary)
        Path(args.summary_out).write_text(text, encoding="utf-8")
        print(f"wrote {args.summary_out}")
        return 0
    if not args.version:
        raise SystemExit("--version is required")
    if args.rescore:
        out_dir = Path(args.out).resolve() if args.out else DEFAULT_OUT / args.version
        rows = write_version_files(out_dir, args.version, args.audited)
        for r in rows:
            print(f"{r['case']} run {r['run']}: " + (f"{r['passed']}/{r['total']} {r['checks']}" if r["ok"] else f"FAILED {r['error']}"))
        return 0
    if not args.backend:
        raise SystemExit("--backend is required")
    return run_version(args)


if __name__ == "__main__":
    sys.exit(main())
