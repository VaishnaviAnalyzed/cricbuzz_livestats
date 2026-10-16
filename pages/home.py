"""Home page: project overview, tools, instructions and navigation."""
import streamlit as st

from utils.db_connection import DatabaseError, run_query

st.title("🏏 Cricbuzz LiveStats")
st.subheader("Real-Time Cricket Insights & SQL-Based Analytics")
st.write(
    "A cricket analytics dashboard that combines **live data from the Cricbuzz API** with a "
    "**SQL database** in an interactive Streamlit web app."
)

# ---- database snapshot -------------------------------------------------
try:
    counts = run_query(
        "SELECT (SELECT COUNT(*) FROM players) AS players, (SELECT COUNT(*) FROM teams) AS teams, "
        "(SELECT COUNT(*) FROM matches) AS matches, (SELECT COUNT(*) FROM venues) AS venues"
    ).iloc[0]
    cols = st.columns(4)
    for col, (label, value) in zip(cols, counts.items()):
        col.metric(label.capitalize(), f"{int(value):,}")
except DatabaseError as exc:
    st.warning(f"Could not read database statistics: {exc}")

st.divider()

# ---- navigation ---------------------------------------------------------
st.markdown("### 📌 Pages")
left, right = st.columns(2)
with left:
    st.page_link("pages/live_matches.py", label="Live Matches", icon="⚡")
    st.caption("Ongoing / recent / upcoming matches with full scorecards from the Cricbuzz API.")
    st.page_link("pages/top_stats.py", label="Top Player Stats", icon="🏆")
    st.caption("Most runs, highest score, most wickets, rankings - via API and the database.")
    st.page_link("pages/sql_queries.py", label="SQL Queries & Analytics", icon="🔍")
    st.caption("25 SQL questions (beginner → advanced) plus a read-only custom query box.")
with right:
    st.page_link("pages/crud_operations.py", label="CRUD Operations", icon="🛠️")
    st.caption("Create, read, update and delete players, matches, venues and more.")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🧰 Tools used")
    st.markdown(
        "- **Python** - application logic\n"
        "- **Streamlit** - multi-page web UI\n"
        "- **SQL** (SQLite / PostgreSQL / MySQL via SQLAlchemy)\n"
        "- **requests** - Cricbuzz REST API (RapidAPI)\n"
        "- **pandas / Plotly** - data handling and charts"
    )
    st.markdown("### 🚀 How to use")
    st.markdown(
        "1. Add `RAPIDAPI_KEY` to `.env` to enable live data (optional).\n"
        "2. Browse **Live Matches** and **Top Player Stats**.\n"
        "3. Explore the 25 queries on **SQL Queries & Analytics**.\n"
        "4. Manage records on **CRUD Operations**."
    )
with c2:
    st.markdown("### 🗂️ Folder structure")
    st.code(
        """cricbuzz_livestats/
├── app.py / main.py        # Streamlit entry point
├── requirements.txt
├── README.md               # setup + documentation
├── pages/                  # home, live_matches, top_stats,
│                           # sql_queries, crud_operations
├── utils/                  # db_connection, api_client,
│                           # api_to_db, crud, config
├── database/               # schema.sql, seed_sample_data, init_db
├── sql/queries.py          # the 25 SQL questions
├── notebooks/              # data_fetching.ipynb
└── tests/                  # pytest suite""",
        language="text",
    )
    st.link_button("📖 Cricbuzz API on RapidAPI", "https://rapidapi.com/cricketapilive/api/cricbuzz-cricket")

st.info(
    "ℹ️ The bundled database holds **synthetic sample statistics** so every feature works offline. "
    "Live pages use real Cricbuzz data when an API key is configured."
)
