"""Settings come from environment variables only. No secrets are required for demo mode."""

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str
    max_request_bytes: int
    enable_docs: bool


def get_settings() -> Settings:
    env = os.getenv("PATIENTSHIELD_ENV", "development")
    return Settings(
        environment=env,
        # Vercel functions reject bodies over 4.5 MB; stay under it with headroom.
        max_request_bytes=int(os.getenv("PATIENTSHIELD_MAX_REQUEST_BYTES", str(4 * 1024 * 1024))),
        enable_docs=_bool("PATIENTSHIELD_ENABLE_DOCS", env != "production"),
    )
