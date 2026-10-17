"""Deployment packaging checks: these catch the misconfigurations that only show up on Vercel."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _pyproject_deps() -> list:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
    assert block, "pyproject.toml must declare [project] dependencies for Vercel"
    return sorted(re.findall(r'"([^"]+)"', block.group(1)))


def _requirements() -> list:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return sorted(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def test_pyproject_and_requirements_list_the_same_pinned_dependencies():
    assert _pyproject_deps() == _requirements()
    assert all("==" in dep for dep in _requirements()), "pin exact versions for reproducible deploys"


def test_python_range_has_an_upper_bound_for_vercel():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'requires-python\s*=\s*">=3\.9,<3\.13"', text)


def test_vercel_entrypoint_exposes_the_real_app():
    sys.path.insert(0, str(ROOT / "api"))
    try:
        import index  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    from patientshield.app import app

    assert index.app is app
