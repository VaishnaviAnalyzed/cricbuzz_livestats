"""Smoke-test every Streamlit page with Streamlit's AppTest harness."""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["live_matches", "top_stats", "sql_queries", "crud_operations"]


@pytest.fixture(scope="module", autouse=True)
def database(tmp_path_factory):
    from utils.db_connection import init_db, reset_engine

    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path_factory.mktemp('db') / 'app.db').as_posix()}"
    os.environ.pop("RAPIDAPI_KEY", None)
    reset_engine()
    init_db(seed=True)
    yield
    reset_engine()


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(page):
    at = AppTest.from_file(str(ROOT / "pages" / f"{page}.py"), default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]


def test_sql_page_runs_a_query():
    at = AppTest.from_file(str(ROOT / "pages" / "sql_queries.py"), default_timeout=30).run()
    at.button(key="run_prepared").click().run()
    assert not at.exception
    assert at.dataframe, "expected a result table"


def test_crud_create_player():
    at = AppTest.from_file(str(ROOT / "pages" / "crud_operations.py"), default_timeout=30).run()
    at.text_input(key="c_Players_full_name").set_value("Smoke Tester")
    at.text_input(key="c_Players_country").set_value("India")
    at.selectbox(key="c_Players_playing_role").select("Batsman")
    at.button[0].click().run()
    assert not at.exception
    assert any("Created record" in s.value for s in at.success)


def test_full_app_navigation():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
