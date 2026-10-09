# StudyLens Live Whiteboard: build contract

This is the single source of truth that every part of the build codes against.
The data contract itself is code: `backend/app/schemas.py` (Python, pydantic) and its mirror
`frontend/src/types.ts` (TypeScript). If you must change the contract, change both and say so
in your final report.

## Product in one paragraph

A student uploads any study image (lecture slide, textbook photo, diagram). An AI tutor teaches it
like a teacher at a whiteboard: it circles components, draws arrows, underlines terms and writes
labels **on top of the untouched original image** (separate SVG layer), one step at a time, while
narrating (ElevenLabs voice with word timestamps; each drawing appears when its cue phrase is
spoken). The student can ask follow-up questions (optionally dragging a rectangle to say "this
part") and the tutor draws again. A tap-on-the-image quiz ends the lesson. Hackathon: Banana Hacks
2026 (image-AI theme; judges penalise thin API wrappers), so the engineering story is the
**grounding pipeline**: CV perception (OCR + OpenCV) finds real regions first, the LLM plans the
lesson by choosing region ids *and* giving its own box estimate, and a fusion step cross-checks the
two before anything is drawn.

## Pipeline

```
upload -> prepare_image (EXIF, RGB on white, max side 1600)
       -> perceive: OCR lines (RapidOCR) + OpenCV shapes/figures + text blocks
                    -> regions R1..Rn (reading order) + ink mask + free-space map
                    -> Set-of-Mark image (numbered outlines)
       -> plan_lesson: LLM gets original + marked image + compact region list
                    -> strict JSON: steps, narration, annotations (target ids + own box estimate + cue)
       -> grounding fusion (per target): consensus / cv_snap / id_only / llm_refined / llm_only
       -> geometry: ellipse/rect padding, arrow endpoints on box edges with curvature,
                    span boxes for underlining a word, label placement in free space
       -> validator: ids exist, boxes in bounds, cues are substrings, sane counts
       -> Lesson JSON -> frontend animates it (rough.js strokes) synced to TTS word timings
```

## Repo layout and ownership

```
.env                      OPENAI_API_KEY, ELEVENLABS_API_KEY (never print, never commit)
CONTRACT.md               this file
samples/                  test images; *.json next to an image = ground truth (see below)
  quick/network_basic.png + .json   first hand-made sample (1280x720)
backend/
  requirements.txt        pinned deps (append a line if you add a package)
  pytest.ini              pythonpath=. ; marker `live` for paid-API tests
  app/config.py           settings (OPENAI_MODEL default gpt-5.4-mini, paths)        [contract]
  app/schemas.py          pydantic data contract                                     [contract]
  app/perception/types.py PerceptionResult, FreeSpaceMap protocol                    [contract]
  app/perception/__init__.py  prepare_image / perceive lazy exports                  [contract]
  app/perception/*.py     preprocess, ocr, regions, freespace, textspan, som, pipeline  [perception]
  app/tutor/__init__.py   plan_lesson / answer_followup / locate_targets lazy exports [contract]
  app/tutor/*.py          llm, prompts, planner, grounding, geometry, validator       [tutor]
  app/tts/*.py            ElevenLabs with timestamps + disk cache                     [server]
  app/render/preview.py   PIL renderer of lesson annotations                          [server]
  app/store.py, app/main.py   FastAPI app + storage                                   [server]
  scripts/perceive_debug.py   image -> marked PNG + regions JSON                       [perception]
  scripts/run_pipeline.py     image -> perception + lesson + preview PNGs              [server]
  scripts/make_samples.py     synthetic slides + ground truth (+ photo/dense variants) [eval]
  scripts/eval_grounding.py   raw-LLM boxes vs fused pipeline, IoU metrics             [eval]
  tests/test_<area>.py        each area owns its own test file
  data/                   runtime storage (gitignored)
frontend/                 Vite 8 + React 19 + TS 6 + Excalidraw 0.18.1 (whiteboard)
  src/types.ts            TypeScript mirror of schemas.py                            [contract]
  src/board/types.ts      BoardHandle interface between board engine and app         [contract]
  src/board/**            Excalidraw whiteboard engine (pen animation, overlays)     [board]
  everything else         app shell, API client, player, voice, follow-up, quiz      [app]
```

## Commands (Windows; Git Bash paths shown)

- Python: `/d/BananaHack/backend/.venv/Scripts/python.exe` (always use the venv; run from `backend/`)
- Tests: `cd /d/BananaHack/backend && .venv/Scripts/python -m pytest -q` (live tests: `RUN_LIVE=1`)
- API: `cd /d/BananaHack/backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000`
- Frontend: `cd /d/BananaHack/frontend && npm run dev` (Vite proxies `/api` -> `http://127.0.0.1:8000`), `npm run build`
- Scripts are run as `.venv/Scripts/python scripts/<name>.py ...` from `backend/` (they put `backend/` on `sys.path`).

## Coordinates

All API geometry is normalized `{x, y, w, h}` / `{x, y}` relative to the **processed** image
(`Perception.width x height`, same aspect ratio as the upload). Origin top-left. Region ids are
`R1..Rn` in reading order (top-to-bottom, then left-to-right) so they are stable for one image.
Ground-truth JSON files in `samples/` use **pixel** boxes `[x0, y0, x1, y1]` of that image file.

## HTTP API (FastAPI, prefix `/api`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | | `{ok, model, tts}` |
| POST | `/api/images` | multipart `file` (png/jpg/webp or PDF, <= 15 MB) + optional form `page` (PDF, 1-based) | `Perception` (with `image_url`, `marked_url`; `source_pages` for PDFs) |
| GET | `/api/images/{image_id}/original.png` | | processed image |
| GET | `/api/images/{image_id}/marked.png` | | Set-of-Mark debug image |
| GET | `/api/samples` | | `SampleInfo[]` (images under `samples/`) |
| GET | `/api/samples/file/{name:path}` | | the sample image |
| POST | `/api/samples/load` | `LoadSampleRequest {name}` | `Perception` (as if uploaded) |
| POST | `/api/documents` | multipart `file` (PDF, <= 15 MB) | `DocumentInfo` (no page is scanned) |
| GET | `/api/documents/{doc_id}` | | `DocumentInfo` |
| GET | `/api/documents/{doc_id}/pages/{page}.png` | | rendered page image (cached; same pixels the scan uses) |
| POST | `/api/documents/{doc_id}/pages/{page}/perceive` | | `Perception` with `doc_id`, `page` (re-asking returns the same scan) |
| POST | `/api/lessons` | `LessonRequest {image_id, model?, question?}` | `Lesson` (`question`, `context_pages` for document pages) |
| POST | `/api/lessons/stream` | `LessonRequest` | NDJSON events: `meta`, `header`, `step` (one per step, grounded), `lesson` (full), or `error` |
| POST | `/api/followups` | `FollowupRequest {image_id, lesson_id?, question, selection?, model?}` | `FollowupResponse` |
| POST | `/api/tts` | `TTSRequest {text, voice_id?}` | `TTSResponse {audio_url, duration, words[]}` |
| GET | `/api/audio/{name}` | | cached mp3 |

Errors: JSON `{"detail": "..."}` with 400 (bad input), 404 (unknown id), 502 (OpenAI/ElevenLabs failed).
An unknown `image_id` whose files are still on disk is re-perceived lazily (survives server restarts).

## Python module interfaces

```python
# perception (owner: perception)
from app.perception import prepare_image, perceive
img = prepare_image(raw_bytes)               # PIL RGB, max side MAX_IMAGE_SIDE
pr = perceive(img, image_id)                 # PerceptionResult (app/perception/types.py)
pr.region("R7"); pr.span_box("R7", "router"); pr.freespace.place_near(box, w, h, avoid)
pr.freespace.ink_fraction(box)

# tutor (owner: tutor)
from app.tutor import plan_lesson, answer_followup, locate_targets
lesson = plan_lesson(pr, model=None)                                   # schemas.Lesson
fu = answer_followup(pr, "why?", lesson=lesson, selection=None)        # schemas.FollowupResponse
targets = locate_targets(pr, ["the router", "the switch"])            # list[schemas.LocatedTarget]

# tts (owner: server)
from app.tts.eleven import synthesize         # synthesize(text, voice_id=None) -> TTSResponse-like result + mp3 on disk

# preview (owner: server)
from app.render.preview import render_lesson  # render_lesson(pr.image, steps, upto=None) -> PIL.Image
```

## Grounding fusion (tutor/grounding.py)

For every target reference the LLM returns `ids` (0..n region ids) and `approx` (its own normalized
box). Let `cv` = union box of the valid ids.
1. ids valid and IoU(cv, approx) >= 0.3, or approx centre inside cv (expanded 10%) -> **consensus**,
   use `cv` (pixel-tight), confidence ~0.9+.
2. ids valid but disagree -> look for a region whose box matches approx (IoU >= 0.5); if found ->
   **cv_snap**. Else, if the id's text matches the target description -> **id_only**. Else tighten
   approx to the ink inside it (expanded 15%) -> **llm_refined**.
3. no valid ids -> best region by IoU with approx (>= 0.4) -> **cv_snap**; else **llm_refined**; else
   raw approx -> **llm_only**. Drop the annotation if nothing usable remains (warn).

## LLM call shape (verified working with openai==3.26.1 on this key)

```python
from openai import OpenAI
client = OpenAI()  # key from .env via app.config
resp = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "..."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,...", "detail": "high"}},
    ]}],
    response_format={"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": SCHEMA}},
    reasoning_effort="low",   # gpt-5*/o*: if the API rejects it, retry without it
)
data = json.loads(resp.choices[0].message.content)
```
Strict schemas: every object needs `additionalProperties: false` and every property listed in
`required` (use `["string", "null"]` for optional). Do not send `temperature` to gpt-5* models.

Probe on `samples/quick/network_basic.png` (raw boxes, no CV): gpt-4.1 0.48 mean IoU 4.1 s;
gpt-4.1-mini 0.34 2.2 s; gpt-5-mini 0.35 4.8 s; **gpt-5.4-mini 0.95 2.2 s**; gpt-5.4 0.97 3.8 s;
gpt-5.5 0.99 4.1 s. So new models are good on clean slides; the pipeline must prove its value on
harder images (phone photos, dense diagrams, small labels), on pixel-tightness, label placement,
word-level spans and on letting cheap models work. Report honest numbers.

## ElevenLabs (paid "creator" key, 131k credits)

`POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128`
header `xi-api-key`, body `{"text": ..., "model_id": "eleven_flash_v2_5"}` -> `{audio_base64,
alignment: {characters, character_start_times_seconds, character_end_times_seconds}, ...}`.
Default voice `Xb7hH8MSUJpSbSDYk0k2` ("Alice - Clear, Engaging Educator"). Cache by
sha256(voice|model|text) under `backend/data/tts/` so the same narration never costs twice.

## Visual language (frontend + preview renderer)

Marker palette: red `#e03131`, blue `#1971c2`, green `#2f9e44`, orange `#f08c00`, purple `#9c36b5`
(follow-up answers default to purple; `PALETTE` in `frontend/src/types.ts`).

The whiteboard is an **Excalidraw** canvas (`@excalidraw/excalidraw` 0.18.1, MIT, credited in the
README). The processed image is a locked image element at scene (0,0) with its pixel size, so scene
coordinates = normalized x (width, height). The tutor draws like a person holding a marker: circles,
boxes and underlines are `freedraw` strokes whose points grow over time (slightly imperfect, a hand-
drawn circle overshoots its start), arrows are `arrow` elements whose points grow along the Bezier,
labels are Excalifont `text` elements written character by character after their leader line,
highlights are translucent filled rectangles that sweep left to right. Every tutor element carries
`customData` (annotation id, step, kind, grounding, confidence) so steps can be dimmed, cleared and
badged. Students draw with the normal Excalidraw tools; their latest drawing's bounding box becomes
the follow-up `selection`. The PIL preview renderer (backend) only needs to be faithful, not pretty.

## Budget rules for builders

- OpenAI: iterate with `gpt-5.4-mini`; use `gpt-5.5` only for final comparisons. Keep each agent
  under ~60 paid calls. Use the disk cache (`LLM_CACHE=1`) when re-running the same inputs.
- ElevenLabs: under ~5,000 characters per agent; always go through the cache.
- Never print or log API keys.

## PDF reader mode and lesson context

Uploading a PDF to `/api/documents` stores it and extracts each page's text layer (PyMuPDF), but runs
no perception. The student browses pages as plain images; pressing "Explain this page" perceives that
page only (`/perceive`), then streams a lesson. For a document page, the lesson request is enriched on
the server with a document context: the document title, page X of N, a short outline of the previous
pages' text (the immediately previous page in more detail) and the titles + summaries of lessons
already taught for this document in this session. The planner tells the model to build on earlier
pages without re-teaching them, and, when `question` is given, to shape the lesson around answering
it. `Lesson.context_pages` lists the earlier pages that were included.
