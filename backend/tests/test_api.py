def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok" and body["demo_mode"] is True


def test_security_headers_on_every_response(client):
    for path in ("/api/health", "/api/sources", "/api/does-not-exist"):
        res = client.get(path)
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["cache-control"] == "no-store"
        assert "default-src 'none'" in res.headers["content-security-policy"]


def test_list_sources_includes_coverage(client):
    body = client.get("/api/sources").json()
    assert body["coverage"]["total"] == len(body["sources"])
    first = body["sources"][0]
    assert {"id", "url", "source_type", "verification", "excerpts", "last_checked"} <= first.keys()


def test_filter_sources_by_jurisdiction_and_topic(client):
    nj = client.get("/api/sources", params={"jurisdiction": "NJ"}).json()["sources"]
    assert nj and all(s["jurisdiction"] == "NJ" for s in nj)
    medicaid = client.get("/api/sources", params={"topic": "medicaid"}).json()["sources"]
    assert medicaid and all("medicaid" in s["topics"] for s in medicaid)


def test_invalid_filter_is_rejected_without_echoing_input(client):
    res = client.get("/api/sources", params={"topic": "<script>alert(1)</script>"})
    assert res.status_code == 422
    assert "<script>" not in res.text


def test_get_one_source_and_unknown_source(client):
    assert client.get("/api/sources/nj-dobi-ihcap").json()["jurisdiction"] == "NJ"
    missing = client.get("/api/sources/not-a-real-source")
    assert missing.status_code == 404
    assert missing.json()["error"] == "http_error"


def test_source_id_pattern_blocks_path_tricks(client):
    assert client.get("/api/sources/..%2F..%2Fetc").status_code in (404, 422)


def test_oversized_request_is_rejected_before_reading_body(client):
    res = client.post("/api/health", content=b"x" * 2048, headers={"content-type": "text/plain"})
    assert res.status_code == 413
    assert res.json()["error"] == "too_large"


def test_docs_disabled_when_configured(client):
    assert client.get("/api/docs").status_code == 404


def test_settings_default_to_production_on_vercel(monkeypatch):
    from patientshield.core.config import get_settings

    monkeypatch.delenv("PATIENTSHIELD_ENV", raising=False)
    monkeypatch.delenv("PATIENTSHIELD_ENABLE_DOCS", raising=False)
    monkeypatch.setenv("VERCEL_ENV", "preview")
    settings = get_settings()
    assert settings.environment == "production" and settings.enable_docs is False

    monkeypatch.delenv("VERCEL_ENV")
    assert get_settings().enable_docs is True


def test_claims_endpoint_lists_every_claim_with_known_sources(client):
    from patientshield.core.claims import CLAIMS
    from patientshield.core.sources.service import get_source

    body = client.get("/api/claims").json()
    assert {c["id"] for c in body} == set(CLAIMS)
    for claim in body:
        assert claim["text"] and claim["source_ids"]
        assert all(get_source(sid) is not None for sid in claim["source_ids"])


def test_every_source_is_cited_by_at_least_one_claim_or_flagged(client):
    """A verified source nobody cites is dead weight; a flagged one may exist only to explain an uncertainty."""
    cited = {sid for c in client.get("/api/claims").json() for sid in c["source_ids"]}
    for s in client.get("/api/sources").json()["sources"]:
        assert s["id"] in cited or s["verification"] == "needs-review", s["id"]


def test_chunked_json_body_over_the_limit_is_rejected(client):
    # No Content-Length header: the limit must be enforced while the body streams in (client cap is 1 KB).
    def chunks():
        for _ in range(8):
            yield b'{"answers": {"coverage_source": "' + b"a" * 200 + b'"}}'

    res = client.post("/api/triage", content=chunks(), headers={"Content-Type": "application/json"})
    assert res.status_code == 413
    assert res.json()["error"] == "too_large"
    assert res.headers["x-content-type-options"] == "nosniff"


def test_invalid_content_length_header_is_rejected(client):
    res = client.post("/api/triage", content=b"{}", headers={"Content-Type": "application/json", "Content-Length": "abc"})
    assert res.status_code == 400


def test_validation_errors_mask_user_chosen_keys(client):
    res = client.post("/api/plan", json={"answers": {"<img src=x onerror=alert(1)>": 5}})
    assert res.status_code == 422
    assert "<img" not in res.text and "onerror" not in res.text
    assert any(f.startswith("body.answers.*") for f in res.json()["fields"])


def test_suggest_rejects_oversized_signal_codes(client):
    assert client.post("/api/triage/suggest", json={"signals": ["x" * 41]}).status_code == 422
    assert client.post("/api/triage/suggest", json={"signals": ["medicaid"] * 21}).status_code == 422
