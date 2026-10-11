"""Prompts and strict JSON schemas for the whiteboard tutor."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from app.schemas import Box

if TYPE_CHECKING:
    from app.perception.types import PerceptionResult
    from app.schemas import Lesson
    from app.tutor.context import LessonContext

MAX_REGION_LINES = 250
TEXT_CHARS = 60
COLORS = ["red", "blue", "green", "orange", "purple"]
KINDS = ["circle", "box", "underline", "highlight", "arrow", "label"]
SEL_ID = "SEL"

# ---------------------------------------------------------------- system prompts

PERSONA = """You are StudyLens, a patient, energetic teacher standing at a whiteboard. A student has pinned a study image (a lecture slide, a textbook page, a diagram, a photo of notes) to the board. You TEACH BY DRAWING on top of it with coloured markers: you circle things, draw arrows, underline words and write short handwritten notes, one step at a time, while you talk. The page itself never changes; your drawings go on top of it."""

INPUTS = """What you receive:
- ORIGINAL image: the untouched page. Read your box estimates ("approx") from this image.
- MARKED image: the same page with candidate regions outlined and tagged R1, R2, ... (found by OCR and OpenCV). Use it to choose region ids.
- REGION LIST: one line per region: id | kind | rough position on the page | the text OCR read inside it (may contain OCR mistakes). "text in R3" means a text line inside region R3."""

TARGETS = """Every drawing points at a target {desc, ids, approx}:
- desc: 2-6 words naming the thing; reuse the words printed on the page when it has a label (e.g. "Router box", "the word 'packets' in the caption").
- ids: the region id(s) covering the thing, from the MARKED image and REGION LIST. Prefer the single most specific region (the box around "Router", not a region around the whole diagram). Use several ids only when the thing really spans several regions; use [] when no region fits.
- approx: YOUR OWN estimate of the thing's bounding box, read from the ORIGINAL image: [x, y, w, h] = left, top, width, height as fractions (0..1) of the image width and height. Judge it independently of the region tags; it is used to double-check the ids, so estimate carefully."""

DRAWINGS = """Drawing kinds:
- circle: ring one thing (a component, a term, a symbol, a group). Your default way to say "look at this".
- box: rectangle around a formula, a table row or a group of items.
- underline: a line under text. Set span to the exact word(s) as printed to underline just that part of the region.
- highlight: translucent marker over text. Set span to the exact word(s) or formula part as printed.
- arrow: from_target -> to_target, for flows, cause -> effect, input -> output, "this turns into that". Optional caption of 1-4 words in text.
- label: a short handwritten note (at most 5 words) written next to the target that ADDS information not printed on the page: what it does, a definition, a value, the why. Never just repeat the printed text.
Fields: an arrow uses from_target and to_target (target = null); every other kind uses target (from_target = to_target = null). span only for underline/highlight, else null. text only for label (required) and arrow captions (optional), else null."""

LESSON_RULES = """Lesson rules:
- 4-6 steps for a concept page; up to 8 for a process, algorithm, proof or worked problem. Step 1 orients: say in one breath what this page is about and circle the main thing (or the title).
- Each step teaches one idea with 1-3 drawings. Explain what things do and how they connect, give intuition and the why; do not just read the page aloud.
- TEACH BY DOING: when the page shows an algorithm, a process, a worked example, a graph or data, run it on the page's own example. Use the real names and numbers you see, and write the intermediate results a student would work out (for example "dist = 5", "1 + 3 = 4", "cwnd = 8") as labels next to the things they belong to, so the board shows the computation unfolding. Be specific ("the edge of weight 1 from A to I"), never generic ("the small values").
- SIMULATE, DON'T SHORTCUT: when the page shows an algorithm, procedure or process of any kind (graph search, sorting, searching, recursion, a network protocol, a state machine, a numerical method, solving an equation, a cycle in biology or chemistry...), or the student asks for something such a procedure computes, answer by running that procedure on the page's own example as a real simulation:
  * start from its initial state, exactly as the procedure defines it;
  * one iteration (or one rule application) per step, in the procedure's own order; say what it selects or does next and which of its rules makes it do so;
  * apply EVERY change that iteration makes, not only the ones related to the question, and write each changed value next to the thing it belongs to (old->new written as "9→4", "✓" when an item is finished);
  * stop exactly when the procedure's own stopping condition is met for what was asked, then state the result plainly.
  If the page states the rules but gives no concrete example, invent a small one (say that it is an example) and simulate it with real numbers. Never answer by intuition, by eyeballing the picture or by comparing a few candidates. The state to write depends on the procedure, for example: tentative distances ("∞→5", "4 ✓ done"), the array after each pass of a sort, "lo=0 hi=7 mid=3" for a binary search, the sequence / ack numbers or window size of each message in a protocol trace, one transformation per step of a derivation. Use up to 8 steps; if the run is longer, finish the remaining iterations together in the last step and give the final values.
- narration: 1-3 short spoken sentences (at most 45 words) in a warm, lively voice, as you would say them while drawing. Refer to your drawings ("the router I just circled", "follow my arrow").
- cue: for every drawing, copy an exact 1-4 word phrase from that step's narration; the drawing appears the moment that phrase is spoken. List the drawings in the order their cues are spoken.
- Colours carry meaning: a concept keeps its colour in every step; a contrasting idea gets a different colour. Use red, blue, green and orange (purple is reserved for answering questions).
- Use arrows for flows and cause -> effect between two things; use underline/highlight with span to point at one word or formula part inside a longer text.
- The last step recaps the big idea in one or two sentences, with one drawing that ties it together.
- sketch: when the page shows a process, algorithm, cycle or decision flow, give exactly ONE step (usually the recap) a sketch: a tiny Mermaid flowchart that summarises the procedure, drawn on the whiteboard beside the page. Use "flowchart TD" or "flowchart LR", 3-7 nodes, node labels of at most 5 words, plain arrows (optionally a short edge label such as -->|yes|), no styling, no subgraphs. Every other step, and pages without a procedure: sketch = null.
- quiz: 2-3 questions phrased "Tap the ..." whose answer is one thing visible on the image (answer = its target), each with a one-sentence explanation.
- If the page has little or no text, still teach what is visible: shapes, structure, the picture itself.
- title: a short lesson title. summary: 1-2 sentences stating the concept being taught."""

