"""OpenAI chat wrapper: strict JSON-schema output, image parts, retries and a disk cache."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Iterator, Union

from PIL import Image

from app import config

log = logging.getLogger("app.tutor.llm")

Part = Union[str, Image.Image, dict]

CACHE_DIR: Path = config.DATA_DIR / "llm_cache"
REQUEST_TIMEOUT = 180.0
MAX_ATTEMPTS = 4

_client: Any = None
_client_lock = threading.Lock()
stats: dict[str, float] = {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}
last_meta: dict[str, Any] = {}


class LLMError(RuntimeError):
    """The model call failed for good (the API layer maps this to HTTP 502)."""


def _get_client() -> Any:
    global _client
    with _client_lock:
        if _client is None:
            if not config.OPENAI_API_KEY:
                raise LLMError("OPENAI_API_KEY is not set")
            from openai import OpenAI

            _client = OpenAI(api_key=config.OPENAI_API_KEY, max_retries=0, timeout=REQUEST_TIMEOUT)
        return _client


def is_reasoning_model(model: str) -> bool:
    m = model.lower().split("/")[-1]
    return m.startswith("gpt-5") or (len(m) > 1 and m[0] == "o" and m[1].isdigit())


# ---------------------------------------------------------------- images

def image_to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    (img if img.mode in ("RGB", "L") else img.convert("RGB")).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def image_part(img: Image.Image, detail: str = "high") -> dict:
    return {"type": "image_url", "image_url": {"url": image_to_data_url(img), "detail": detail}}


def _image_hash(img: Image.Image) -> str:
    h = hashlib.sha256(f"{img.mode}|{img.size[0]}x{img.size[1]}|".encode())
    h.update(img.tobytes())
    return h.hexdigest()


def _content(part: Part) -> dict:
    if isinstance(part, str):
        return {"type": "text", "text": part}
    if isinstance(part, Image.Image):
        return image_part(part)
    if isinstance(part, dict):
        return part
    raise TypeError(f"unsupported message part: {type(part).__name__}")


# ---------------------------------------------------------------- cache

def cache_key(model: str, system: str, parts: list[Part], schema: dict, schema_name: str, effort: str | None) -> str:
    items: list[Any] = []
    for p in parts:
        if isinstance(p, str):
            items.append(["text", p])
        elif isinstance(p, Image.Image):
            items.append(["image", _image_hash(p)])
        else:
            items.append(["raw", hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()])
    blob = json.dumps(
        {"model": model, "system": system, "parts": items, "schema": schema, "name": schema_name, "effort": effort},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_read(key: str) -> tuple[dict, dict] | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.is_file():
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
        return blob["data"], blob["meta"]
    except (OSError, ValueError, KeyError):
        return None


def _cache_write(key: str, data: dict, meta: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_DIR / f"{key}.{os.getpid()}.{threading.get_ident()}.tmp"
        tmp.write_text(json.dumps({"data": data, "meta": meta, "created": time.time()}, ensure_ascii=False),
                       encoding="utf-8")
        os.replace(tmp, CACHE_DIR / f"{key}.json")
    except OSError as e:  # the cache is an optimisation only
        log.warning("llm cache write failed: %s", e)


# ---------------------------------------------------------------- call

def _backoff(attempt: int, err: Exception | None = None) -> float:
    delay = min(20.0, 1.5 * (2 ** attempt)) + random.uniform(0, 0.5)
    response = getattr(err, "response", None)
    try:
        retry_after = float(response.headers.get("retry-after")) if response is not None else None
    except (TypeError, ValueError, AttributeError):
        retry_after = None
    if retry_after is not None and 0 < retry_after <= 30:
        delay = max(delay, retry_after)
    return delay


def _rejects_reasoning(err: Exception) -> bool:
    text = str(getattr(err, "message", "") or err).lower()
    return "reasoning" in text and ("unsupported" in text or "not supported" in text or "unrecognized" in text
                                    or "invalid" in text or "unknown" in text or "does not support" in text)


def chat_json(
    model: str | None,
    system: str,
    parts: list[Part],
    schema: dict,
    schema_name: str,
    *,
    cache: bool | None = None,
    reasoning_effort: str | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> tuple[dict, dict]:
    """One strict-JSON chat completion. Returns (data, meta) where meta has model, seconds,
    input_tokens, output_tokens, cached. Raises LLMError when the call fails for good."""
    import openai

    model = model or config.OPENAI_MODEL
    effort = (reasoning_effort or config.OPENAI_REASONING_EFFORT or None) if is_reasoning_model(model) else None
    use_cache = config.LLM_CACHE if cache is None else cache
    t0 = time.perf_counter()
    key = cache_key(model, system, parts, schema, schema_name, effort) if use_cache else None
    if key is not None:
        hit = _cache_read(key)
        if hit is not None:
            data, meta = hit
            meta = {**meta, "cached": True, "seconds": round(time.perf_counter() - t0, 3),
                    "original_seconds": meta.get("seconds")}
            stats["cache_hits"] += 1
            last_meta.clear()
            last_meta.update(meta)
            return data, meta

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [_content(p) for p in parts]},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        },
    }
    if effort:
        kwargs["reasoning_effort"] = effort

    client = _get_client()
    attempt, json_retry_used, last_err = 0, False, None
    while attempt < max_attempts:
        try:
            resp = client.chat.completions.create(**kwargs)
        except openai.BadRequestError as e:
            if "reasoning_effort" in kwargs and _rejects_reasoning(e):
                log.info("model %s rejected reasoning_effort; retrying without it", model)
                kwargs.pop("reasoning_effort")
                continue
            raise LLMError(f"OpenAI rejected the request: {getattr(e, 'message', e)}") from e
        except openai.AuthenticationError:  # its message can echo part of the key: never pass it on
            raise LLMError("OpenAI authentication failed (check OPENAI_API_KEY)") from None
        except openai.RateLimitError as e:
            if getattr(e, "code", None) == "insufficient_quota":
                raise LLMError("OpenAI quota exhausted") from e
            last_err = e
        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            last_err = e
        except openai.APIStatusError as e:
            if e.status_code < 500 and e.status_code not in (408, 409):
                raise LLMError(f"OpenAI error {e.status_code}: {getattr(e, 'message', e)}") from e
            last_err = e
        else:
            choice = resp.choices[0] if resp.choices else None
            content = choice.message.content if choice is not None else None
            try:
                if not content:
                    refusal = getattr(choice.message, "refusal", None) if choice is not None else None
                    raise ValueError(f"empty response ({refusal or getattr(choice, 'finish_reason', 'no choice')})")
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("response is not a JSON object")
            except ValueError as e:
                if json_retry_used:
                    raise LLMError(f"model returned invalid JSON twice: {e}") from e
                json_retry_used = True
                log.warning("invalid JSON from %s (%s); retrying once", model, e)
                continue
            usage = getattr(resp, "usage", None)
            details = getattr(usage, "completion_tokens_details", None)
            prompt_details = getattr(usage, "prompt_tokens_details", None)
            meta = {
                "model": model,
                "model_version": getattr(resp, "model", model),
                "seconds": round(time.perf_counter() - t0, 3),
                "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                "reasoning_tokens": int(getattr(details, "reasoning_tokens", 0) or 0),
                "cached_input_tokens": int(getattr(prompt_details, "cached_tokens", 0) or 0),
                "reasoning_effort": kwargs.get("reasoning_effort"),
                "cached": False,
            }
            stats["calls"] += 1
            stats["input_tokens"] += meta["input_tokens"]
            stats["output_tokens"] += meta["output_tokens"]
            stats["seconds"] += meta["seconds"]
            last_meta.clear()
            last_meta.update(meta)
            log.info("%s %s: %.1fs, %d in / %d out tokens", schema_name, model, meta["seconds"],
                     meta["input_tokens"], meta["output_tokens"])
            if key is not None:
                _cache_write(key, data, meta)
            return data, meta
        attempt += 1
        if attempt < max_attempts:
            delay = _backoff(attempt - 1, last_err)
            log.warning("OpenAI call failed (%s); retry %d/%d in %.1fs", type(last_err).__name__, attempt,
                        max_attempts - 1, delay)
            time.sleep(delay)
    raise LLMError(f"OpenAI call failed after {max_attempts} attempts: {type(last_err).__name__}: {last_err}")


def chat_json_stream(
    model: str | None,
    system: str,
    parts: list[Part],
    schema: dict,
    schema_name: str,
    *,
    cache: bool | None = None,
    reasoning_effort: str | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> Iterator[str]:
    """Streaming twin of chat_json: yields the JSON text as it is generated (a cache hit yields it
    whole). Retries only before the first token; afterwards a failure raises LLMError. On success the
    full response is validated, cached and described in `last_meta`."""
    import openai

    model = model or config.OPENAI_MODEL
    effort = (reasoning_effort or config.OPENAI_REASONING_EFFORT or None) if is_reasoning_model(model) else None
    use_cache = config.LLM_CACHE if cache is None else cache
    t0 = time.perf_counter()
    key = cache_key(model, system, parts, schema, schema_name, effort) if use_cache else None
    if key is not None:
        hit = _cache_read(key)
        if hit is not None:
            data, meta = hit
            last_meta.clear()
            last_meta.update({**meta, "cached": True, "original_seconds": meta.get("seconds")})
            stats["cache_hits"] += 1
            yield json.dumps(data, ensure_ascii=False)
            return
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [_content(p) for p in parts]},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if effort:
        kwargs["reasoning_effort"] = effort
    client = _get_client()
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        pieces: list[str] = []
        usage = None
        first_token: float | None = None
        try:
            for chunk in client.chat.completions.create(**kwargs):
                usage = getattr(chunk, "usage", None) or usage
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    if first_token is None:
                        first_token = time.perf_counter() - t0
                    pieces.append(delta)
                    yield delta
        except openai.BadRequestError as e:
            if not pieces and "reasoning_effort" in kwargs and _rejects_reasoning(e):
                kwargs.pop("reasoning_effort")
                continue
            raise LLMError(f"OpenAI rejected the request: {getattr(e, 'message', e)}") from e
        except openai.AuthenticationError:
            raise LLMError("OpenAI authentication failed (check OPENAI_API_KEY)") from None
        except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError,
                openai.InternalServerError) as e:
            if pieces:
                raise LLMError(f"OpenAI stream broke off: {type(e).__name__}") from e
            last_err = e
            if attempt + 1 < max_attempts:
                time.sleep(_backoff(attempt, e))
            continue
        text = "".join(pieces)
        try:
            data = json.loads(text)
        except ValueError as e:
            raise LLMError(f"model returned invalid JSON: {e}") from e
        meta = {
            "model": model,
            "seconds": round(time.perf_counter() - t0, 3),
            "first_token_seconds": round(first_token or 0.0, 3),
            "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "reasoning_effort": kwargs.get("reasoning_effort"),
            "cached": False,
        }
        stats["calls"] += 1
        stats["input_tokens"] += meta["input_tokens"]
        stats["output_tokens"] += meta["output_tokens"]
        stats["seconds"] += meta["seconds"]
        last_meta.clear()
        last_meta.update(meta)
        if key is not None:
            _cache_write(key, data, meta)
        return
    raise LLMError(f"OpenAI stream failed after {max_attempts} attempts: {type(last_err).__name__}: {last_err}")
