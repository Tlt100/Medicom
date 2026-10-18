import datetime as dt

from fastapi import APIRouter, HTTPException

from patientshield.core.triage.flow import FlowError
from patientshield.features.denials.actionplan.builder import build_plan
from patientshield.features.denials.actionplan.models import ActionPlan, PlanRequest

router = APIRouter(tags=["plan"])


@router.post("/plan", response_model=ActionPlan)
def post_plan(body: PlanRequest) -> ActionPlan:
    try:
        server_today = dt.date.today()
        today = body.today if body.today and abs((body.today - server_today).days) <= 1 else server_today
        return build_plan(body, today=today)
    except FlowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
