"""Centralised SQL database connection handling (SQLite / PostgreSQL / MySQL).

All pages and services go through this module so credentials and engine
configuration live in exactly one place.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from utils.config import BASE_DIR, get_settings

SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"


class DatabaseError(Exception):
    """Raised for any database failure, with a user-friendly message."""


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create (once) and return the SQLAlchemy engine."""
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        Path(url.replace("sqlite:///", "", 1)).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, future=True, pool_pre_ping=True)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _record):  # pragma: no cover - trivial
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def reset_engine() -> None:
    """Dispose the cached engine (used by tests / after settings change)."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()


def run_query(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame."""
    try:
        with get_engine().connect() as conn:
            return pd.read_sql_query(text(sql), conn, params=params or {})
    except SQLAlchemyError as exc:
        raise DatabaseError(_clean(exc)) from exc


def execute(sql: str, params: dict[str, Any] | None = None) -> int:
    """Run a single write statement inside a transaction; return affected rows."""
    try:
        with get_engine().begin() as conn:
            return conn.execute(text(sql), params or {}).rowcount
    except SQLAlchemyError as exc:
        raise DatabaseError(_clean(exc)) from exc


def _clean(exc: SQLAlchemyError) -> str:
    """Return a short human-readable message for a SQLAlchemy exception."""
    return str(getattr(exc, "orig", exc)).split("\n")[0]


def _split_statements(script: str) -> list[str]:
    """Split a SQL script into statements (comment lines removed)."""
    lines = [ln for ln in script.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def init_db(seed: bool = False) -> None:
    """Create all tables/indexes/views; optionally load the sample dataset."""
    engine = get_engine()
    script = SCHEMA_FILE.read_text(encoding="utf-8")
    try:
        with engine.begin() as conn:
            for stmt in _split_statements(script):
                conn.execute(text(stmt))
    except SQLAlchemyError as exc:
        raise DatabaseError(f"Schema creation failed: {_clean(exc)}") from exc

    if seed:
        with engine.connect() as conn:
            empty = conn.execute(text("SELECT COUNT(*) FROM players")).scalar() == 0
        if empty:
            from database.seed_sample_data import seed_sample_data

            seed_sample_data(engine)


def ensure_database() -> None:
    """Create + seed the database on first run (no-op afterwards)."""
    if not inspect(get_engine()).has_table("players"):
        init_db(seed=True)
    else:
        init_db(seed=False)  # idempotent: adds any missing tables/views


def safe_select(sql: str) -> str:
    """Validate that user supplied SQL is a single read-only statement."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise DatabaseError("Query is empty.")
    if ";" in cleaned:
        raise DatabaseError("Only a single statement is allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise DatabaseError("Only SELECT queries are allowed here.")
    banned = r"\b(insert|update|delete|drop|alter|create|truncate|attach|detach|pragma|replace)\b"
    if re.search(banned, cleaned, re.IGNORECASE):
        raise DatabaseError("Write/DDL keywords are not allowed in this interface.")
    return cleaned
