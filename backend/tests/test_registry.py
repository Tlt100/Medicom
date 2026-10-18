"""The registry is the foundation for every legal claim, so its rules are tested directly."""

import copy
import datetime as dt
import re

import pytest
from pydantic import ValidationError

from patientshield.core.sources.models import Source, SourceType, Verification
from patientshield.core.sources.registry import RAW_SOURCES
from patientshield.core.sources.service import RegistryError, all_sources, coverage, load_sources

OFFICIAL_HOSTS = re.compile(r"^https://(www\.)?([a-z0-9-]+\.)*(gov|nj\.gov)/")


def test_registry_loads_and_has_mvp_size():
    sources = load_sources()
    assert 8 <= len(sources) <= 12


def test_every_source_is_an_official_https_government_url():
    for s in all_sources():
        assert OFFICIAL_HOSTS.match(str(s.url)), s.id


def test_verified_sources_have_verbatim_excerpts_and_needs_review_explains_why():
    for s in all_sources():
        if s.verification == Verification.verified:
            assert s.excerpts, s.id
        else:
            assert s.review_note and len(s.review_note) > 20, s.id


def test_dates_are_labelled_and_checks_are_not_in_the_future():
    today = dt.date(2026, 10, 17)
    for s in all_sources():
        assert s.last_checked <= today, s.id
        if s.date:
            assert s.date_label, s.id


def test_registry_covers_binding_law_and_both_jurisdictions():
    cov = coverage(all_sources())
    assert cov.binding >= 3
    assert cov.federal > 0 and cov.nj > 0
    assert cov.verified + cov.needs_review == cov.total


def test_known_uncertainty_is_flagged_not_hidden():
    by_id = {s.id: s for s in all_sources()}
    assert by_id["nj-dmahs-mc-26-06"].verification == Verification.needs_review
    assert "deadline" in by_id["nj-dobi-ihcap"].review_note.lower()
    assert "state-based exchange" in by_id["cms-0057-f-fact-sheet"].review_note.lower()


def _entry(**changes):
    entry = copy.deepcopy(RAW_SOURCES[0])
    entry.update(changes)
    return entry


def test_rejects_verified_source_without_excerpt():
    with pytest.raises(ValidationError, match="verbatim excerpt"):
        Source.model_validate(_entry(excerpts=[]))


def test_rejects_needs_review_without_note():
    with pytest.raises(ValidationError, match="must say what is unverified"):
        Source.model_validate(_entry(verification="needs-review", review_note=None))


def test_rejects_plain_http_url():
    with pytest.raises(ValidationError):
        Source.model_validate(_entry(url="http://www.ecfr.gov/example"))


def test_rejects_unlabelled_date():
    with pytest.raises(ValidationError, match="date needs a label"):
        Source.model_validate(_entry(date_label=None))


def test_rejects_duplicate_ids():
    with pytest.raises(RegistryError, match="duplicate"):
        load_sources([RAW_SOURCES[0], RAW_SOURCES[0]])


def test_binding_flag_matches_source_type():
    for s in all_sources():
        assert s.is_binding == (s.source_type in {SourceType.statute, SourceType.regulation})
