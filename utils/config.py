"""Central configuration.

Secrets (API key, DB credentials) are never hard-coded. They are read, in order, from:
1. Environment variables / a local ``.env`` file
2. Streamlit secrets (``.streamlit/secrets.toml`` or Streamlit Cloud secrets)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_HOST = "cricbuzz-cricket.p.rapidapi.com"
DEFAULT_DB_URL = f"sqlite:///{(BASE_DIR / 'data' / 'cricbuzz.db').as_posix()}"


def _secret(name: str, default: str | None = None) -> str | None:
    """Return a setting from env vars, falling back to Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:  # Streamlit may be missing (notebooks/tests) or have no secrets file
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:  # noqa: BLE001 - any failure simply means "not configured"
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    rapidapi_key: str | None
    rapidapi_host: str
    database_url: str


def get_settings() -> Settings:
    """Build the settings object (read lazily so tests can override env vars)."""
    return Settings(
        rapidapi_key=_secret("RAPIDAPI_KEY"),
        rapidapi_host=_secret("RAPIDAPI_HOST", DEFAULT_HOST) or DEFAULT_HOST,
        database_url=_secret("DATABASE_URL", DEFAULT_DB_URL) or DEFAULT_DB_URL,
    )
