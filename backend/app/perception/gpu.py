"""Client for the optional GPU perception service (backend/gpu/modal_app.py, deployed on Modal).

Two things run on the GPU, both only refinements of what the CPU pipeline already found:
  segment(image, boxes)  SAM 2.1 masks for box prompts -> tight mask boxes (grounding refinement)
  latex(crops)           formula OCR (Qwen2-VL-2B) -> LaTeX for text lines that look like math

Enabled only when GPU_URL and GPU_KEY are set (config.GPU_ENABLED). Never raises into the
pipeline: every failure (unset, cold container, timeout, HTTP error, bad payload) returns None and
logs one warning, and a failure pauses GPU use for a short while so a broken service costs one
timeout, not one per request. A container that is not known to be warm is woken in the background
and skipped this time (unless GPU_WAIT_COLD=1), so a cold start never stalls a student's request.
"""
from __future__ import annotations

import base64
import io
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Sequence

import numpy as np
from PIL import Image

from app import config

log = logging.getLogger("app.perception.gpu")

HEADER = "X-DrawExplain-Key"
WARM_SECONDS = 240.0  # the Modal container scales down after 300 idle seconds
PAUSE_AFTER_FAILURE = 45.0
WARMUP_SECONDS = 150.0  # how long a background warm-up waits for a cold container
MAX_FORMULAS = 12
LATEX_TAG = " [LaTeX: "
PROMPT_TEXT_CHARS = 60  # the planner's region list shows at most this many characters per region

_lock = threading.Lock()
_client: Any = None
_paused_until = 0.0
_ready_at: dict[str, float] = {}  # capability ("segment" / "latex") -> last time it was known to work
_warming: threading.Thread | None = None
stats: dict[str, float] = {"calls": 0, "failures": 0, "seconds": 0.0}


# ---------------------------------------------------------------- state

def enabled() -> bool:
    """Configured, and not paused after a recent failure."""
    return bool(config.GPU_ENABLED) and time.monotonic() >= _paused_until


def sam_enabled() -> bool:
    return enabled() and bool(config.GPU_SAM)


def latex_enabled() -> bool:
    return enabled() and bool(config.GPU_LATEX)


def is_warm(capability: str) -> bool:
    t = _ready_at.get(capability)
    return t is not None and time.monotonic() - t < WARM_SECONDS


def ready(capability: str) -> bool:
    """True when a call is worth making now: warm, or the caller is allowed to wait for a cold start.
    Otherwise the container is woken in the background and the caller skips the GPU this time."""
    if is_warm(capability) or config.GPU_WAIT_COLD:
        return True
    warmup()
    return False


def reset() -> None:
    """Forget warm/paused state (tests)."""
    global _paused_until, _warming
    _paused_until = 0.0
    _ready_at.clear()
    _warming = None


def _pause(reason: str) -> None:
    global _paused_until
    _paused_until = time.monotonic() + PAUSE_AFTER_FAILURE
    _ready_at.clear()
    stats["failures"] += 1
    log.warning("GPU service unavailable (%s); continuing without it for %.0fs", reason, PAUSE_AFTER_FAILURE)


def _get_client() -> Any:
    global _client
    with _lock:
        if _client is None:
            import httpx

            _client = httpx.Client(timeout=config.GPU_TIMEOUT, follow_redirects=False)
        return _client


def _request(method: str, path: str, payload: dict | None = None, timeout: float | None = None,
             pause_on_failure: bool = True) -> dict | None:
    if not enabled():
        return None
    t0 = time.perf_counter()
    try:
        client = _get_client()
        kwargs: dict[str, Any] = {"headers": {HEADER: config.GPU_KEY},
                                  "timeout": timeout if timeout is not None else config.GPU_TIMEOUT}
        if payload is not None:
            kwargs["json"] = payload
        resp = client.request(method, config.GPU_URL + path, **kwargs)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")  # never echo headers or the body
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("response is not a JSON object")
    except Exception as e:  # noqa: BLE001 - the GPU is optional; any failure means "not this time"
        if pause_on_failure:
            _pause(f"{path}: {type(e).__name__}{': ' + str(e) if isinstance(e, RuntimeError) else ''}")
        else:
            stats["failures"] += 1
            log.info("GPU %s failed: %s", path, type(e).__name__)
        return None
    finally:
        stats["calls"] += 1
        stats["seconds"] += time.perf_counter() - t0
    return data


# ---------------------------------------------------------------- endpoints

