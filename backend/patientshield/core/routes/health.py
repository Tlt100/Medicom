from fastapi import APIRouter

from patientshield import __version__
from patientshield.core.sources.registry import REGISTRY_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "registry_version": REGISTRY_VERSION, "demo_mode": True}
