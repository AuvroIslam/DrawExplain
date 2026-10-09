"""FastAPI app: upload -> perception -> lesson -> follow-ups, plus TTS and sample images.

Run: .venv/Scripts/python -m uvicorn app.main:app --port 8000   (from backend/)
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

import httpx
import openai
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import config, perception, tutor
from app.perception import preprocess as perception_preprocess
from app.perception.types import PerceptionResult
from app.schemas import (
    Box,
    FollowupRequest,
    FollowupResponse,
    Lesson,
    LessonRequest,
    LoadSampleRequest,
    Perception,
    SampleInfo,
    TTSRequest,
    TTSResponse,
)
from app.store import ImageStore, LessonStore, valid_id
from app.tts import eleven

log = logging.getLogger("studylens")

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/pjpeg", "image/webp"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_QUESTION_CHARS = 1000
MAX_TTS_CHARS = 2500
MIN_SELECTION = 0.02
_MODEL_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_KEYLIKE_RE = re.compile(r"\b(?:sk|xi)[-_][-_A-Za-z0-9*]{8,}")
_UPSTREAM_MODULES = ("openai", "httpx", "httpcore")  # openai 3.x raises httpx2/httpcore2 errors
FRONTEND_DIST = config.ROOT_DIR / "frontend" / "dist"

images = ImageStore()
lessons = LessonStore()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if os.getenv("STUDYLENS_WARMUP", "1") == "1":
        threading.Thread(target=_warmup, name="perception-warmup", daemon=True).start()
    yield


app = FastAPI(title="StudyLens Live Whiteboard", version="1.0", lifespan=lifespan)
# Split deployments (frontend on Vercel, API elsewhere): CORS_ORIGINS="https://a.app,https://b.app" and/or
# CORS_ORIGIN_REGEX="https://.*\.vercel\.app". Defaults cover the local Vite dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
                   if o.strip()],
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": _describe("Internal error", exc)})


# ---------------------------------------------------------------- health


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "model": config.OPENAI_MODEL, "tts": bool(config.ELEVENLABS_API_KEY)}


# ---------------------------------------------------------------- images


@app.post("/api/images", response_model=Perception)
def upload_image(file: UploadFile = File(...), page: int = Form(1)) -> Perception:
    """Upload a study image or a PDF (one page of it): prepare + perceive, return regions and URLs."""
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    ext = Path(file.filename or "").suffix.lower()
    pdf = ctype == "application/pdf" or ext == ".pdf"
    if not pdf and ctype not in IMAGE_TYPES and ext not in IMAGE_EXTS:
        raise HTTPException(400, "Unsupported file type; upload a PNG, JPEG, WebP image or a PDF")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "File is larger than 15 MB")
    pages = None
    if pdf or perception_preprocess.is_pdf(data):
        try:
            data, pages = perception_preprocess.render_pdf_page(data, page)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
    result = _ingest(data).perception
    return result.model_copy(update={"source_pages": pages}) if pages else result


@app.get("/api/images/{image_id}", response_model=Perception)
def get_image(image_id: str) -> Perception:
    return _perceived(image_id).perception


@app.get("/api/images/{image_id}/original.png")
def image_original(image_id: str) -> FileResponse:
    return _image_file(image_id, "original.png", "public, max-age=86400")


@app.get("/api/images/{image_id}/marked.png")
def image_marked(image_id: str) -> FileResponse:
    return _image_file(image_id, "marked.png", "no-cache")


# ---------------------------------------------------------------- samples


@app.get("/api/samples", response_model=list[SampleInfo])
def list_samples() -> list[SampleInfo]:
    """Images under SAMPLES_DIR (recursive, folders named "eval" skipped)."""
    root = _samples_root()
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        rel = path.relative_to(root)
        if any(part.lower() == "eval" or part.startswith(".") for part in rel.parts[:-1]):
            continue
        name = rel.as_posix()
        out.append(SampleInfo(name=name, url=f"/api/samples/file/{quote(name)}"))
    return out


@app.get("/api/samples/file/{name:path}")
def sample_file(name: str) -> FileResponse:
    return FileResponse(_sample_path(name), headers={"Cache-Control": "public, max-age=3600"})


@app.post("/api/samples/load", response_model=Perception)
def load_sample(req: LoadSampleRequest) -> Perception:
    return _ingest(_sample_path(req.name).read_bytes()).perception


# ---------------------------------------------------------------- lessons


@app.post("/api/lessons", response_model=Lesson)
def create_lesson(req: LessonRequest) -> Lesson:
    """Plan a grounded whiteboard lesson for an uploaded image."""
    pr = _perceived(req.image_id)
    model = _model(req.model)
    t0 = time.perf_counter()
    try:
        lesson = tutor.plan_lesson(pr, model=model)
    except HTTPException:
        raise
    except Exception as exc:
        raise _tutor_error("Lesson planning failed", exc) from exc
    lesson.image_id = pr.perception.image_id
    lessons.put(lesson)
    log.info(
        "lesson %s for %s: %d steps, %d warnings, %.1fs",
        lesson.lesson_id, lesson.image_id, len(lesson.steps), len(lesson.warnings), time.perf_counter() - t0,
    )
    return lesson


@app.post("/api/lessons/stream")
def create_lesson_stream(req: LessonRequest) -> StreamingResponse:
    """Streamed lesson (newline-delimited JSON): meta, header, each step as soon as it is grounded,
    then the full lesson. Errors after the stream started arrive as {"type": "error", "detail": ...}."""
    pr = _perceived(req.image_id)
    model = _model(req.model)

    def events() -> Iterator[str]:
        try:
            for ev in tutor.stream_lesson(pr, model=model):
                if ev["type"] == "lesson":
                    lessons.put(Lesson.model_validate(ev["lesson"]))
                yield json.dumps(ev, ensure_ascii=False) + "\n"
        except Exception as exc:  # the status line is already sent: report in-band
            err = exc if isinstance(exc, HTTPException) else _tutor_error("Lesson planning failed", exc)
            log.warning("streamed lesson failed: %s", err.detail)
            yield json.dumps({"type": "error", "detail": err.detail}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/lessons/{lesson_id}", response_model=Lesson)
def get_lesson(lesson_id: str) -> Lesson:
    try:
        return lessons.get(lesson_id)
    except KeyError:
        raise HTTPException(404, "Unknown lesson_id") from None


@app.post("/api/followups", response_model=FollowupResponse)
def create_followup(req: FollowupRequest) -> FollowupResponse:
    """Answer a follow-up question with new drawing steps (optionally about a selected area)."""
    pr = _perceived(req.image_id)
    lesson = None
    if req.lesson_id:
        try:
            lesson = lessons.get(req.lesson_id)
        except KeyError:  # still streaming or lost on restart: answer without the lesson context
            log.info("follow-up for unknown lesson %s; answering without lesson context", req.lesson_id)
        if lesson is not None and lesson.image_id != pr.perception.image_id:
            raise HTTPException(400, "lesson_id belongs to a different image")
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "question is empty")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(400, f"question is longer than {MAX_QUESTION_CHARS} characters")
    selection = _clean_selection(req.selection)
    model = _model(req.model)
    try:
        return tutor.answer_followup(pr, question, lesson=lesson, selection=selection, model=model)
    except HTTPException:
        raise
    except Exception as exc:
        raise _tutor_error("Follow-up failed", exc) from exc


# ---------------------------------------------------------------- voice


@app.post("/api/tts", response_model=TTSResponse)
def text_to_speech(req: TTSRequest) -> TTSResponse:
    """Narration audio + word timings (ElevenLabs, disk-cached)."""
    if not req.text.strip():
        raise HTTPException(400, "text is empty")
    if len(req.text) > MAX_TTS_CHARS:
        raise HTTPException(400, f"text is longer than {MAX_TTS_CHARS} characters")
    try:
        return eleven.synthesize(req.text, req.voice_id or None)
    except eleven.TTSNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except eleven.TTSError as exc:
        raise HTTPException(502, _scrub(f"Text-to-speech failed: {exc}")[:300]) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/audio/{name}")
def audio(name: str) -> FileResponse:
    path = eleven.audio_path(name)
    if path is None or not path.is_file():
        raise HTTPException(404, "Unknown audio file")
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})


# ---------------------------------------------------------------- helpers


def _ingest(data: bytes) -> PerceptionResult:
    """Validate, prepare and perceive image bytes (identical bytes reuse the earlier result)."""
    if not data:
        raise HTTPException(400, "Empty file")
    if _sniff(data) is None:
        raise HTTPException(400, "Not a PNG, JPEG or WebP image")
    digest = hashlib.sha256(data).hexdigest()
    known = images.find_digest(digest)
    if known is not None:
        return known
    t0 = time.perf_counter()
    try:
        image = perception.prepare_image(data)
    except ImportError as exc:
        raise HTTPException(500, _describe("Perception module unavailable", exc)) from exc
    except Exception as exc:
        raise HTTPException(400, _describe("Could not read the image", exc)) from exc
    prepare_s = round(time.perf_counter() - t0, 3)
    try:
        pr = images.create(image, digest=digest, timings={"prepare": prepare_s})
    except Exception as exc:
        log.exception("perception failed")
        raise HTTPException(500, _describe("Perception failed", exc)) from exc
    log.info(
        "image %s: %dx%d, %d regions, %.1fs",
        pr.perception.image_id, pr.width, pr.height, len(pr.perception.regions), time.perf_counter() - t0,
    )
    return pr


def _sniff(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _perceived(image_id: str) -> PerceptionResult:
    if not valid_id(image_id):
        raise HTTPException(404, "Unknown image_id")
    try:
        return images.get(image_id)
    except KeyError:
        raise HTTPException(404, "Unknown image_id") from None
    except Exception as exc:
        log.exception("re-perception of %s failed", image_id)
        raise HTTPException(500, _describe("Perception failed", exc)) from exc


def _image_file(image_id: str, name: str, cache: str) -> FileResponse:
    if not valid_id(image_id):
        raise HTTPException(404, "Unknown image_id")
    path = images.file(image_id, name)
    if not path.is_file():
        raise HTTPException(404, "Unknown image_id")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": cache})


def _samples_root() -> Path:
    return Path(config.SAMPLES_DIR).resolve()


def _sample_path(name: str) -> Path:
    """Resolve a sample name, refusing anything outside SAMPLES_DIR or not an image."""
    root = _samples_root()
    try:
        path = (root / name).resolve()
    except (OSError, ValueError):
        raise HTTPException(404, "Unknown sample") from None
    if not path.is_relative_to(root) or path == root or path.suffix.lower() not in IMAGE_EXTS or not path.is_file():
        raise HTTPException(404, "Unknown sample")
    return path


def _model(model: str | None) -> str | None:
    if model is None or not model.strip():
        return None
    if not _MODEL_RE.match(model.strip()):
        raise HTTPException(400, "Invalid model name")
    return model.strip()


def _clean_selection(box: Box | None) -> Box | None:
    """Normalize a dragged rectangle: positive size, at least MIN_SELECTION, clipped to the image."""
    if box is None:
        return None
    if not all(math.isfinite(v) for v in (box.x, box.y, box.w, box.h)):
        raise HTTPException(400, "selection must be finite numbers")
    x0, x1 = sorted((box.x, box.x + box.w))
    y0, y1 = sorted((box.y, box.y + box.h))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half_w, half_h = max(x1 - x0, MIN_SELECTION) / 2, max(y1 - y0, MIN_SELECTION) / 2
    x0, x1 = max(0.0, cx - half_w), min(1.0, cx + half_w)
    y0, y1 = max(0.0, cy - half_h), min(1.0, cy + half_h)
    if x1 - x0 <= 1e-4 or y1 - y0 <= 1e-4:
        return None
    return Box(x=x0, y=y0, w=x1 - x0, h=y1 - y0)


def _tutor_error(prefix: str, exc: Exception) -> HTTPException:
    """OpenAI failures (anywhere in the cause chain) and unusable model output -> 502, bugs -> 500."""
    upstream = _upstream_cause(exc)
    if upstream is not None:
        log.warning("%s: %s", prefix, _describe("upstream", upstream))
        return HTTPException(502, _describe(prefix, upstream))
    if isinstance(exc, ValueError):  # includes JSON decoding and pydantic validation of model output
        log.warning("%s: %s", prefix, _describe("invalid model output", exc))
        return HTTPException(502, _describe(f"{prefix} (unusable model answer)", exc))
    log.exception(prefix)
    return HTTPException(500, _describe(prefix, exc))


def _upstream_cause(exc: BaseException) -> BaseException | None:
    """The OpenAI/HTTP error behind `exc` (preferred), else a tutor wrapper such as LLMError."""
    wrapper: BaseException | None = None
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (openai.OpenAIError, httpx.HTTPError, TimeoutError)):
            return current
        if type(current).__module__.startswith(_UPSTREAM_MODULES):
            return current
        name = type(current).__name__
        if wrapper is None and ("LLM" in name or "OpenAI" in name):
            wrapper = current
        current = current.__cause__ or current.__context__
    return wrapper


def _describe(prefix: str, exc: BaseException) -> str:
    if isinstance(exc, openai.APIStatusError):
        text = f"{prefix}: OpenAI returned HTTP {exc.status_code}"
    elif isinstance(exc, openai.APITimeoutError):
        text = f"{prefix}: OpenAI request timed out"
    elif isinstance(exc, openai.APIConnectionError):
        text = f"{prefix}: could not reach OpenAI"
    else:
        lines = str(exc).strip().splitlines()
        text = f"{prefix}: {type(exc).__name__}" + (f": {lines[0]}" if lines else "")
    return _scrub(text)[:300]


def _scrub(text: str) -> str:
    for key in (config.OPENAI_API_KEY, config.ELEVENLABS_API_KEY):
        if key:
            text = text.replace(key, "***")
    return _KEYLIKE_RE.sub("***", text)


def _warmup() -> None:
    """Load the OCR models in the background so the first upload is not slower than the rest."""
    from PIL import Image, ImageDraw

    try:
        image = Image.new("RGB", (480, 160), "white")
        draw = ImageDraw.Draw(image)
        draw.text((20, 60), "Warm up the OCR models", fill="black")
        draw.rectangle((300, 40, 440, 120), outline="black", width=3)
        t0 = time.perf_counter()
        perception.perceive(image, "warmup")
        log.info("perception warm-up done in %.1fs", time.perf_counter() - t0)
    except Exception as exc:  # warm-up is best effort
        log.warning("perception warm-up skipped: %s", _describe("warmup", exc))


if os.getenv("SERVE_FRONTEND", "1") == "1" and (FRONTEND_DIST / "index.html").is_file():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
