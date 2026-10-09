"""HTTP API tests (no network: perception, tutor and TTS are stubbed)."""
from __future__ import annotations

import io
import re
import uuid

import httpx2
import numpy as np
import openai
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import config, main, perception, tutor
from app.perception.types import PerceptionResult
from app.schemas import (
    Annotation,
    Box,
    FollowupResponse,
    Geometry,
    Lesson,
    Perception,
    Region,
    Step,
    TTSResponse,
    WordTiming,
)
from app.store import ImageStore, LessonStore
from app.tts import eleven


class FakeFreeSpace:
    def ink_fraction(self, box: Box) -> float:
        return 0.0

    def place_near(self, target: Box, w: float, h: float, avoid: list[Box] | None = None) -> Box:
        return Box(x=0.0, y=0.0, w=w, h=h)


def make_image_bytes(fmt: str = "PNG", size: tuple[int, int] = (320, 200), seed: int = 0) -> bytes:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40 + seed, 50, 140, 120), outline="navy", width=4)
    draw.text((180, 80), f"Router {seed}", fill="black")
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()


class Calls:
    def __init__(self) -> None:
        self.perceive: list[str] = []
        self.plan: list[tuple[str, str | None]] = []
        self.followup: list[dict] = []


@pytest.fixture()
def calls() -> Calls:
    return Calls()


@pytest.fixture()
def client(tmp_path, monkeypatch, calls: Calls) -> TestClient:
    monkeypatch.setenv("STUDYLENS_WARMUP", "0")
    data_dir = tmp_path / "data"
    samples = tmp_path / "samples"
    (samples / "quick").mkdir(parents=True)
    (samples / "eval").mkdir()
    (samples / "deep" / "x").mkdir(parents=True)
    (samples / "quick" / "a.png").write_bytes(make_image_bytes(seed=1))
    (samples / "b.jpg").write_bytes(make_image_bytes("JPEG", seed=2))
    (samples / "deep" / "x" / "y.webp").write_bytes(make_image_bytes("WEBP", seed=3))
    (samples / "eval" / "hidden.png").write_bytes(make_image_bytes(seed=4))
    (samples / "quick" / "a.json").write_text("{}")
    (samples / "notes.txt").write_text("not an image")
    (tmp_path / "secret.png").write_bytes(make_image_bytes(seed=5))

    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "SAMPLES_DIR", samples)
    monkeypatch.setattr(main, "images", ImageStore(data_dir / "images"))
    monkeypatch.setattr(main, "lessons", LessonStore(data_dir / "lessons"))

    def fake_prepare(data: bytes) -> Image.Image:
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            return im.convert("RGB")

    def fake_perceive(image: Image.Image, image_id: str) -> PerceptionResult:
        calls.perceive.append(image_id)
        w, h = image.size
        regions = [
            Region(id="R1", kind="shape", box=Box(x=40 / w, y=50 / h, w=100 / w, h=70 / h), source="opencv"),
            Region(id="R2", kind="text", box=Box(x=180 / w, y=78 / h, w=60 / w, h=14 / h), text="Router", source="ocr"),
        ]
        marked = image.copy()
        ImageDraw.Draw(marked).rectangle((40, 50, 140, 120), outline="red", width=2)
        return PerceptionResult(
            perception=Perception(image_id=image_id, width=w, height=h, regions=regions, timings={"ocr": 0.01}),
            image=image,
            marked=marked,
            ink=np.zeros((h, w), dtype=bool),
            freespace=FakeFreeSpace(),
        )

    def fake_plan(pr: PerceptionResult, model: str | None = None) -> Lesson:
        calls.plan.append((pr.perception.image_id, model))
        return Lesson(
            lesson_id=uuid.uuid4().hex[:12],
            image_id=pr.perception.image_id,
            title="Routers",
            summary="A router forwards packets.",
            steps=[_step(1)],
            model=model or config.OPENAI_MODEL,
        )

    def fake_followup(pr, question, lesson=None, selection=None, model=None) -> FollowupResponse:
        calls.followup.append({"question": question, "lesson": lesson, "selection": selection, "model": model})
        return FollowupResponse(title=f"Re: {question}", steps=[_step(2)], model=model or config.OPENAI_MODEL)

    monkeypatch.setattr(perception, "prepare_image", fake_prepare)
    monkeypatch.setattr(perception, "perceive", fake_perceive)
    monkeypatch.setattr(tutor, "plan_lesson", fake_plan)
    monkeypatch.setattr(tutor, "answer_followup", fake_followup)
    return TestClient(main.app)