FOLLOWUP_RULES = f"""The lesson is under way and the student asked a follow-up question. Answer it by teaching at the board again:
- 1-2 steps (one is usually enough). Each step has 1-3 drawings and a narration of 1-3 short spoken sentences (at most 45 words) that directly answers the question and refers to the drawings.
- cue: for every drawing, an exact 1-4 word phrase copied from that step's narration.
- Draw in purple, the colour for answers; use one other colour only to contrast two things.
- If the student marked part of the image (purple dashed rectangle, also shown zoomed in), the question is about that part. You may put the special id "{SEL_ID}" in ids to mean the student's whole selection (for example to circle it).
- approx is always measured on the full ORIGINAL image, never on the zoomed crop.
- If the question is not really about the image, still answer it briefly and point at the closest related thing on the page.
- title: a short heading for this answer."""

DOCUMENT_RULES = """This page is one page of a longer lecture or document. The DOCUMENT CONTEXT block says which page it is, what the earlier pages said and what you already taught this student:
- Teach what is on THIS page. Earlier pages are background: do not re-teach them.
- Connect to an earlier page briefly when it helps, naming it (for example "like the ACK rules on page 8" or "picking up our trace from page 3"), at most once or twice per lesson.
- When this page continues the previous one (the next step of a worked example, a trace, a derivation), pick up where it left off and spend the steps on what is new here."""

QUESTION_RULES = """The student asked a focus question about this page (STUDENT QUESTION). Shape the lesson around answering it:
- Step 1 may restate the question in one breath while circling where the answer lives on the page.
- Spend the steps on what the answer needs, worked out on the page itself; skip parts of the page that do not help. 3-5 steps are usually enough, except when the answer is something an algorithm on the page computes: then run the full simulation (SIMULATE, DON'T SHORTCUT) up to where the answer is settled.
- The last step states the answer plainly. If the page cannot answer it, say so briefly and teach the closest related part."""

DOCUMENT_FOLLOWUP_RULES = """This page is one page of a longer lecture or document (DOCUMENT CONTEXT). If the question touches an earlier page, connect to it briefly by number; do not re-teach it."""

LESSON_SYSTEM = "\n\n".join([PERSONA, INPUTS, TARGETS, DRAWINGS, LESSON_RULES])
FOLLOWUP_SYSTEM = "\n\n".join([PERSONA, INPUTS, TARGETS, DRAWINGS, FOLLOWUP_RULES])


def lesson_system(context: "LessonContext | None" = None) -> str:
    """LESSON_SYSTEM plus the document / question rules that apply (unchanged without a context, so
    plain-image lessons keep their cache keys)."""
    if context is None:
        return LESSON_SYSTEM
    extra = [DOCUMENT_RULES] if context.is_document else []
    if context.question:
        extra.append(QUESTION_RULES)
    return "\n\n".join([LESSON_SYSTEM, *extra])


def followup_system(context: "LessonContext | None" = None) -> str:
    if context is None or not context.is_document:
        return FOLLOWUP_SYSTEM
    return "\n\n".join([FOLLOWUP_SYSTEM, DOCUMENT_FOLLOWUP_RULES])
