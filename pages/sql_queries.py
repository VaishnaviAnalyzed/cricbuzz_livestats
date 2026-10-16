"""SQL Queries & Analytics page: the 25 practice queries + a read-only custom query box."""
import pandas as pd
import plotly.express as px
import streamlit as st

from sql.queries import QUERIES
from utils.db_connection import DatabaseError, run_query, safe_select

st.title("🔍 SQL Queries & Analytics")
st.caption("25 queries on the player & match database - from basic SELECTs to window functions and CTEs.")

tab_prepared, tab_custom = st.tabs(["📚 25 practice queries", "✍️ Custom SQL"])


def show_result(df: pd.DataFrame, key: str) -> None:
    """Render a result table, a CSV download and an optional bar chart."""
    st.success(f"{len(df):,} row(s) returned")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if df.empty:
        return
    st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(), f"{key}.csv", "text/csv",
                       key=f"dl_{key}")
    text_cols = [c for c in df.columns if df[c].dtype == "object"]
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if text_cols and num_cols and len(df) <= 60:
        with st.expander("📊 Quick chart"):
            x = st.selectbox("Category (x)", text_cols, key=f"x_{key}")
            y = st.selectbox("Value (y)", num_cols, key=f"y_{key}")
            st.plotly_chart(px.bar(df.head(30), x=x, y=y), use_container_width=True)


with tab_prepared:
    level = st.radio("Difficulty", ["All", "Beginner", "Intermediate", "Advanced"], horizontal=True)
    pool = [q for q in QUERIES if level in ("All", q["level"])]
    selected = st.selectbox("Question", pool, format_func=lambda q: f"Q{q['id']:02d} · [{q['level']}] {q['title']}")

    st.markdown(f"**Question {selected['id']}:** {selected['question']}")
    st.code(selected["sql"].strip(), language="sql")

    if st.button("▶️ Run query", type="primary", key="run_prepared"):
        try:
            show_result(run_query(selected["sql"]), f"q{selected['id']}")
        except DatabaseError as exc:
            st.error(f"Query failed: {exc}")

    if "extra_sql" in selected:
        st.markdown(f"**{selected['extra_title']}**")
        st.code(selected["extra_sql"].strip(), language="sql")
        if st.button("▶️ Run extra query", key="run_extra"):
            try:
                show_result(run_query(selected["extra_sql"]), f"q{selected['id']}b")
            except DatabaseError as exc:
                st.error(f"Query failed: {exc}")

with tab_custom:
    st.write("Write your own **read-only** query (SELECT / WITH). Tables: `players`, `teams`, `venues`, "
             "`series`, `matches`, `batting_performances`, `bowling_performances`, "
             "`fielding_performances`, `player_career_stats` + views `v_match_results`, `v_player_overview`.")
    sql = st.text_area("SQL", "SELECT * FROM v_match_results ORDER BY match_date DESC LIMIT 10;", height=160)
    if st.button("▶️ Run custom query", key="run_custom"):
        try:
            show_result(run_query(safe_select(sql)), "custom")
        except DatabaseError as exc:
            st.error(f"Query rejected/failed: {exc}")
    with st.expander("Schema reference"):
        try:
            tables = run_query("SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
            st.write(", ".join(tables["name"]))
        except DatabaseError:
            st.caption("Schema listing is only available on SQLite; see database/schema.sql.")
