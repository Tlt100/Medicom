"""Deployment packaging checks: these catch misconfigurations that otherwise only show up on Vercel.

Vercel's Python runtime prefers pyproject.toml over requirements.txt and .python-version when it exists,
so this project deliberately has no pyproject.toml (tool settings live in pytest.ini and ruff.toml).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_pyproject_so_vercel_uses_requirements_and_python_version():
    assert not (ROOT / "pyproject.toml").exists()


def test_runtime_python_is_pinned_to_3_12():
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"


def test_runtime_dependencies_are_pinned():
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    deps = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    assert deps, "requirements.txt must list the API's runtime dependencies"
    assert all(re.match(r"^[A-Za-z0-9_.-]+==[0-9][\w.]*$", d) for d in deps), deps


def test_vercel_entrypoint_exposes_the_real_app():
    sys.path.insert(0, str(ROOT / "api"))
    try:
        import index
    finally:
        sys.path.pop(0)
    from patientshield.app import app

    assert index.app is app
