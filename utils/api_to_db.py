"""Save Cricbuzz API data into the SQL database (get-or-create / upsert logic)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from utils.db_connection import DatabaseError, _clean, get_engine

FORMAT_MAP = {"TEST": "Test", "ODI": "ODI", "T20": "T20I", "T20I": "T20I"}


def normalize_format(raw: str | None) -> str | None:
    """Map Cricbuzz format strings to the schema's allowed values (else None)."""
    return FORMAT_MAP.get((raw or "").strip().upper())


def _ms_to_date(ms: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _get_or_create(conn, table: str, pk: str, where_col: str, where_val: Any,
                   values: dict[str, Any]) -> int:
    """Return the pk of the row where ``where_col = where_val``, inserting it if missing."""
    row = conn.execute(text(f"SELECT {pk} FROM {table} WHERE {where_col} = :v"),
                       {"v": where_val}).first()
    if row:
        return int(row[0])
    new_id = conn.execute(text(f"SELECT COALESCE(MAX({pk}), 0) + 1 FROM {table}")).scalar()
    data = {where_col: where_val, **values}
    cols = list(data)
    conn.execute(text(f"INSERT INTO {table} ({pk}, {', '.join(cols)}) "
                      f"VALUES (:_pk, {', '.join(':' + c for c in cols)})"),
                 {**data, "_pk": new_id})
    return int(new_id)


def save_matches(matches: list[dict[str, Any]]) -> tuple[int, int]:
    """Upsert teams, venues, series and matches from flattened API rows.

    Returns (saved, skipped). Rows are skipped when the format is not
    Test/ODI/T20I or when mandatory fields are missing.
    """
    saved = skipped = 0
    try:
        with get_engine().begin() as conn:  # all-or-nothing transaction
            for m in matches:
                fmt = normalize_format(m.get("format"))
                match_date = _ms_to_date(m.get("start_ms"))
                if not (fmt and m.get("team1") and m.get("team2") and match_date and m.get("match_id")):
                    skipped += 1
                    continue
                t1 = _get_or_create(conn, "teams", "team_id", "team_name", m["team1"],
                                    {"country": m["team1"], "short_name": m.get("team1_short")})
                t2 = _get_or_create(conn, "teams", "team_id", "team_name", m["team2"],
                                    {"country": m["team2"], "short_name": m.get("team2_short")})
                venue_id = None
                if m.get("venue"):
                    venue_id = _get_or_create(conn, "venues", "venue_id", "venue_name", m["venue"],
                                              {"city": m.get("city"), "country": "Unknown"})
                series_id = None
                if m.get("series"):
                    series_id = _get_or_create(conn, "series", "series_id", "series_name", m["series"],
                                               {"match_type": fmt, "start_date": match_date})
                exists = conn.execute(text("SELECT match_id FROM matches WHERE cb_id = :c"),
                                      {"c": m["match_id"]}).first()
                if exists:
                    conn.execute(text("UPDATE matches SET status = :s WHERE match_id = :id"),
                                 {"s": (m.get("state") or "Complete")[:40], "id": exists[0]})
                else:
                    new_id = conn.execute(text("SELECT COALESCE(MAX(match_id), 0) + 1 FROM matches")).scalar()
                    conn.execute(text(
                        "INSERT INTO matches (match_id, cb_id, series_id, description, match_format, "
                        "team1_id, team2_id, venue_id, match_date, status) VALUES "
                        "(:id, :cb, :ser, :d, :f, :t1, :t2, :v, :dt, :st)"),
                        {"id": new_id, "cb": m["match_id"], "ser": series_id,
                         "d": f"{m['team1']} vs {m['team2']} - {m.get('description') or fmt}"[:200],
                         "f": fmt, "t1": t1, "t2": t2, "v": venue_id, "dt": match_date,
                         "st": (m.get("state") or "Complete")[:40]})
                saved += 1
    except SQLAlchemyError as exc:
        raise DatabaseError(_clean(exc)) from exc
    return saved, skipped
