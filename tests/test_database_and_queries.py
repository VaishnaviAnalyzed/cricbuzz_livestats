"""Database + SQL analytics tests (run with: pytest -q)."""
from __future__ import annotations

import pytest

from sql.queries import QUERIES
from utils import crud
from utils.db_connection import (DatabaseError, init_db, reset_engine, run_query,
                                 safe_select)


@pytest.fixture(scope="module", autouse=True)
def database(tmp_path_factory):
    """Create an isolated, seeded SQLite DB for the whole module."""
    import os

    path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{path.as_posix()}"
    reset_engine()
    init_db(seed=True)
    yield
    reset_engine()
    os.environ.pop("DATABASE_URL", None)


def test_seed_row_counts():
    assert run_query("SELECT COUNT(*) AS n FROM players").iloc[0, 0] == 88
    assert run_query("SELECT COUNT(*) AS n FROM matches").iloc[0, 0] == 420


def test_there_are_25_queries():
    assert [q["id"] for q in QUERIES] == list(range(1, 26))


@pytest.mark.parametrize("query", QUERIES, ids=lambda q: f"Q{q['id']}")
def test_every_query_runs(query):
    df = run_query(query["sql"])
    assert list(df.columns), "query returned no columns"
    if query["id"] not in (9,):  # Q9 depends on random career stats
        assert len(df) > 0, f"Q{query['id']} returned no rows with sample data"
    if "extra_sql" in query:
        assert len(run_query(query["extra_sql"])) > 0


def test_safe_select_blocks_writes():
    assert safe_select("SELECT 1;") == "SELECT 1"
    for bad in ("DROP TABLE players", "SELECT 1; DELETE FROM players", "UPDATE players SET country='x'"):
        with pytest.raises(DatabaseError):
            safe_select(bad)


def test_crud_roundtrip_and_validation():
    values = {"full_name": "Test Player", "country": "India", "playing_role": "Batsman",
              "batting_style": "Right-hand bat", "bowling_style": None}
    assert crud.validate("Players", values) == []
    new_id = crud.create_row("Players", values)
    assert crud.get_row("Players", new_id)["full_name"] == "Test Player"
    crud.update_row("Players", new_id, {**values, "full_name": "Renamed"})
    assert crud.get_row("Players", new_id)["full_name"] == "Renamed"
    crud.delete_row("Players", new_id)
    assert crud.get_row("Players", new_id) is None
    assert crud.validate("Players", {**values, "full_name": ""})


def test_foreign_key_protects_teams_in_use():
    with pytest.raises(DatabaseError):
        crud.delete_row("Teams", 1)
