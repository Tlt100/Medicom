from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from ..claims import CLAIMS

router = APIRouter(tags=["claims"])


class ClaimSummary(BaseModel):
    id: str
    text: str
    source_ids: List[str]


@router.get("/claims", response_model=List[ClaimSummary])
def list_claims() -> List[ClaimSummary]:
    """Every plain-language legal statement PatientShield can show, with the sources it cites."""
    return [ClaimSummary(id=c.id, text=c.text, source_ids=list(c.source_ids)) for c in CLAIMS.values()]
