"""API tests: ingestion flow, reels listing/filters/pagination, stats, retry,
search (keyword + semantic), collections, knowledge bases, and chat."""
from __future__ import annotations

import shutil

from app.core.constants import ProcessingStatus
from app.models.reel import Reel
from app.workers.dispatch import run_reel_inline


def _make_completed_reel(db, *, url, caption, creator=None, category=None):
    reel = Reel(reel_url=url, normalized_url=url, shortcode=url.rstrip("/").split("/")[-1],
                caption=caption, creator_username=creator, processing_status=ProcessingStatus.DISCOVERED)
    db.add(reel)
    db.commit()
    db.refresh(reel)
    run_reel_inline(reel.id)
    db.refresh(reel)
    if category:
        reel.category = category
        reel.category_source = "manual"
        db.commit()
    return reel


# ----------------------------------------------------------------- ingestion
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_full_ingestion_flow(client, sample_export, tmp_path):
    base = tmp_path / "export"
    shutil.make_archive(str(base), "zip", root_dir=sample_export)
    with open(str(base) + ".zip", "rb") as fh:
        r = client.post(
            "/api/ingestion/upload",
            files={"file": ("export.zip", fh, "application/zip")},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    job_id = body["job_id"]
    convos = {c["thread_id"]: c for c in body["conversations"]}
    assert "my_alt_account_17b2f9" in convos
    assert convos["my_alt_account_17b2f9"]["reel_count"] >= 3

    # Import the alt-account conversation (runs inline since Celery is off).
    r = client.post("/api/ingestion/import", json={"job_id": job_id, "thread_id": "my_alt_account_17b2f9"})
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["report"]["new_reels_imported"] == 4
    assert job["duplicates_skipped"] >= 1

    # Reels now exist.
    r = client.get("/api/reels")
    assert r.status_code == 200
    assert r.json()["total"] == 4


def test_upload_rejects_bad_type(client):
    r = client.post("/api/ingestion/upload", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400


# --------------------------------------------------------- reels + filters
def test_reels_pagination_and_filters(client, db):
    _make_completed_reel(db, url="https://www.instagram.com/reel/A1/", caption="python programming tips and tricks", creator="dev_a")
    _make_completed_reel(db, url="https://www.instagram.com/reel/A2/", caption="ai agents guide for developers", creator="dev_b")
    _make_completed_reel(db, url="https://www.instagram.com/reel/A3/", caption="travel vlog paris city guide", creator="dev_a")

    r = client.get("/api/reels", params={"page": 1, "page_size": 2})
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    r = client.get("/api/reels", params={"creator": "dev_a"})
    assert r.json()["total"] == 2

    r = client.get("/api/reels", params={"status": str(ProcessingStatus.COMPLETED)})
    assert r.json()["total"] == 3


def test_reel_detail_and_manual_recategorize(client, db):
    reel = _make_completed_reel(db, url="https://www.instagram.com/reel/B1/", caption="machine learning basics explained simply")
    r = client.get(f"/api/reels/{reel.id}")
    assert r.status_code == 200
    assert "transcript" in r.json()

    r = client.patch(f"/api/reels/{reel.id}", json={"category": "Finance"})
    assert r.status_code == 200
    assert r.json()["category"] == "Finance"
    assert r.json()["category_source"] == "manual"


def test_stats_endpoint(client, db):
    _make_completed_reel(db, url="https://www.instagram.com/reel/C1/", caption="ai agents explained in great detail")
    _make_completed_reel(db, url="https://www.instagram.com/reel/C2/", caption=None)  # insufficient
    r = client.get("/api/reels/stats")
    s = r.json()
    assert s["total"] == 2
    assert s["completed"] >= 1
    assert isinstance(s["by_category"], list)


def test_retry_endpoint(client, db):
    reel = _make_completed_reel(db, url="https://www.instagram.com/reel/D1/", caption=None)
    assert reel.processing_status == str(ProcessingStatus.INSUFFICIENT_CONTENT)
    r = client.post(f"/api/reels/{reel.id}/retry")
    assert r.status_code == 200
    assert r.json()["queued"] is True


# -------------------------------------------------------------- search
def test_keyword_and_semantic_search(client, db):
    _make_completed_reel(db, url="https://www.instagram.com/reel/E1/",
                         caption="How to build autonomous AI agents with Python tools")
    _make_completed_reel(db, url="https://www.instagram.com/reel/E2/",
                         caption="Best budget travel destinations in Europe")

    r = client.get("/api/search", params={"q": "AI agents", "mode": "keyword"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.get("/api/search", params={"q": "autonomous agents python", "mode": "semantic"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1


# --------------------------------------------------------- collections + KB + chat
def test_collections_crud(client, db):
    reel = _make_completed_reel(db, url="https://www.instagram.com/reel/F1/", caption="productivity hacks for daily work")
    r = client.post("/api/collections", json={"name": "Faves", "color": "#f00"})
    assert r.status_code == 201
    cid = r.json()["id"]
    r = client.post(f"/api/collections/{cid}/reels", json={"reel_ids": [reel.id]})
    assert r.json()["reel_count"] == 1


def test_knowledge_base_and_chat(client, db):
    r1 = _make_completed_reel(db, url="https://www.instagram.com/reel/G1/",
                              caption="Deep dive into retrieval augmented generation and vector databases")
    r2 = _make_completed_reel(db, url="https://www.instagram.com/reel/G2/",
                              caption="How transformers and attention mechanisms work")

    r = client.post("/api/knowledge-bases", json={
        "name": "AI Study", "source_type": "manual", "reel_ids": [r1.id, r2.id],
    })
    assert r.status_code == 201, r.text
    kb = r.json()
    assert kb["reel_count"] == 2
    kb_id = kb["id"]

    r = client.post("/api/chat", json={"query": "how does retrieval augmented generation work?", "knowledge_base_id": kb_id})
    assert r.status_code == 200, r.text
    ans = r.json()
    assert ans["answer"]["content"]
    assert ans["answer"]["citations"]  # grounded with citations
    assert ans["session_id"]


def test_pdf_export_endpoint(client, db, monkeypatch):
    reel = _make_completed_reel(db, url="https://www.instagram.com/reel/H1/", caption="fitness routine for the whole week")
    # Avoid the heavy WeasyPrint dependency in tests by stubbing conversion.
    import app.services.pdf.renderer as renderer

    monkeypatch.setattr(renderer, "html_to_pdf", lambda html: b"%PDF-1.4 stub")
    r = client.post("/api/export/pdf", json={"reel_ids": [reel.id]})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
