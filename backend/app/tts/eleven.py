"""ElevenLabs text-to-speech with character timestamps, cached on disk.

synthesize(text) -> TTSResponse: mp3 under DATA_DIR/tts/<sha256>.mp3 (+ <sha256>.json with the
raw alignment), word timings indexed into the ORIGINAL request text. The same voice/model/text
never costs twice.
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from app import config
from app.schemas import TTSResponse, WordTiming

log = logging.getLogger(__name__)

API_BASE = "https://api.elevenlabs.io"
OUTPUT_FORMAT = "mp3_44100_128"
MP3_BITRATE = 128_000
TIMEOUT_S = 60.0

_VOICE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_AUDIO_NAME_RE = re.compile(r"^[0-9a-f]{64}\.mp3$")
_FOLD = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


class TTSError(RuntimeError):
    """ElevenLabs could not produce audio (network, HTTP error, bad response)."""


class TTSNotConfigured(TTSError):
    """ELEVENLABS_API_KEY is missing."""


def tts_dir() -> Path:
    return config.DATA_DIR / "tts"


def cache_key(text: str, voice_id: str, model_id: str) -> str:
    return hashlib.sha256(f"{voice_id}|{model_id}|{text}".encode("utf-8")).hexdigest()


def audio_path(name: str) -> Path | None:
    """Cached mp3 for an /api/audio/<name> request, or None when the name is not a cache file name."""
    if not _AUDIO_NAME_RE.match(name or ""):
        return None
    return tts_dir() / name


def synthesize(text: str, voice_id: str | None = None, *, client: httpx.Client | None = None) -> TTSResponse:
    """Speech for `text` with per-word timings (cached by voice|model|text)."""
    if not text or not text.strip():
        raise ValueError("text is empty")
    voice = voice_id or config.ELEVENLABS_VOICE_ID
    if not _VOICE_RE.match(voice):
        raise ValueError("invalid voice_id")
    model = config.ELEVENLABS_MODEL_ID
    sha = cache_key(text, voice, model)
    mp3_path = tts_dir() / f"{sha}.mp3"
    meta_path = tts_dir() / f"{sha}.json"

    with _lock_for(sha):
        cached = _load_cached(text, sha, mp3_path, meta_path)
        if cached is not None:
            return cached
        data = _request(text, voice, model, client)
        audio_b64 = data.get("audio_base64")
        if not audio_b64:
            raise TTSError("ElevenLabs response contained no audio")
        try:
            audio = base64.b64decode(audio_b64)
        except (ValueError, TypeError) as exc:
            raise TTSError("ElevenLabs returned undecodable audio") from exc
        alignment = data.get("alignment")
        normalized = data.get("normalized_alignment")
        words, duration = word_timings(text, alignment, normalized, fallback_duration=_mp3_seconds(len(audio)))
        meta = {
            "text": text,
            "voice_id": voice,
            "model_id": model,
            "output_format": OUTPUT_FORMAT,
            "duration": duration,
            "words": [w.model_dump() for w in words],
            "alignment": alignment,
            "normalized_alignment": normalized,
        }
        _atomic_write(mp3_path, audio)
        _atomic_write(meta_path, json.dumps(meta, ensure_ascii=False).encode("utf-8"))
    return TTSResponse(audio_url=f"/api/audio/{sha}.mp3", duration=duration, words=words, cached=False)


def word_timings(
    text: str,
    alignment: dict[str, Any] | None,
    normalized_alignment: dict[str, Any] | None = None,
    fallback_duration: float | None = None,
) -> tuple[list[WordTiming], float]:
    """Character alignment -> (words, duration). Words are maximal non-whitespace runs of
    `text`; char_start/char_end index into `text` even if ElevenLabs altered the characters."""
    duration = max(_last_end(alignment), _last_end(normalized_alignment))
    if duration <= 0:
        duration = float(fallback_duration or 0.0)
    times: list[tuple[float, float] | None] | None = None
    best = 0.0
    for candidate, threshold in ((alignment, 0.8), (normalized_alignment, 0.5)):
        projected, coverage = _project(text, candidate)
        if projected is not None and coverage >= threshold and coverage > best:
            times, best = projected, coverage
            if coverage >= 0.999:
                break
    if times is None:
        times = [None] * len(text)
    filled = _fill_gaps(times, duration)

    words: list[WordTiming] = []
    last_start = 0.0
    for match in re.finditer(r"\S+", text):
        s, e = match.start(), match.end()
        start = max(filled[s][0], last_start)
        end = max(filled[e - 1][1], start)
        last_start = start
        words.append(WordTiming(word=match.group(), start=round(start, 3), end=round(end, 3), char_start=s, char_end=e))
    if words:
        duration = max(duration, words[-1].end)
    return words, round(duration, 3)


def _project(text: str, alignment: dict[str, Any] | None) -> tuple[list[tuple[float, float] | None] | None, float]:
    """Map alignment character times onto positions of `text`; returns (times, coverage of non-space chars)."""
    if not alignment:
        return None, 0.0
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    flat_chars: list[str] = []
    flat_times: list[tuple[float, float]] = []
    for ch, s, e in zip(chars, starts, ends):
        ch = str(ch)
        if not ch:
            continue
        step = (float(e) - float(s)) / len(ch)
        for k, c in enumerate(ch):
            flat_chars.append(c)
            flat_times.append((float(s) + k * step, float(s) + (k + 1) * step))
    if not flat_chars:
        return None, 0.0
    joined = "".join(flat_chars)
    times: list[tuple[float, float] | None] = [None] * len(text)
    if joined == text:
        times = list(flat_times)
    else:
        matcher = difflib.SequenceMatcher(None, _fold(text), _fold(joined), autojunk=False)
        for a, b, size in matcher.get_matching_blocks():
            for k in range(size):
                times[a + k] = flat_times[b + k]
    non_space = [i for i, c in enumerate(text) if not c.isspace()]
    if not non_space:
        return times, 0.0
    matched = sum(1 for i in non_space if times[i] is not None)
    return times, matched / len(non_space)


def _fill_gaps(times: list[tuple[float, float] | None], duration: float) -> list[tuple[float, float]]:
    """Interpolate characters without a timing between their timed neighbours."""
    n = len(times)
    out: list[tuple[float, float]] = []
    i = 0
    while i < n:
        if times[i] is not None:
            out.append(times[i])  # type: ignore[arg-type]
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        t0 = out[-1][1] if out else 0.0
        t1 = times[j][0] if j < n else max(duration, t0)  # type: ignore[index]
        t1 = max(t1, t0)
        span = j - i
        for k in range(span):
            out.append((t0 + (t1 - t0) * k / span, t0 + (t1 - t0) * (k + 1) / span))
        i = j
    return out


def _fold(s: str) -> str:
    return "".join(c.lower() if len(c.lower()) == 1 else c for c in s.translate(_FOLD))


def _last_end(alignment: dict[str, Any] | None) -> float:
    if not alignment:
        return 0.0
    ends = alignment.get("character_end_times_seconds") or []
    try:
        return max((float(e) for e in ends), default=0.0)
    except (TypeError, ValueError):
        return 0.0


def _mp3_seconds(n_bytes: int) -> float:
    return n_bytes * 8 / MP3_BITRATE


def _request(text: str, voice: str, model: str, client: httpx.Client | None) -> dict[str, Any]:
    key = config.ELEVENLABS_API_KEY
    if not key:
        raise TTSNotConfigured("Text-to-speech is not configured (ELEVENLABS_API_KEY is missing)")
    url = f"{API_BASE}/v1/text-to-speech/{voice}/with-timestamps"
    headers = {"xi-api-key": key, "Accept": "application/json"}
    body = {"text": text, "model_id": model}
    t0 = time.perf_counter()
    try:
        if client is None:
            with httpx.Client(timeout=TIMEOUT_S) as own:
                resp = own.post(url, params={"output_format": OUTPUT_FORMAT}, headers=headers, json=body)
        else:
            resp = client.post(url, params={"output_format": OUTPUT_FORMAT}, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        raise TTSError("ElevenLabs request timed out") from exc
    except httpx.HTTPError as exc:
        raise TTSError(f"ElevenLabs request failed ({type(exc).__name__})") from exc
    if resp.status_code != 200:
        raise TTSError(f"ElevenLabs HTTP {resp.status_code}: {_error_text(resp)}")
    try:
        data = resp.json()
    except ValueError as exc:
        raise TTSError("ElevenLabs returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise TTSError("ElevenLabs returned an unexpected response")
    log.info("tts: %d chars synthesized in %.2fs", len(text), time.perf_counter() - t0)
    return data


def _error_text(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if isinstance(detail, dict):
        detail = detail.get("message") or detail.get("status")
    text = str(detail or resp.reason_phrase or "error")
    key = config.ELEVENLABS_API_KEY
    if key:
        text = text.replace(key, "***")
    return text[:200]


def _load_cached(text: str, sha: str, mp3_path: Path, meta_path: Path) -> TTSResponse | None:
    if not (mp3_path.is_file() and meta_path.is_file()):
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("alignment") or meta.get("normalized_alignment"):
            words, duration = word_timings(
                text, meta.get("alignment"), meta.get("normalized_alignment"),
                fallback_duration=_mp3_seconds(mp3_path.stat().st_size),
            )
        else:
            words = [WordTiming.model_validate(w) for w in meta.get("words", [])]
            duration = float(meta.get("duration", 0.0))
    except (OSError, ValueError, TypeError) as exc:
        log.warning("tts cache entry %s unreadable (%s); re-synthesizing", sha[:12], exc)
        return None
    return TTSResponse(audio_url=f"/api/audio/{sha}.mp3", duration=duration, words=words, cached=True)


def _lock_for(sha: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(sha, threading.Lock())


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