def _step(index: int) -> Step:
    return Step(
        index=index,
        title=f"Step {index}",
        narration="This is the router.",
        annotations=[
            Annotation(
                id=f"s{index}a1",
                kind="circle",
                target_ids=["R1"],
                cue="the router",
                geometry=Geometry(box=Box(x=0.1, y=0.2, w=0.35, h=0.4)),
                confidence=0.93,
            )
        ],
    )


def _upload(client: TestClient, data: bytes, name: str = "slide.png", ctype: str = "image/png"):
    return client.post("/api/images", files={"file": (name, data, ctype)})


# ---------------------------------------------------------------- health / upload


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["model"] == config.OPENAI_MODEL
    assert body["tts"] is bool(config.ELEVENLABS_API_KEY)


def test_upload_returns_perception_and_serves_files(client: TestClient, calls: Calls) -> None:
    res = _upload(client, make_image_bytes())
    assert res.status_code == 200, res.text
    p = Perception.model_validate(res.json())
    assert re.fullmatch(r"[0-9a-f]{12}", p.image_id)
    assert (p.width, p.height) == (320, 200)
    assert [r.id for r in p.regions] == ["R1", "R2"]
    assert p.image_url == f"/api/images/{p.image_id}/original.png"
    assert p.marked_url == f"/api/images/{p.image_id}/marked.png"
    assert "prepare" in p.timings and "ocr" in p.timings

    for url in (p.image_url, p.marked_url):
        img = client.get(url)
        assert img.status_code == 200
        assert img.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(img.content)).size == (320, 200)

    folder = config.DATA_DIR / "images" / p.image_id
    assert {f.name for f in folder.iterdir()} == {"original.png", "marked.png", "perception.json"}
    stored = Perception.model_validate_json((folder / "perception.json").read_text())
    assert stored.image_url == p.image_url and len(stored.regions) == 2
    assert client.get(f"/api/images/{p.image_id}").json()["image_id"] == p.image_id
    assert calls.perceive == [p.image_id]


@pytest.mark.parametrize(("fmt", "name", "ctype"), [("JPEG", "photo.jpg", "image/jpeg"), ("WEBP", "x.webp", "image/webp")])
def test_upload_jpeg_and_webp(client: TestClient, fmt: str, name: str, ctype: str) -> None:
    res = _upload(client, make_image_bytes(fmt), name, ctype)
    assert res.status_code == 200, res.text
    assert res.json()["width"] == 320


def test_upload_accepts_octet_stream_with_image_extension(client: TestClient) -> None:
    assert _upload(client, make_image_bytes(), "blob.png", "application/octet-stream").status_code == 200


def test_upload_rejects_bad_input(client: TestClient, calls: Calls) -> None:
    assert _upload(client, b"hello", "notes.txt", "text/plain").status_code == 400
    assert _upload(client, b"GIF89a....", "fake.png", "image/png").status_code == 400
    assert _upload(client, b"", "empty.png", "image/png").status_code == 400
    corrupt = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    res = _upload(client, corrupt, "corrupt.png", "image/png")
    assert res.status_code == 400 and res.json()["detail"].startswith("Could not read the image")
    big = make_image_bytes() + b"\x00" * (15 * 1024 * 1024)
    res = _upload(client, big, "big.png", "image/png")
    assert res.status_code == 400 and "15 MB" in res.json()["detail"]
    assert calls.perceive == []


def test_identical_upload_is_perceived_once(client: TestClient, calls: Calls) -> None:
    first = _upload(client, make_image_bytes(seed=7)).json()
    second = _upload(client, make_image_bytes(seed=7)).json()
    assert first["image_id"] == second["image_id"]
    assert len(calls.perceive) == 1


def test_unknown_ids_are_404(client: TestClient) -> None:
    assert client.get("/api/images/0123456789ab/original.png").status_code == 404
    assert client.get("/api/images/0123456789ab/marked.png").status_code == 404
    assert client.get("/api/images/0123456789ab").status_code == 404
    assert client.get("/api/images/..%2F..%2Fsecret/original.png").status_code == 404
    assert client.post("/api/lessons", json={"image_id": "0123456789ab"}).status_code == 404
    assert client.post("/api/lessons", json={"image_id": "../../etc"}).status_code == 404
    assert client.get("/api/lessons/0123456789ab").status_code == 404
    res = client.post("/api/followups", json={"image_id": "nope", "question": "why?"})
    assert res.status_code == 404 and res.json() == {"detail": "Unknown image_id"}


def test_restart_reperceives_from_disk(client: TestClient, calls: Calls, monkeypatch) -> None:
    image_id = _upload(client, make_image_bytes(seed=9)).json()["image_id"]
    monkeypatch.setattr(main, "images", ImageStore(config.DATA_DIR / "images"))  # fresh process memory
    res = client.post("/api/lessons", json={"image_id": image_id})
    assert res.status_code == 200, res.text
    assert calls.perceive == [image_id, image_id]
    assert calls.plan == [(image_id, None)]
    res = client.get(f"/api/images/{image_id}")
    assert res.json()["image_url"] == f"/api/images/{image_id}/original.png"
    assert calls.perceive == [image_id, image_id]  # cached in memory again