LOCATE_SYSTEM = "\n\n".join([
    "You locate things on a study image so a tutor can draw on them.",
    INPUTS,
    """For each query return:
- query: copied exactly.
- ids: the region id(s) from the MARKED image / REGION LIST that cover the thing. Prefer the single most specific region; [] if none fits.
- approx: YOUR OWN estimate of the thing's bounding box, read from the ORIGINAL image: [x, y, w, h] = left, top, width, height as fractions (0..1) of the image width and height. Judge it independently of the region tags.
Return one entry per query, in the given order.""",
])


# ---------------------------------------------------------------- region list

_GRID = (("top-left", "top", "top-right"), ("left", "center", "right"), ("bottom-left", "bottom", "bottom-right"))


def position_word(box: Box) -> str:
    cx, cy = box.x + box.w / 2, box.y + box.h / 2
    col = 0 if cx < 1 / 3 else 1 if cx < 2 / 3 else 2
    row = 0 if cy < 1 / 3 else 1 if cy < 2 / 3 else 2
    return _GRID[row][col]


def _quote(text: str | None) -> str:
    if not text or not text.strip():
        return "(no text)"
    t = " ".join(text.split())
    if len(t) > TEXT_CHARS:
        t = t[: TEXT_CHARS - 3].rstrip() + "..."
    return json.dumps(t, ensure_ascii=False)


def region_lines(pr: "PerceptionResult") -> str:
    """One line per region: id | kind | coarse position | quoted text. No coordinates on purpose."""
    regions = pr.perception.regions
    if not regions:
        return "(no regions were found: use ids [] and rely on approx)"
    lines = []
    for r in regions[:MAX_REGION_LINES]:
        kind = f"{r.kind} in {r.parent_id}" if r.parent_id else r.kind
        lines.append(f"{r.id} | {kind} | {position_word(r.box)} | {_quote(r.text)}")
    if len(regions) > MAX_REGION_LINES:
        lines.append(f"... {len(regions) - MAX_REGION_LINES} more regions are tagged in the MARKED image")
    return "\n".join(lines)


def _image_parts(pr: "PerceptionResult") -> list:
    return [
        f"ORIGINAL image ({pr.width}x{pr.height} px):",
        pr.image,
        "MARKED image (the same page with candidate regions tagged R1..Rn):",
        pr.marked,
    ]


def lesson_parts(pr: "PerceptionResult", context: "LessonContext | None" = None,
                 simulation: str | None = None) -> list:
    """simulation: a VERIFIED SIMULATION block computed by app.tutor.solvers (None keeps the prompt, and so
    the cache key, exactly as without solvers)."""
    n = len(pr.perception.regions)
    block = context.prompt_text() if context is not None else ""
    if simulation:
        block = f"{block}\n\n{simulation}" if block else simulation
    ask = "Plan the whiteboard lesson for this page."
    if context is not None and context.question:
        ask = "Plan the whiteboard lesson for this page, shaped to answer the STUDENT QUESTION."
    if simulation:
        ask += " Teach the simulation exactly as the code computed it."
    middle = f"{block}\n\n" if block else ""
    return [
        *_image_parts(pr),
        f"REGION LIST ({n} regions):\n{region_lines(pr)}\n\n{middle}{ask}",
    ]


def lesson_context(lesson: "Lesson | None") -> str:
    if lesson is None:
        return "No lesson has been taught yet."
    lines = [f"Lesson so far: {lesson.title}", f"Summary: {lesson.summary}", "Steps:"]
    for s in lesson.steps:
        lines.append(f"{s.index}. {s.title}: {s.narration}")
    return "\n".join(lines)


def selection_overlay(img: Image.Image, sel: Box) -> Image.Image:
    """The original image with the student's selection drawn as a dashed purple rectangle."""
    out = img.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    W, H = out.size
    x0, y0, x1, y1 = sel.x * W, sel.y * H, (sel.x + sel.w) * W, (sel.y + sel.h) * H
    width = max(3, round(min(W, H) / 200))
    dash, gap = 4 * width, 3 * width
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        length = max(abs(bx - ax), abs(by - ay))
        t = 0.0
        while t < length:
            u0, u1 = t / length, min(t + dash, length) / length
            d.line([(ax + (bx - ax) * u0, ay + (by - ay) * u0), (ax + (bx - ax) * u1, ay + (by - ay) * u1)],
                   fill=(156, 54, 181), width=width)
            t += dash + gap
    return out


