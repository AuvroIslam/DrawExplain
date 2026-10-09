"""PDF reader mode: browse pages without scanning, scan on demand, lessons get the earlier pages as context."""
from __future__ import annotations

import io
import uuid

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import config, main, tutor
from app.documents import DocumentStore
from app.schemas import Lesson
from app.store import ImageStore, LessonStore

PAGES = ["Intro to Graphs", "Edges have weights 5 and 7", "Dijkstra picks the cheapest vertex"]


def make_pdf() -> bytes:
    doc = pymupdf.open()
    for i, text in enumerate(PAGES):
        page = doc.new_page(width=720, height=405)
        page.insert_text((60, 80), text, fontsize=28)
        page.draw_rect(pymupdf.Rect(80 + 120 * i, 160, 260 + 120 * i, 260), color=(0, 0, 0), width=3)
    doc.set_metadata({"title": "Graph Lecture"})
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYLENS_WARMUP", "0")
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "images", ImageStore(data_dir / "images"))
    monkeypatch.setattr(main, "lessons", LessonStore(data_dir / "lessons"))
    monkeypatch.setattr(main, "documents", DocumentStore(data_dir / "docs"))
    contexts: list = []

    def fake_plan(pr, model=None, context=None):
        contexts.append(context)
        return Lesson(lesson_id=uuid.uuid4().hex[:12], image_id=pr.perception.image_id,
                      title=f"Lesson {len(contexts)}", summary=f"Summary {len(contexts)}", steps=[],
                      model="test", question=context.question if context else None,
                      context_pages=context.context_pages if context else [])

    monkeypatch.setattr(tutor, "plan_lesson", fake_plan)
    c = TestClient(main.app)
    c.contexts = contexts  # type: ignore[attr-defined]
    return c


def upload(client: TestClient) -> dict:
    res = client.post("/api/documents", files={"file": ("lecture.pdf", make_pdf(), "application/pdf")})
    assert res.status_code == 200, res.text
    return res.json()


def test_upload_and_browse_without_scanning(client):
    doc = upload(client)
    assert doc["pages"] == 3 and doc["title"] == "Graph Lecture" and len(doc["page_sizes"]) == 3
    for page in (1, 2, 3, 2):
        res = client.get(doc["page_url"].replace("{page}", str(page)))
        assert res.status_code == 200 and res.headers["content-type"] == "image/png"
        assert list(Image.open(io.BytesIO(res.content)).size) == doc["page_sizes"][page - 1]
    assert main.documents.image_for(doc["doc_id"], 2) is None  # browsing scanned nothing
    assert client.get(f"/api/documents/{doc['doc_id']}/pages/9.png").status_code == 404
    assert client.get("/api/documents/nope/pages/1.png").status_code == 404


def test_scan_on_demand_is_idempotent(client):
    doc = upload(client)
    first = client.post(f"/api/documents/{doc['doc_id']}/pages/2/perceive").json()
    assert first["doc_id"] == doc["doc_id"] and first["page"] == 2
    assert [first["width"], first["height"]] == doc["page_sizes"][1]
    again = client.post(f"/api/documents/{doc['doc_id']}/pages/2/perceive").json()
    assert again["image_id"] == first["image_id"]


def test_lessons_build_on_earlier_pages_and_answer_the_question(client):
    doc = upload(client)
    p2 = client.post(f"/api/documents/{doc['doc_id']}/pages/2/perceive").json()
    assert client.post("/api/lessons", json={"image_id": p2["image_id"]}).status_code == 200
    ctx2 = client.contexts[-1]
    assert ctx2.page == 2 and ctx2.question is None
    assert [n.page for n in ctx2.previous] == [1] and "Intro to Graphs" in ctx2.previous[0].text

    p3 = client.post(f"/api/documents/{doc['doc_id']}/pages/3/perceive").json()
    res = client.post("/api/lessons", json={"image_id": p3["image_id"], "question": "  Why the cheapest?  "})
    assert res.status_code == 200
    ctx3 = client.contexts[-1]
    assert ctx3.question == "Why the cheapest?"
    assert [n.page for n in ctx3.previous] == [1, 2]
    assert [t.page for t in ctx3.taught] == [2] and ctx3.taught[0].title == "Lesson 1"
    assert res.json()["question"] == "Why the cheapest?" and res.json()["context_pages"] == [1, 2]


def test_question_works_for_plain_images_and_is_bounded(client):
    png = io.BytesIO()
    Image.new("RGB", (900, 600), "white").save(png, format="PNG")
    img = client.post("/api/images", files={"file": ("a.png", png.getvalue(), "image/png")}).json()
    client.post("/api/lessons", json={"image_id": img["image_id"], "question": "What is this?"})
    ctx = client.contexts[-1]
    assert ctx.question == "What is this?" and ctx.page is None
    too_long = client.post("/api/lessons", json={"image_id": img["image_id"], "question": "x" * 501})
    assert too_long.status_code == 400


def test_rejects_non_pdf(client):
    res = client.post("/api/documents", files={"file": ("a.png", b"\x89PNG....", "image/png")})
    assert res.status_code == 400