# ---------------------------------------------------------------- samples


def test_samples_list_and_files(client: TestClient) -> None:
    res = client.get("/api/samples")
    assert res.status_code == 200
    names = [s["name"] for s in res.json()]
    assert names == ["b.jpg", "deep/x/y.webp", "quick/a.png"]
    for sample in res.json():
        assert sample["url"] == f"/api/samples/file/{sample['name']}"
        img = client.get(sample["url"])
        assert img.status_code == 200
        assert img.content == (config.SAMPLES_DIR / sample["name"]).read_bytes()


def test_samples_path_traversal_is_refused(client: TestClient) -> None:
    for bad in ("../secret.png", "..%2Fsecret.png", "%2e%2e/secret.png", "quick/../../secret.png", "notes.txt", "quick/a.json", "missing.png"):
        assert client.get(f"/api/samples/file/{bad}").status_code == 404, bad
    for bad in ("../secret.png", "..\\secret.png", "notes.txt", "", "missing.png", str(config.SAMPLES_DIR.parent / "secret.png")):
        assert client.post("/api/samples/load", json={"name": bad}).status_code == 404, bad


def test_samples_load_is_like_upload(client: TestClient, calls: Calls) -> None:
    res = client.post("/api/samples/load", json={"name": "quick/a.png"})
    assert res.status_code == 200, res.text
    p = res.json()
    assert p["image_url"] == f"/api/images/{p['image_id']}/original.png"
    assert client.get(p["marked_url"]).status_code == 200
    again = client.post("/api/samples/load", json={"name": "quick/a.png"}).json()
    assert again["image_id"] == p["image_id"] and len(calls.perceive) == 1
    assert client.post("/api/samples/load", json={"name": "eval/hidden.png"}).status_code == 200


# ---------------------------------------------------------------- lessons / follow-ups


def test_lesson_and_followup_flow(client: TestClient, calls: Calls) -> None:
    image_id = _upload(client, make_image_bytes()).json()["image_id"]
    res = client.post("/api/lessons", json={"image_id": image_id, "model": "gpt-5.4-mini"})
    assert res.status_code == 200, res.text
    lesson = Lesson.model_validate(res.json())
    assert lesson.image_id == image_id and lesson.model == "gpt-5.4-mini"
    assert (config.DATA_DIR / "lessons" / f"{lesson.lesson_id}.json").is_file()
    assert client.get(f"/api/lessons/{lesson.lesson_id}").json() == res.json()

    body = {
        "image_id": image_id,
        "lesson_id": lesson.lesson_id,
        "question": "  What does the router do?  ",
        "selection": {"x": 0.5, "y": 0.6, "w": -0.2, "h": -0.3},
    }
    res = client.post("/api/followups", json=body)
    assert res.status_code == 200, res.text
    assert FollowupResponse.model_validate(res.json()).steps[0].index == 2
    call = calls.followup[-1]
    assert call["question"] == "What does the router do?"
    assert call["lesson"].lesson_id == lesson.lesson_id
    sel = call["selection"]
    assert (round(sel.x, 6), round(sel.y, 6), round(sel.w, 6), round(sel.h, 6)) == (0.3, 0.3, 0.2, 0.3)

    res = client.post("/api/followups", json={"image_id": image_id, "question": "why?", "selection": {"x": 0.995, "y": 0.5, "w": 0, "h": 0}})
    assert res.status_code == 200
    sel = calls.followup[-1]["selection"]
    assert calls.followup[-1]["lesson"] is None
    assert sel.x + sel.w <= 1.0 and sel.w > 0 and sel.h >= 0.0199

    # an unknown lesson (still streaming, or lost on restart) is answered without lesson context
    assert client.post("/api/followups", json={"image_id": image_id, "lesson_id": "0123456789ab", "question": "x"}).status_code == 200
    assert calls.followup[-1]["lesson"] is None
    assert client.post("/api/followups", json={"image_id": image_id, "question": "   "}).status_code == 400
    assert client.post("/api/followups", json={"image_id": image_id, "question": "x" * 1001}).status_code == 400
    assert client.post("/api/lessons", json={"image_id": image_id, "model": "bad model; rm -rf"}).status_code == 400


def test_followup_rejects_lesson_of_other_image(client: TestClient) -> None:
    a = _upload(client, make_image_bytes(seed=1)).json()["image_id"]
    b = _upload(client, make_image_bytes(seed=2)).json()["image_id"]
    lesson_id = client.post("/api/lessons", json={"image_id": a}).json()["lesson_id"]
    res = client.post("/api/followups", json={"image_id": b, "lesson_id": lesson_id, "question": "why?"})
    assert res.status_code == 400


