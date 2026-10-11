"""ElevenLabs TTS: word-timing conversion and the disk cache (httpx mocked, no network)."""
from __future__ import annotations

import base64
import json

import httpx
import pytest

from app import config
from app.tts import eleven


def _alignment(chars: str, step: float = 0.1, start: float = 0.0) -> dict:
    return {
        "characters": list(chars),
        "character_start_times_seconds": [round(start + i * step, 4) for i in range(len(chars))],
        "character_end_times_seconds": [round(start + (i + 1) * step, 4) for i in range(len(chars))],
    }


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key-not-real")
    monkeypatch.setattr(eleven, "API_BASE", "http://127.0.0.1:9")  # any accidental real call fails fast


# ---------------------------------------------------------------- word timings


def test_exact_alignment_gives_words_with_offsets() -> None:
    text = "The router, then  the switch."
    words, duration = eleven.word_timings(text, _alignment(text))
    assert [w.word for w in words] == ["The", "router,", "then", "the", "switch."]
    assert [text[w.char_start:w.char_end] for w in words] == [w.word for w in words]
    router = words[1]
    assert (router.char_start, router.char_end) == (4, 11)
    assert (router.start, router.end) == (0.4, 1.1)
    assert words[3].char_start == 18  # double space respected
    assert duration == pytest.approx(len(text) * 0.1)


def test_misaligned_characters_still_index_original_text() -> None:
    text = "  It’s the router — really."
    spoken = "It's the router - really."  # ElevenLabs stripped the indent and plain-ASCII'd the punctuation
    words, duration = eleven.word_timings(text, _alignment(spoken))
    assert [w.word for w in words] == ["It’s", "the", "router", "—", "really."]
    for w in words:
        assert text[w.char_start:w.char_end] == w.word
    router = next(w for w in words if w.word == "router")
    assert (router.start, router.end) == (0.9, 1.5)  # chars 9..14 of the spoken text
    assert duration == pytest.approx(len(spoken) * 0.1)
    starts = [w.start for w in words]
    assert starts == sorted(starts)


def test_normalized_alignment_used_when_alignment_missing() -> None:
    text = "Port 3 forwards."
    normalized = "Port three forwards."
    words, duration = eleven.word_timings(text, None, _alignment(normalized))
    assert [w.word for w in words] == ["Port", "3", "forwards."]
    port, three, fwd = words
    assert (port.start, port.end) == (0.0, 0.4)
    assert (fwd.start, fwd.end) == (1.1, 2.0)
    assert port.end <= three.start <= three.end <= fwd.start  # interpolated inside the gap
    assert duration == 2.0


def test_proportional_fallback_without_alignment() -> None:
    text = "one two three"
    words, duration = eleven.word_timings(text, None, None, fallback_duration=2.6)
    assert duration == 2.6
    assert [w.word for w in words] == ["one", "two", "three"]
    assert words[0].start == 0.0 and words[-1].end == pytest.approx(2.6)
    assert words[1].start == pytest.approx(0.8)  # char 4 of 13 -> 4/13 * 2.6
    assert all(a.end <= b.start + 1e-9 for a, b in zip(words, words[1:]))


def test_garbage_alignment_falls_back_to_proportional() -> None:
    text = "alpha beta"
    words, duration = eleven.word_timings(text, _alignment("zzzzzzzzzz", step=0.2))
    assert duration == 2.0
    assert words[0].start == 0.0 and words[1].start == pytest.approx(1.2)


# ---------------------------------------------------------------- synthesize + cache


def _mock_client(calls: list[httpx.Request], status: int = 200, payload: dict | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if status != 200:
            return httpx.Response(status, json=payload or {"detail": {"status": "invalid_api_key", "message": "bad key test-key-not-real"}})
        text = json.loads(request.content)["text"]
        return httpx.Response(200, json=payload or {
            "audio_base64": base64.b64encode(b"ID3-fake-mp3-" + text.encode()).decode(),
            "alignment": _alignment(text, step=0.05),
            "normalized_alignment": _alignment(text, step=0.05),
        })

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_synthesize_calls_once_then_uses_cache() -> None:
    calls: list[httpx.Request] = []
    client = _mock_client(calls)
    text = "Watch the router here."
    first = eleven.synthesize(text, client=client)
    assert first.cached is False and len(calls) == 1
    req = calls[0]
    assert req.method == "POST"
    assert req.url.path == f"/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}/with-timestamps"
    assert req.url.params["output_format"] == "mp3_44100_128"
    assert req.headers["xi-api-key"] == "test-key-not-real"
    assert json.loads(req.content) == {"text": text, "model_id": config.ELEVENLABS_MODEL_ID}

    sha = eleven.cache_key(text, config.ELEVENLABS_VOICE_ID, config.ELEVENLABS_MODEL_ID)
    assert first.audio_url == f"/api/audio/{sha}.mp3"
    mp3 = config.DATA_DIR / "tts" / f"{sha}.mp3"
    assert mp3.read_bytes() == b"ID3-fake-mp3-" + text.encode()
    meta = json.loads((config.DATA_DIR / "tts" / f"{sha}.json").read_text(encoding="utf-8"))
    assert meta["text"] == text and meta["alignment"]["characters"][0] == "W"
    assert eleven.audio_path(f"{sha}.mp3") == mp3
    assert [w.word for w in first.words] == ["Watch", "the", "router", "here."]
    assert first.duration == pytest.approx(len(text) * 0.05)

    second = eleven.synthesize(text, client=client)
    assert second.cached is True and len(calls) == 1
    assert second.words == first.words and second.duration == first.duration
    assert second.audio_url == first.audio_url

    other = eleven.synthesize(text, voice_id="OtherVoice123", client=client)
    assert other.cached is False and len(calls) == 2
    assert calls[1].url.path.startswith("/v1/text-to-speech/OtherVoice123/")
    assert other.audio_url != first.audio_url


def test_synthesize_http_error_is_clear_and_secret_free() -> None:
    calls: list[httpx.Request] = []
    with pytest.raises(eleven.TTSError) as info:
        eleven.synthesize("Hello there.", client=_mock_client(calls, status=401))
    assert "401" in str(info.value) and "test-key-not-real" not in str(info.value)
    assert not any((config.DATA_DIR / "tts").glob("*.mp3"))


def test_synthesize_without_audio_is_an_error() -> None:
    with pytest.raises(eleven.TTSError):
        eleven.synthesize("Hello there.", client=_mock_client([], payload={"alignment": None}))


def test_synthesize_network_error_is_tts_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(eleven.TTSError):
        eleven.synthesize("Hello there.", client=httpx.Client(transport=httpx.MockTransport(boom)))


def test_missing_key_raises_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "")
    calls: list[httpx.Request] = []
    with pytest.raises(eleven.TTSNotConfigured, match="ELEVENLABS_API_KEY"):
        eleven.synthesize("Hello there.", client=_mock_client(calls))
    assert calls == []


def test_bad_input_is_value_error() -> None:
    client = _mock_client([])
    with pytest.raises(ValueError):
        eleven.synthesize("   ", client=client)
    with pytest.raises(ValueError):
        eleven.synthesize("hi", voice_id="../../v1/user", client=client)


def test_audio_path_validation() -> None:
    assert eleven.audio_path("../secret.mp3") is None
    assert eleven.audio_path("x.mp3") is None
    assert eleven.audio_path("a" * 64 + ".mp3") is not None
