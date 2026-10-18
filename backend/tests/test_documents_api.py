"""Upload and sample-letter API: the upload → extraction workflow end to end."""

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from patientshield.app import create_app
from patientshield.config import Settings
from patientshield.routers import documents as documents_router
from patientshield.samples.letters import SAMPLES, SAMPLES_BY_ID, page_texts
from patientshield.samples.pdfgen import render_pdf


@pytest.fixture
def api() -> TestClient:
    return TestClient(create_app(Settings(environment="test", max_request_bytes=4 * 1024 * 1024, enable_docs=False)))


def upload(api: TestClient, name: str, data: bytes, content_type: str = "application/pdf"):
    return api.post("/api/extract", content=data, headers={"Content-Type": content_type, "X-File-Name": quote(name)})


def test_upload_pdf_returns_cited_fields(api):
    sample = SAMPLES_BY_ID["nj-prior-auth-mri"]
    res = upload(api, "my letter.pdf", render_pdf(sample))
    assert res.status_code == 200
    body = res.json()
    assert body["document"] == {
        "name": "my letter.pdf",
        "kind": "pdf",
        "page_count": 2,
        "size_bytes": len(render_pdf(sample)),
        "synthetic": False,
        "sample_id": None,
    }
    deadline = next(f for f in body["fields"] if f["key"] == "appeal_deadline")
    c = deadline["citations"][0]
    assert body["pages"][c["page"] - 1]["text"][c["start"] : c["end"]] == c["quote"]
    assert "not save" in body["retention"]
    assert res.headers["cache-control"] == "no-store"


def test_upload_text_file(api):
    text = "\f".join(page_texts(SAMPLES_BY_ID["self-funded-out-of-network"]))
    res = upload(api, "letter.txt", text.encode(), "text/plain")
    assert res.status_code == 200
    assert res.json()["document"]["kind"] == "text"


def test_upload_rejects_bad_files_with_clear_messages(api):
    res = upload(api, "photo.png", b"\x89PNG\r\n\x1a\n", "image/png")
    assert res.status_code == 422
    assert res.json() == {"error": "unsupported_type", "message": "PatientShield accepts PDF (.pdf) and plain-text (.txt) files only."}

    empty = upload(api, "empty.pdf", b"")
    assert empty.status_code == 422 and empty.json()["error"] == "empty"


def test_upload_size_limit_without_content_length(api, monkeypatch):
    monkeypatch.setattr(documents_router, "MAX_BYTES", 100)

    def chunks():
        for _ in range(5):
            yield b"x" * 50

    res = api.post("/api/extract", content=chunks(), headers={"X-File-Name": "big.txt"})
    assert res.status_code == 413 and res.json()["error"] == "too_large"


def test_upload_size_limit_with_content_length(client):
    # The default test client caps requests at 1 KB, so this is rejected before the body is read.
    res = client.post("/api/extract", content=b"x" * 2048, headers={"X-File-Name": "a.txt"})
    assert res.status_code == 413


def test_malicious_file_name_is_sanitized_not_echoed(api):
    text = "\f".join(page_texts(SAMPLES_BY_ID["nj-prior-auth-mri"]))
    res = upload(api, "<img src=x onerror=alert(1)>.txt", text.encode(), "text/plain")
    assert res.status_code == 200
    assert "<" not in res.json()["document"]["name"]


def test_list_samples(api):
    body = api.get("/api/samples").json()
    assert [s["id"] for s in body] == [s.id for s in SAMPLES]
    assert all(s["filename"].startswith("synthetic-") for s in body)


def test_extract_sample_runs_the_pdf_path(api):
    body = api.post("/api/samples/vague-letter-missing-details/extract").json()
    assert body["document"]["synthetic"] is True and body["document"]["kind"] == "pdf"
    assert any(s["kind"] == "suspicious" for s in body["signals"])


def test_download_sample_pdf(api):
    res = api.get("/api/samples/nj-prior-auth-mri/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.headers["content-disposition"] == 'attachment; filename="synthetic-nj-prior-auth-mri.pdf"'
    assert res.content.startswith(b"%PDF-")


def test_unknown_and_invalid_sample_ids(api):
    assert api.post("/api/samples/does-not-exist/extract").status_code == 404
    assert api.get("/api/samples/BAD_ID!/pdf").status_code in (404, 422)
