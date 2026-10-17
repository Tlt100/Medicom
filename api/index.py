"""Vercel entry point: exposes the FastAPI ASGI app as a Python serverless function."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from patientshield.app import app  # noqa: E402

__all__ = ["app"]
