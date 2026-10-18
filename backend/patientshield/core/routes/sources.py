from typing import Optional

from fastapi import APIRouter, HTTPException, Path

from patientshield.core.sources.models import Jurisdiction, RegistryResponse, Source, Topic
from patientshield.core.sources.service import get_source, registry_response

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=RegistryResponse)
def list_sources(topic: Optional[Topic] = None, jurisdiction: Optional[Jurisdiction] = None) -> RegistryResponse:
    return registry_response(topic, jurisdiction)


@router.get("/{source_id}", response_model=Source)
def read_source(source_id: str = Path(pattern=r"^[a-z0-9-]{1,80}$")) -> Source:
    source = get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return source
