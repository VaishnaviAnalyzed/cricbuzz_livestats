"""Data-driven CRUD service for the admin page.

Each manageable table is described once in ``ENTITIES``; the generic functions
below build validated, parameterised SQL from that description. Table/column
names come ONLY from this config (never from user input), and every value is
bound as a parameter, which prevents SQL injection.
"""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from utils.db_connection import DatabaseError, _clean, get_engine, run_query

ROLES = ["Batsman", "Bowler", "All-rounder", "Wicket-keeper"]
BAT_STYLES = ["Right-hand bat", "Left-hand bat"]
FORMATS = ["Test", "ODI", "T20I"]
STATUSES = ["Complete", "Live", "Upcoming", "Abandoned"]
VICTORY_TYPES = ["runs", "wickets", "draw", "tie"]
TOSS = ["bat", "bowl"]


def field(name: str, label: str, kind: str, required: bool = False, **kw: Any) -> dict[str, Any]:
    """Describe one editable column."""
    return {"name": name, "label": label, "kind": kind, "required": required, **kw}


def _fk(table: str, id_col: str, label_col: str) -> dict[str, str]:
    return {"table": table, "id": id_col, "label": label_col}


def _match_rules(v: dict[str, Any]) -> list[str]:
    errors = []
    if v.get("team1_id") and v.get("team1_id") == v.get("team2_id"):
        errors.append("Team 1 and Team 2 must be different.")
    winner = v.get("winner_team_id")
    if winner and winner not in (v.get("team1_id"), v.get("team2_id")):
        errors.append("Winner must be one of the two teams.")
    return errors


ENTITIES: dict[str, dict[str, Any]] = {
    "Players": {
        "table": "players", "pk": "player_id", "label": "full_name",
        "fields": [
            field("full_name", "Full name", "text", True),
            field("country", "Country", "text", True),
            field("playing_role", "Playing role", "select", True, options=ROLES),
            field("batting_style", "Batting style", "select", options=BAT_STYLES),
            field("bowling_style", "Bowling style", "text"),
        ],
    },
    "Player career stats": {
        "table": "player_career_stats", "pk": "stat_id", "label": "format",
        "fields": [
            field("player_id", "Player", "fk", True, fk=_fk("players", "player_id", "full_name")),
            field("format", "Format", "select", True, options=FORMATS),
            field("matches", "Matches", "int", True, min=0),
            field("innings", "Innings", "int", True, min=0),
            field("runs", "Runs", "int", True, min=0),
            field("batting_avg", "Batting average", "float", min=0),
            field("strike_rate", "Strike rate", "float", min=0),
            field("highest_score", "Highest score", "int", min=0),
            field("centuries", "Centuries", "int", min=0),
            field("fifties", "Fifties", "int", min=0),
            field("wickets", "Wickets", "int", min=0),
            field("bowling_avg", "Bowling average", "float", min=0),
            field("economy", "Economy", "float", min=0),
            field("catches", "Catches", "int", min=0),
            field("stumpings", "Stumpings", "int", min=0),
        ],
    },
    "Matches": {
        "table": "matches", "pk": "match_id", "label": "description",
        "rules": _match_rules,
        "fields": [
            field("description", "Description", "text", True),
            field("match_format", "Format", "select", True, options=FORMATS),
            field("team1_id", "Team 1", "fk", True, fk=_fk("teams", "team_id", "team_name")),
            field("team2_id", "Team 2", "fk", True, fk=_fk("teams", "team_id", "team_name")),
            field("venue_id", "Venue", "fk", fk=_fk("venues", "venue_id", "venue_name")),
            field("series_id", "Series", "fk", fk=_fk("series", "series_id", "series_name")),
            field("match_date", "Match date", "date", True),
            field("status", "Status", "select", True, options=STATUSES),
            field("toss_winner_id", "Toss winner", "fk", fk=_fk("teams", "team_id", "team_name")),
            field("toss_decision", "Toss decision", "select", options=TOSS),
            field("winner_team_id", "Winner", "fk", fk=_fk("teams", "team_id", "team_name")),
            field("victory_type", "Victory type", "select", options=VICTORY_TYPES),
            field("victory_margin", "Victory margin", "int", min=0),
        ],
    },
    "Teams": {
        "table": "teams", "pk": "team_id", "label": "team_name",
        "fields": [
            field("team_name", "Team name", "text", True),
            field("country", "Country", "text", True),
            field("short_name", "Short name", "text"),
        ],
    },
    "Venues": {
        "table": "venues", "pk": "venue_id", "label": "venue_name",
        "fields": [
            field("venue_name", "Venue name", "text", True),
            field("city", "City", "text"),
            field("country", "Country", "text", True),
            field("capacity", "Capacity", "int", min=1),
        ],
    },
    "Series": {
        "table": "series", "pk": "series_id", "label": "series_name",
        "fields": [
            field("series_name", "Series name", "text", True),
            field("host_country", "Host country", "text"),
            field("match_type", "Match type", "select", options=FORMATS),
            field("start_date", "Start date", "date"),
            field("total_matches", "Total matches", "int", min=0),
        ],
    },
}


