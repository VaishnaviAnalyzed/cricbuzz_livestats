"""Cricbuzz LiveStats - main entry point.

Run with:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Cricbuzz LiveStats", page_icon="🏏", layout="wide")

from utils.api_client import CricbuzzClient  # noqa: E402
from utils.config import get_settings  # noqa: E402
from utils.db_connection import DatabaseError, ensure_database  # noqa: E402


@st.cache_resource(show_spinner="Preparing database...")
def _init_database() -> bool:
    """Create tables and load sample data on first launch."""
    ensure_database()
    return True


try:
    _init_database()
except DatabaseError as exc:
    st.error(f"Database connection failed: {exc}")
    st.info("Check DATABASE_URL in your .env file (default is a local SQLite file).")
    st.stop()

with st.sidebar:
    st.markdown("### 🏏 Cricbuzz LiveStats")
    st.caption("Real-time cricket insights & SQL-based analytics")
    api_ok = CricbuzzClient().configured
    st.caption(("🟢 Cricbuzz API key detected" if api_ok else "🟡 No API key - using sample database only"))
    st.caption(f"🗄️ DB: `{get_settings().database_url.split('://')[0]}`")

navigation = st.navigation([
    st.Page("pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/live_matches.py", title="Live Matches", icon="⚡"),
    st.Page("pages/top_stats.py", title="Top Player Stats", icon="🏆"),
    st.Page("pages/sql_queries.py", title="SQL Queries & Analytics", icon="🔍"),
    st.Page("pages/crud_operations.py", title="CRUD Operations", icon="🛠️"),
])
navigation.run()
