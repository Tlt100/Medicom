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


def test_frontend_security_headers_stay_strict():
    """The site's CSP and headers live in vercel.json; loosening them should fail CI, not slip through."""
    import json

    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    headers = {h["key"].lower(): h["value"] for rule in config["headers"] for h in rule["headers"]}
    csp = headers["content-security-policy"]
    directives = dict(d.strip().split(" ", 1) for d in csp.split(";") if d.strip() and " " in d.strip())
    assert directives["default-src"] == "'self'"
    assert directives["script-src"] == "'self'"
    assert directives["frame-ancestors"] == "'none'"
    assert directives["object-src"] == "'none'"
    for unsafe in ("'unsafe-inline'", "'unsafe-eval'", "http:", "https:", "*"):
        assert unsafe not in csp, unsafe
    assert "https://" not in csp, "no third-party hosts (fonts are self-hosted)"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["cross-origin-opener-policy"] == "same-origin"
    assert "max-age=" in headers["strict-transport-security"]