# ---------------------------------------------------------------- reads
def list_rows(entity: str, search: str | None = None, limit: int = 1000):
    """Return rows of an entity (newest first), optionally filtered by label text."""
    cfg = ENTITIES[entity]
    sql = f"SELECT * FROM {cfg['table']}"
    params: dict[str, Any] = {}
    if search:
        sql += f" WHERE LOWER(CAST({cfg['label']} AS TEXT)) LIKE :s"
        params["s"] = f"%{search.lower()}%"
    sql += f" ORDER BY {cfg['pk']} DESC LIMIT {int(limit)}"
    return run_query(sql, params)


def get_row(entity: str, pk: int) -> dict[str, Any] | None:
    """Fetch one row as a dict (or None)."""
    cfg = ENTITIES[entity]
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text(f"SELECT * FROM {cfg['table']} WHERE {cfg['pk']} = :pk"),
                               {"pk": pk}).mappings().first()
        return dict(row) if row else None
    except SQLAlchemyError as exc:
        raise DatabaseError(_clean(exc)) from exc


def fk_options(fk: dict[str, str]) -> dict[int, str]:
    """Return {id: label} for a foreign-key dropdown."""
    df = run_query(f"SELECT {fk['id']} AS id, {fk['label']} AS label FROM {fk['table']} "
                   f"ORDER BY {fk['label']}")
    return dict(zip(df["id"].astype(int), df["label"].astype(str)))


# ---------------------------------------------------------------- validation
def validate(entity: str, values: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty = valid)."""
    cfg = ENTITIES[entity]
    errors: list[str] = []
    for f in cfg["fields"]:
        v = values.get(f["name"])
        empty = v is None or (isinstance(v, str) and not v.strip())
        if f["required"] and empty:
            errors.append(f"{f['label']} is required.")
            continue
        if empty:
            continue
        if f["kind"] in ("int", "float") and "min" in f and v < f["min"]:
            errors.append(f"{f['label']} must be >= {f['min']}.")
    rules: Callable | None = cfg.get("rules")
    if rules:
        errors.extend(rules(values))
    return errors


def _clean_values(entity: str, values: dict[str, Any]) -> dict[str, Any]:
    """Normalise empty strings to NULL, strip text, convert dates to ISO strings."""
    out: dict[str, Any] = {}
    for f in ENTITIES[entity]["fields"]:
        v = values.get(f["name"])
        if isinstance(v, str):
            v = v.strip() or None
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        out[f["name"]] = v
    return out


# ---------------------------------------------------------------- writes
def create_row(entity: str, values: dict[str, Any]) -> int:
    """Insert a row inside a transaction and return its new primary key."""
    errors = validate(entity, values)
    if errors:
        raise ValueError(" ".join(errors))
    cfg, data = ENTITIES[entity], _clean_values(entity, values)
    cols = list(data)
    try:
        with get_engine().begin() as conn:  # one atomic transaction
            new_id = conn.execute(
                text(f"SELECT COALESCE(MAX({cfg['pk']}), 0) + 1 FROM {cfg['table']}")).scalar()
            conn.execute(
                text(f"INSERT INTO {cfg['table']} ({cfg['pk']}, {', '.join(cols)}) "
                     f"VALUES (:_pk, {', '.join(':' + c for c in cols)})"),
                {**data, "_pk": new_id})
        return int(new_id)
    except SQLAlchemyError as exc:
        raise DatabaseError(_clean(exc)) from exc


def update_row(entity: str, pk: int, values: dict[str, Any]) -> int:
    """Update a row; returns the number of affected rows."""
    errors = validate(entity, values)
    if errors:
        raise ValueError(" ".join(errors))
    cfg, data = ENTITIES[entity], _clean_values(entity, values)
    sets = ", ".join(f"{c} = :{c}" for c in data)
    try:
        with get_engine().begin() as conn:
            return conn.execute(
                text(f"UPDATE {cfg['table']} SET {sets} WHERE {cfg['pk']} = :_pk"),
                {**data, "_pk": pk}).rowcount
    except SQLAlchemyError as exc:
        raise DatabaseError(_clean(exc)) from exc


def delete_row(entity: str, pk: int) -> int:
    """Delete a row. Foreign-key violations surface as a DatabaseError."""
    cfg = ENTITIES[entity]
    try:
        with get_engine().begin() as conn:
            return conn.execute(text(f"DELETE FROM {cfg['table']} WHERE {cfg['pk']} = :pk"),
                                {"pk": pk}).rowcount
    except SQLAlchemyError as exc:
        raise DatabaseError(
            f"Cannot delete: {_clean(exc)} (the record is probably referenced by other data)."
        ) from exc
