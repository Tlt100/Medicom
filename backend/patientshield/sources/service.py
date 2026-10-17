"""Loads and validates the registry once, and answers queries about it."""

from functools import lru_cache
from typing import Dict, List, Optional

from .models import Coverage, Jurisdiction, RegistryResponse, Source, Topic, Verification
from .registry import LAST_REVIEWED, RAW_SOURCES, REGISTRY_VERSION


class RegistryError(ValueError):
    pass


def load_sources(raw=RAW_SOURCES) -> List[Source]:
    """Validate every entry. A malformed or duplicate entry fails loudly at startup."""
    sources: List[Source] = []
    seen = set()
    for entry in raw:
        source = Source.model_validate(entry)
        if source.id in seen:
            raise RegistryError(f"duplicate source id: {source.id}")
        seen.add(source.id)
        sources.append(source)
    return sources


@lru_cache(maxsize=1)
def _sources() -> List[Source]:
    return load_sources()


@lru_cache(maxsize=1)
def _by_id() -> Dict[str, Source]:
    return {s.id: s for s in _sources()}


def all_sources(topic: Optional[Topic] = None, jurisdiction: Optional[Jurisdiction] = None) -> List[Source]:
    out = _sources()
    if topic is not None:
        out = [s for s in out if topic in s.topics]
    if jurisdiction is not None:
        out = [s for s in out if s.jurisdiction == jurisdiction]
    return out


def get_source(source_id: str) -> Optional[Source]:
    return _by_id().get(source_id)


def coverage(sources: List[Source]) -> Coverage:
    verified = sum(1 for s in sources if s.verification == Verification.verified)
    return Coverage(
        total=len(sources),
        verified=verified,
        needs_review=len(sources) - verified,
        binding=sum(1 for s in sources if s.is_binding),
        federal=sum(1 for s in sources if s.jurisdiction == Jurisdiction.federal),
        nj=sum(1 for s in sources if s.jurisdiction == Jurisdiction.nj),
    )


def registry_response(topic: Optional[Topic] = None, jurisdiction: Optional[Jurisdiction] = None) -> RegistryResponse:
    sources = all_sources(topic, jurisdiction)
    return RegistryResponse(
        registry_version=REGISTRY_VERSION,
        last_reviewed=LAST_REVIEWED,
        coverage=coverage(sources),
        sources=sources,
    )
