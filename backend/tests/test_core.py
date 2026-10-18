"""The shared core: document pipeline and types, the citation system, and module boundaries."""

import re
from pathlib import Path
from urllib.parse import quote

import pytest

from patientshield.core.citations import CitationError, DocumentCitation, SourceCitation, check_document_citations, check_source_citations
from patientshield.core.documents import pipeline
from patientshield.core.documents.parsing import DocumentError
from patientshield.features.denials.samples import SAMPLES_BY_ID, page_texts

PACKAGE = Path(__file__).resolve().parents[1] / "patientshield"
LETTER = "\f".join(page_texts(SAMPLES_BY_ID["nj-prior-auth-mri"])).encode()


# ---------------------------------------------------------------- module boundaries


def test_core_never_imports_a_feature():
    """Features build on core; core must stay usable by every feature, so it can't depend on one."""
    offenders = []
    for path in (PACKAGE / "core").rglob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"\s*(from|import)\s+patientshield\.features", line):
                offenders.append(f"{path.relative_to(PACKAGE)}: {line.strip()}")
    assert offenders == []


def test_features_do_not_import_each_other():
    features = [p.name for p in (PACKAGE / "features").iterdir() if p.is_dir() and not p.name.startswith("_")]
    for feature in features:
        for path in (PACKAGE / "features" / feature).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for other in features:
                if other != feature:
                    assert f"patientshield.features.{other}" not in text, f"{path} imports features.{other}"


# ---------------------------------------------------------------- document pipeline


def test_denial_extractor_is_registered_and_others_are_not_yet():
    assert pipeline.supported_types() == ["denial"]


@pytest.mark.parametrize("doc_type,label", [("eob", "an Explanation of Benefits"), ("bill", "a medical bill")])
def test_unbuilt_document_types_are_refused_honestly(doc_type, label):
    with pytest.raises(DocumentError) as err:
        pipeline.process("x.txt", LETTER, doc_type)  # type: ignore[arg-type]
    assert err.value.code == "not_available"
    assert label in err.value.message and "coming soon" in err.value.message


def test_pipeline_labels_the_document_type():
    result = pipeline.process("letter.txt", LETTER, "denial")
    assert result.document.doc_type == "denial"


def _upload(client, doc_type=None):
    headers = {"Content-Type": "text/plain", "X-File-Name": quote("letter.txt")}
    if doc_type is not None:
        headers["X-Document-Type"] = doc_type
    return client.post("/api/extract", content=LETTER, headers=headers)


def test_upload_defaults_to_a_denial_letter(api_client):
    res = _upload(api_client)
    assert res.status_code == 200 and res.json()["document"]["doc_type"] == "denial"


def test_upload_of_an_unbuilt_type_says_coming_soon(api_client):
    res = _upload(api_client, "eob")
    assert res.status_code == 422
    assert res.json()["error"] == "not_available"


def test_upload_rejects_unknown_document_types_without_echoing_them(api_client):
    res = _upload(api_client, "<script>")
    assert res.status_code == 422 and res.json()["error"] == "invalid_document_type"
    assert "<script>" not in res.text


# ---------------------------------------------------------------- citation system


def test_document_citations_must_match_the_page():
    pages = ["Your claim was denied."]
    check_document_citations(pages, [DocumentCitation(page=1, start=0, end=10, quote="Your claim")])
    with pytest.raises(CitationError):
        check_document_citations(pages, [DocumentCitation(page=1, start=0, end=10, quote="Your clain")])


def test_source_citations_must_name_a_real_source_and_excerpt():
    check_source_citations([SourceCitation(source_id="cfr-29-2560-503-1", locator="§ 2560.503-1(h)(3)(i)")])
    check_source_citations([SourceCitation(source_id="nj-dobi-ihcap")])
    with pytest.raises(CitationError):
        check_source_citations([SourceCitation(source_id="not-a-source")])
    with pytest.raises(CitationError):
        check_source_citations([SourceCitation(source_id="nj-dobi-ihcap", locator="§ made-up")])
