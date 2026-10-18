from fastapi import APIRouter, HTTPException

from patientshield.core.triage.flow import FlowError
from patientshield.core.triage.models import FlowOut, Suggestion, SuggestRequest, TriageRequest, TriageResult
from patientshield.core.triage.service import flow, suggest, triage

router = APIRouter(prefix="/triage", tags=["triage"])


@router.get("/flow", response_model=FlowOut)
def get_flow() -> FlowOut:
    return flow()


@router.post("/suggest", response_model=Suggestion)
def post_suggest(body: SuggestRequest) -> Suggestion:
    return suggest(body.signals)


@router.post("", response_model=TriageResult)
def post_triage(body: TriageRequest) -> TriageResult:
    try:
        return triage(body.answers)
    except FlowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
