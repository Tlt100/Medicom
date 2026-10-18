from fastapi import APIRouter, HTTPException

from ..actionplan.builder import build_plan
from ..actionplan.models import ActionPlan, PlanRequest
from ..triage.flow import FlowError

router = APIRouter(tags=["plan"])


@router.post("/plan", response_model=ActionPlan)
def post_plan(body: PlanRequest) -> ActionPlan:
    try:
        return build_plan(body)
    except FlowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