def health(timeout: float | None = None) -> dict | None:
    data = _request("GET", "/health", timeout=timeout, pause_on_failure=False)
    if data is not None:
        models = data.get("models") or {}
        now = time.monotonic()
        if models.get("sam"):
            _ready_at["segment"] = now
        if models.get("latex"):
            _ready_at["latex"] = now
    return data


def warmup() -> None:
    """Wake the container in the background (no-op when disabled, warm, or already warming)."""
    global _warming
    if not enabled() or (is_warm("segment") and is_warm("latex")):
        return
    with _lock:
        if _warming is not None and _warming.is_alive():
            return
        _warming = threading.Thread(target=_warm, name="gpu-warmup", daemon=True)
        _warming.start()


def _warm() -> None:
    deadline = time.monotonic() + WARMUP_SECONDS
    while time.monotonic() < deadline and enabled():
        data = health(timeout=max(5.0, deadline - time.monotonic()))
        if data is None:
            return
        models = data.get("models") or {}
        if (models.get("sam") and models.get("latex")) or data.get("errors"):
            return
        time.sleep(2.0)


def wait_ready(timeout: float = 180.0) -> bool:
    """Block until both models are loaded (scripts and the evaluation; the API never waits)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and enabled():
        data = health(timeout=max(5.0, deadline - time.monotonic()))
        if data is not None and all((data.get("models") or {}).get(k) for k in ("sam", "latex")):
            return True
        time.sleep(2.0)
    return False


def encode_image(img: Image.Image, fmt: str = "PNG", quality: int = 90) -> str:
    buf = io.BytesIO()
    im = img if img.mode in ("RGB", "L") else img.convert("RGB")
    if fmt.upper() == "JPEG":
        im.convert("RGB").save(buf, format="JPEG", quality=quality)
    else:
        im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def segment(image: Image.Image, boxes_px: Sequence[Sequence[float]], timeout: float | None = None
            ) -> list[dict | None] | None:
    """SAM 2.1 mask per pixel box [x0, y0, x1, y1] of `image`: {box, score, area, polygon} (pixels) or None
    per box; None for the whole call when the service is off or failed."""
    if not boxes_px or not sam_enabled():
        return None
    payload = {"image": encode_image(image, "JPEG", 90),
               "boxes": [[round(float(v), 1) for v in b] for b in boxes_px]}
    data = _request("POST", "/segment", payload, timeout)
    results = data.get("results") if data is not None else None
    if not isinstance(results, list) or len(results) != len(boxes_px):
        if data is not None:
            log.warning("GPU /segment returned a malformed payload; ignored")
        return None
    _ready_at["segment"] = time.monotonic()
    out: list[dict | None] = []
    for r in results:
        ok = (isinstance(r, dict) and isinstance(r.get("box"), list) and len(r["box"]) == 4
              and all(isinstance(v, (int, float)) for v in r["box"]))
        out.append(r if ok else None)
    return out


def latex(crops: Sequence[Image.Image], timeout: float | None = None) -> list[str | None] | None:
    """LaTeX for each formula crop (None per crop it could not read); None when off or failed."""
    if not crops or not latex_enabled():
        return None
    data = _request("POST", "/latex", {"crops": [encode_image(c) for c in crops]}, timeout)
    res = data.get("latex") if data is not None else None
    if not isinstance(res, list) or len(res) != len(crops):
        if data is not None:
            log.warning("GPU /latex returned a malformed payload; ignored")
        return None
    _ready_at["latex"] = time.monotonic()
    return [str(x).strip() if isinstance(x, str) and x.strip() else None for x in res]


# ---------------------------------------------------------------- formula OCR (perception hook)

_MATH = set("=^_√∫∑Σ∏±×÷≤≥≠≈∞²³½¼¾∂∇πθαβγδΔλμσωΩφψ")
_OPS = set("+-/*()=<>")


def looks_like_formula(text: str | None, score: float = 1.0) -> bool:
    """A short OCR line that is mostly symbols and one-letter variables ("S = ut + 12at2"), not prose
    with an equals sign in it ("Units: newtons (N) = kg m/s2", "cwnd = cwnd + MSS")."""
    t = " ".join((text or "").split())
    if not 3 <= len(t) <= 48:
        return False
    alnum = sum(ch.isalnum() for ch in t)
    if alnum == 0:
        return False
    prose = sum(len(w) for w in re.findall(r"[A-Za-z]{4,}", t))
    if prose > 0.5 * alnum:
        return False
    if any(ch in _MATH for ch in t):
        return True
    return score < 0.85 and sum(ch in _OPS for ch in t) >= 2  # garbled maths: low score, operators


def strip_latex(text: str | None) -> str:
    """The OCR part of a region text that formula OCR extended with " [LaTeX: ...]"."""
    t = text or ""
    i = t.find(LATEX_TAG.strip())
    return t[:i].rstrip() if i >= 0 else t


def _alnum(s: str) -> str:
    return "".join(ch for ch in re.sub(r"\\[A-Za-z]+", " ", s).lower() if ch.isalnum())


def _compact(s: str) -> str:
    s = re.sub(r"\\(mathrm|mathit|text|operatorname)\b", "", s)
    return re.sub(r"[\s{}]|\\[,;:! ]", "", s)


def latex_text(ocr: str, tex: str | None) -> str | None:
    """Region text carrying the LaTeX, or None when the LaTeX adds nothing (same as the OCR text) or
    disagrees with it (a misread: the two must share most letters and digits)."""
    if not tex:
        return None
    tex = " ".join(tex.split())
    a, b = _alnum(ocr), _alnum(tex)
    if not b or SequenceMatcher(None, a, b).ratio() < 0.5:
        return None
    if _compact(ocr) == _compact(tex):
        return None
    text = f"{ocr}{LATEX_TAG}{tex}]"
    return text if len(text) <= PROMPT_TEXT_CHARS else f"[LaTeX: {tex}]"


@dataclass
class FormulaJob:
    """Formula OCR started in the background while the CPU pipeline keeps going."""

    boxes: list[tuple[float, float, float, float]]  # pixel boxes of the formula lines
    texts: list[str]
    thread: threading.Thread | None = None
    result: list[str | None] | None = None
    seconds: float = 0.0
    crops: list[Image.Image] = field(default_factory=list)

    def _run(self) -> None:
        t0 = time.perf_counter()
        try:
            self.result = latex(self.crops)
        except Exception:  # noqa: BLE001 - latex() already never raises; belt and braces
            log.warning("formula OCR failed", exc_info=True)
            self.result = None
        self.seconds = time.perf_counter() - t0

    def apply(self, regions: list, width: int, height: int) -> int:
        """Wait for the result and append the LaTeX to the matching text regions. Returns how many."""
        if self.thread is not None:
            self.thread.join(config.GPU_TIMEOUT + 2.0)
            if self.thread.is_alive():
                return 0
        if not self.result:
            return 0
        n = 0
        texts = [r for r in regions if r.kind == "text" and r.text]
        for (x0, y0, x1, y1), tex in zip(self.boxes, self.result):
            line = (x0 / width, y0 / height, (x1 - x0) / width, (y1 - y0) / height)
            best, best_iou = None, 0.5
            for r in texts:
                iou = _iou(line, (r.box.x, r.box.y, r.box.w, r.box.h))
                if iou > best_iou:
                    best, best_iou = r, iou
            if best is None or LATEX_TAG.strip() in best.text:
                continue
            new = latex_text(best.text, tex)
            if new is not None:
                best.text = new
                n += 1
        return n


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    iw = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    ih = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def start_formula_ocr(rgb: np.ndarray, lines: Sequence[Any], invert: bool = False) -> FormulaJob | None:
    """Pick the OCR lines that look like formulas and start reading them on the GPU in the background.
    `lines` have .box (x0, y0, x1, y1 pixels), .text and .score. None when off, cold or nothing to read."""
    if not latex_enabled():
        return None
    picks = [ln for ln in lines if looks_like_formula(ln.text, float(getattr(ln, "score", 1.0)))][:MAX_FORMULAS]
    if not picks or not ready("latex"):
        return None
    H, W = rgb.shape[:2]
    job = FormulaJob(boxes=[], texts=[])
    for ln in picks:
        x0, y0, x1, y1 = (float(v) for v in ln.box)
        pad = max(4.0, 0.25 * (y1 - y0))
        cx0, cy0 = int(max(0, x0 - pad)), int(max(0, y0 - pad))
        cx1, cy1 = int(min(W, x1 + pad)), int(min(H, y1 + pad))
        if cx1 - cx0 < 4 or cy1 - cy0 < 4:
            continue
        crop = rgb[cy0:cy1, cx0:cx1]
        if invert:  # light text on a dark slide: read it as dark on light
            crop = 255 - crop
        job.crops.append(Image.fromarray(np.ascontiguousarray(crop)))
        job.boxes.append((x0, y0, x1, y1))
        job.texts.append(ln.text)
    if not job.crops:
        return None
    job.thread = threading.Thread(target=job._run, name="gpu-latex", daemon=True)
    job.thread.start()
    return job
