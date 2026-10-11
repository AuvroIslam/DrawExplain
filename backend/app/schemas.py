"""Shared data contract for StudyLens Live Whiteboard (backend <-> frontend).

Coordinates: every Box/Point is NORMALIZED to the processed image (the image that
perception ran on, which keeps the uploaded image's aspect ratio). x, y in [0, 1]
from the top-left corner; w, h are fractions of the image width / height.
The frontend multiplies by Perception.width / Perception.height to get pixels.

Mirror of this file for the frontend: frontend/src/types.ts (keep them in sync).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Box(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Point(BaseModel):
    x: float
    y: float


# ---------------------------------------------------------------- perception

RegionKind = Literal["text", "text_block", "shape", "figure"]
RegionSource = Literal["ocr", "opencv", "merged", "user"]


class Region(BaseModel):
    """A candidate thing on the page that the tutor can point at."""

    id: str  # "R1".."Rn", stable for one image, assigned in reading order
    kind: RegionKind
    box: Box
    text: str | None = None  # OCR text inside the region (labels of shapes too)
    score: float = 1.0  # detector confidence 0..1
    source: RegionSource = "opencv"
    parent_id: str | None = None  # e.g. a text line inside a shape -> the shape's id


class Perception(BaseModel):
    image_id: str
    width: int  # processed image size in pixels
    height: int
    regions: list[Region]
    timings: dict[str, float] = Field(default_factory=dict)  # seconds per stage
    image_url: str | None = None  # served processed image
    marked_url: str | None = None  # served Set-of-Mark debug image
    source_pages: int | None = None  # page count when the upload was a PDF (one page is perceived)
    doc_id: str | None = None  # set when this image is a page of an uploaded document
    page: int | None = None  # 1-based page number within that document


# ---------------------------------------------------------------- lesson

AnnotationKind = Literal["circle", "box", "underline", "highlight", "arrow", "label"]
Color = Literal["red", "blue", "green", "orange", "purple"]
# How the drawing target was located:
#   consensus   - LLM-chosen region id and LLM's own box estimate agree -> CV box used
#   cv_snap     - LLM box estimate snapped to a different/better CV region
#   id_only     - region id trusted (text matched) although the box estimate disagreed
#   llm_refined - no matching region; LLM box tightened to the ink inside it
#   llm_only    - raw LLM box estimate (lowest confidence)
#   user        - the student's own selection
Grounding = Literal["consensus", "cv_snap", "id_only", "llm_refined", "llm_only", "user"]


class Geometry(BaseModel):
    """Resolved drawing geometry, normalized. Which fields are set depends on kind:
    circle    -> box (ellipse bounds, already padded)
    box       -> box (rectangle, already padded)
    highlight -> box (marker rectangle)
    underline -> points [start, end]
    arrow     -> points [start, control, end] (quadratic Bezier); label_box if text
    label     -> label_box (where the text is written), leader [from, to] line to the
                 target, box = target box
    """

    box: Box | None = None
    points: list[Point] | None = None
    label_box: Box | None = None
    leader: list[Point] | None = None


class Annotation(BaseModel):
    id: str  # unique within a lesson, e.g. "s2a1"
    kind: AnnotationKind
    color: Color = "red"
    target_ids: list[str] = Field(default_factory=list)  # region ids (union box if many)
    from_ids: list[str] = Field(default_factory=list)  # arrow source
    to_ids: list[str] = Field(default_factory=list)  # arrow destination
    span: str | None = None  # substring of a text region to underline/highlight
    text: str | None = None  # label text or arrow caption (short)
    cue: str | None = None  # exact phrase from the step narration; draw when it is spoken
    geometry: Geometry
    confidence: float = 1.0  # grounding confidence 0..1
    grounding: Grounding = "consensus"


class Step(BaseModel):
    index: int  # 1-based
    title: str  # short heading
    narration: str  # what the tutor says while drawing (1-3 sentences)
    annotations: list[Annotation]
    sketch: str | None = None  # Mermaid flowchart drawn beside the page (process / algorithm summary)


class QuizItem(BaseModel):
    question: str  # e.g. "Tap the device that forwards packets between networks."
    answer_ids: list[str]
    answer_box: Box  # tap inside (with tolerance) = correct
    explanation: str


class Lesson(BaseModel):
    lesson_id: str
    image_id: str
    title: str
    summary: str  # 1-2 sentence statement of the concept being taught
    steps: list[Step]
    quiz: list[QuizItem] = Field(default_factory=list)
    model: str
    timings: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)  # validator notes
    question: str | None = None  # the student's focus question, when one was asked
    context_pages: list[int] = Field(default_factory=list)  # earlier document pages the lesson builds on


class LocatedTarget(BaseModel):
    """Result of grounding one free-text query ("the router") to a box."""

    query: str
    box: Box | None
    region_ids: list[str] = Field(default_factory=list)
    grounding: Grounding
    confidence: float
    llm_box: Box | None = None  # the model's own raw estimate from the same call


# ---------------------------------------------------------------- API requests

class LessonRequest(BaseModel):
    image_id: str
    model: str | None = None
    question: str | None = None  # optional: what the student wants explained on this page


# ---------------------------------------------------------------- documents (PDF reader)

class DocumentInfo(BaseModel):
    """An uploaded PDF. Pages are browsed as plain images (no scan); a page is perceived only when the
    student asks for it to be explained (POST /api/documents/{doc_id}/pages/{page}/perceive)."""

    doc_id: str
    filename: str
    pages: int
    title: str | None = None  # PDF metadata title, else the first line of page 1
    page_sizes: list[list[int]]  # [width, height] in px of each rendered page image (1-based page i -> index i-1)
    page_url: str  # template, e.g. "/api/documents/<doc_id>/pages/{page}.png"; replace "{page}" with the number


class FollowupRequest(BaseModel):
    image_id: str
    lesson_id: str | None = None
    question: str
    selection: Box | None = None  # rectangle the student dragged on the image
    model: str | None = None


class FollowupResponse(BaseModel):
    title: str
    steps: list[Step]
    model: str
    timings: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class TTSRequest(BaseModel):
    text: str
    voice_id: str | None = None


class WordTiming(BaseModel):
    word: str
    start: float  # seconds
    end: float
    char_start: int  # index into the request text
    char_end: int  # exclusive


class TTSResponse(BaseModel):
    audio_url: str
    duration: float
    words: list[WordTiming]
    cached: bool = False


class SampleInfo(BaseModel):
    name: str  # path relative to the samples dir, e.g. "quick/network_basic.png"
    url: str  # served image url


class LoadSampleRequest(BaseModel):
    name: str