def _openai_request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


class LLMError(RuntimeError):
    pass


def test_tutor_failures_map_to_502_without_secrets(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-proj-SECRETSECRETSECRET1234")
    image_id = _upload(client, make_image_bytes()).json()["image_id"]
    leaky = "Incorrect API key provided: sk-proj-SECRETSECRETSECRET1234 and sk-proj-****1234"
    auth = openai.AuthenticationError(leaky, response=httpx2.Response(401, request=_openai_request()), body=None)

    def wrapped(*args, **kwargs):
        try:
            raise auth
        except openai.OpenAIError as exc:
            raise LLMError(f"call failed: {exc}") from exc

    cases = [
        (openai.APIConnectionError(request=_openai_request()), 502, "could not reach OpenAI"),
        (auth, 502, "OpenAI returned HTTP 401"),
        (None, 502, "OpenAI returned HTTP 401"),
        (ValueError("model returned invalid JSON"), 502, "unusable model answer"),
        (TypeError("bug in planner"), 500, "TypeError"),
    ]
    for exc, status, needle in cases:
        def fail(*args, _exc=exc, **kwargs):
            if _exc is None:
                wrapped()
            raise _exc

        monkeypatch.setattr(tutor, "plan_lesson", fail)
        monkeypatch.setattr(tutor, "answer_followup", fail)
        for path, body in (("/api/lessons", {"image_id": image_id}), ("/api/followups", {"image_id": image_id, "question": "why?"})):
            res = client.post(path, json=body)
            assert res.status_code == status, (path, exc, res.text)
            detail = res.json()["detail"]
            assert needle in detail, detail
            assert "SECRET" not in detail and "sk-proj" not in detail


# ---------------------------------------------------------------- tts / audio


def test_tts_endpoint(client: TestClient, monkeypatch) -> None:
    seen: list[tuple[str, str | None]] = []

    def fake_synth(text: str, voice_id: str | None = None) -> TTSResponse:
        seen.append((text, voice_id))
        return TTSResponse(
            audio_url="/api/audio/" + "a" * 64 + ".mp3",
            duration=0.9,
            words=[WordTiming(word="Hi", start=0.0, end=0.4, char_start=0, char_end=2)],
        )

    monkeypatch.setattr(eleven, "synthesize", fake_synth)
    res = client.post("/api/tts", json={"text": "Hi there"})
    assert res.status_code == 200, res.text
    assert TTSResponse.model_validate(res.json()).words[0].word == "Hi"
    assert seen == [("Hi there", None)]
    assert client.post("/api/tts", json={"text": "  "}).status_code == 400
    assert client.post("/api/tts", json={"text": "x" * 2501}).status_code == 400


def test_tts_failures(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "xi-SECRETKEY1234567890")

    def raising(exc: Exception):
        def synth(text: str, voice_id: str | None = None):
            raise exc
        return synth

    monkeypatch.setattr(eleven, "synthesize", raising(eleven.TTSError("ElevenLabs HTTP 401: bad key xi-SECRETKEY1234567890")))
    res = client.post("/api/tts", json={"text": "Hello"})
    assert res.status_code == 502 and "SECRET" not in res.json()["detail"]
    monkeypatch.setattr(eleven, "synthesize", raising(eleven.TTSNotConfigured("ELEVENLABS_API_KEY is missing")))
    assert client.post("/api/tts", json={"text": "Hello"}).status_code == 503
    monkeypatch.setattr(eleven, "synthesize", raising(ValueError("invalid voice_id")))
    assert client.post("/api/tts", json={"text": "Hello", "voice_id": "../x"}).status_code == 400


def test_audio_is_served_and_names_validated(client: TestClient) -> None:
    name = "ab" * 32 + ".mp3"
    (config.DATA_DIR / "tts").mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / "tts" / name).write_bytes(b"ID3fake-mp3")
    (config.DATA_DIR / "tts" / "secret.txt").write_text("no")
    res = client.get(f"/api/audio/{name}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert res.content == b"ID3fake-mp3"
    for bad in ("cd" * 32 + ".mp3", "secret.txt", "..%2Fsecret.txt", "..%2F..%2F.env", "AB" * 32 + ".mp3"):
        assert client.get(f"/api/audio/{bad}").status_code == 404, bad


def test_cors_preflight(client: TestClient) -> None:
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        res = client.options(
            "/api/lessons",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
        )
        assert res.status_code == 200
        assert res.headers["access-control-allow-origin"] == origin
    res = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in res.headers