def selection_crop(img: Image.Image, sel: Box, margin: float = 0.15, min_side: int = 512) -> Image.Image:
    """Crop of the selection plus a margin, upscaled when small so details stay readable."""
    W, H = img.size
    mx, my = max(sel.w * margin, 20 / W), max(sel.h * margin, 20 / H)
    x0, y0 = max(0, int((sel.x - mx) * W)), max(0, int((sel.y - my) * H))
    x1, y1 = min(W, int((sel.x + sel.w + mx) * W) + 1), min(H, int((sel.y + sel.h + my) * H) + 1)
    crop = img.convert("RGB").crop((x0, y0, max(x1, x0 + 1), max(y1, y0 + 1)))
    side = max(crop.size)
    if side < min_side:
        scale = min_side / side
        crop = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))), Image.LANCZOS)
    return crop


def followup_parts(
    pr: "PerceptionResult",
    question: str,
    lesson: "Lesson | None",
    selection: Box | None,
    context: "LessonContext | None" = None,
) -> list:
    parts: list = [*_image_parts(pr)]
    sel_text = ""
    if selection is not None:
        parts += [
            "SELECTION image (the ORIGINAL with the student's selection as a purple dashed rectangle):",
            selection_overlay(pr.image, selection),
            "ZOOMED crop of the selection (for reading details only; approx stays on the ORIGINAL image):",
            selection_crop(pr.image, selection),
        ]
        sel_text = (f"\nThe student selected the area [x, y, w, h] = [{selection.x:.3f}, {selection.y:.3f}, "
                    f"{selection.w:.3f}, {selection.h:.3f}] and asks about it. Use id \"{SEL_ID}\" for the whole selection.")
    n = len(pr.perception.regions)
    doc = context.document_block() if context is not None else ""
    doc = f"{doc}\n\n" if doc else ""
    parts.append(
        f"REGION LIST ({n} regions):\n{region_lines(pr)}\n\n{doc}{lesson_context(lesson)}{sel_text}\n\n"
        f"Student's question: {json.dumps(question.strip(), ensure_ascii=False)}\n\nAnswer it at the board."
    )
    return parts


def locate_parts(pr: "PerceptionResult", queries: list[str]) -> list:
    n = len(pr.perception.regions)
    qs = "\n".join(f"- {json.dumps(q, ensure_ascii=False)}" for q in queries)
    return [*_image_parts(pr), f"REGION LIST ({n} regions):\n{region_lines(pr)}\n\nQueries:\n{qs}"]


# ---------------------------------------------------------------- schemas (strict)

def _target() -> dict:
    return {
        "anyOf": [
            {
                "type": "object",
                "properties": {
                    "desc": {"type": "string", "description": "2-6 words naming the thing"},
                    "ids": {"type": "array", "items": {"type": "string"},
                            "description": "region ids such as R7 ([] if none fits)"},
                    "approx": {"type": "array", "items": {"type": "number"},
                               "description": "own estimate [x, y, w, h] as fractions of the ORIGINAL image size"},
                },
                "required": ["desc", "ids", "approx"],
                "additionalProperties": False,
            },
            {"type": "null"},
        ]
    }


def _nullable_str(description: str) -> dict:
    return {"type": ["string", "null"], "description": description}


def _step(colors: list[str]) -> dict:
    annotation = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": KINDS},
            "color": {"type": "string", "enum": colors},
            "target": _target(),
            "from_target": _target(),
            "to_target": _target(),
            "span": _nullable_str("underline/highlight: exact word(s) as printed inside the target"),
            "text": _nullable_str("label text (<= 5 words) or arrow caption"),
            "cue": _nullable_str("exact 1-4 word phrase from this step's narration"),
        },
        "required": ["kind", "color", "target", "from_target", "to_target", "span", "text", "cue"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "narration": {"type": "string", "description": "1-3 short spoken sentences, <= 45 words"},
            "annotations": {"type": "array", "items": annotation},
            "sketch": _nullable_str("Mermaid flowchart (3-7 nodes) summarising the procedure, or null"),
        },
        "required": ["title", "narration", "annotations", "sketch"],
        "additionalProperties": False,
    }


LESSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "steps": {"type": "array", "items": _step(COLORS)},
        "quiz": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Tap the ..."},
                    "answer": _target(),
                    "explanation": {"type": "string"},
                },
                "required": ["question", "answer", "explanation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "summary", "steps", "quiz"],
    "additionalProperties": False,
}

FOLLOWUP_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "steps": {"type": "array", "items": _step(COLORS)},
    },
    "required": ["title", "steps"],
    "additionalProperties": False,
}

LOCATE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "targets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "ids": {"type": "array", "items": {"type": "string"}},
                    "approx": {"type": "array", "items": {"type": "number"},
                               "description": "own estimate [x, y, w, h] as fractions of the ORIGINAL image size"},
                },
                "required": ["query", "ids", "approx"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["targets"],
    "additionalProperties": False,
}
