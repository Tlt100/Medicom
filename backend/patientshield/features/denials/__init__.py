"""Denial letters: extraction rules, sample letters, and the cited action plan.

Importing this package registers the denial extractor with the core document pipeline.
"""

from patientshield.features.denials import extraction as _extraction  # noqa: F401  (registers the extractor)
from patientshield.features.denials.plan_routes import router as plan_router
from patientshield.features.denials.sample_routes import router as sample_router

ROUTERS = [sample_router, plan_router]
