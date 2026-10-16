"""Top Player Stats page: API leaderboards, ICC rankings and database leaders."""
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.api_client import (TOPSTATS_TYPES, CricbuzzAPIError, CricbuzzClient,
                              parse_rankings, parse_topstats)
from utils.db_connection import DatabaseError, run_query

st.title("🏆 Top Player Stats")

tab_api, tab_rank, tab_db = st.tabs(["🌐 API top stats", "📈 ICC rankings", "🗄️ Database leaders"])
client = CricbuzzClient()


@st.cache_data(ttl=600, show_spinner="Loading from Cricbuzz...")
def load_topstats(stats_type: str):
    return parse_topstats(CricbuzzClient().top_stats(stats_type))


@st.cache_data(ttl=600, show_spinner="Loading rankings...")
def load_rankings(category: str, fmt: str):
    return parse_rankings(CricbuzzClient().rankings(category, fmt))


# ------------------------------------------------------------------ API stats
with tab_api:
    if not client.configured:
        st.info("Add `RAPIDAPI_KEY` to enable live leaderboards. The **Database leaders** tab works offline.")
    else:
        label = st.selectbox("Statistic", list(TOPSTATS_TYPES))
        try:
            df = load_topstats(TOPSTATS_TYPES[label])
            if df.empty:
                st.warning("The API returned no rows for this statistic.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                numeric = [c for c in df.columns if pd.to_numeric(df[c], errors="coerce").notna().all()]
                name_col = next((c for c in df.columns if "player" in str(c).lower()), df.columns[1] if df.shape[1] > 1 else df.columns[0])
                if numeric:
                    plot_df = df.head(10).copy()
                    ycol = numeric[-1]
                    plot_df[ycol] = pd.to_numeric(plot_df[ycol])
                    st.plotly_chart(px.bar(plot_df, x=ycol, y=name_col, orientation="h",
                                           title=f"{label} (top 10)").update_yaxes(autorange="reversed"),
                                    use_container_width=True)
        except CricbuzzAPIError as exc:
            st.error(f"Cricbuzz API error: {exc}")

# ------------------------------------------------------------------ rankings
with tab_rank:
    if not client.configured:
        st.info("Add `RAPIDAPI_KEY` to enable live ICC rankings.")
    else:
        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", ["batsmen", "bowlers", "allrounders", "teams"])
        fmt = c2.selectbox("Format", ["test", "odi", "t20"])
        try:
            st.dataframe(load_rankings(category, fmt), use_container_width=True, hide_index=True)
        except CricbuzzAPIError as exc:
            st.error(f"Cricbuzz API error: {exc}")

# ------------------------------------------------------------------ database
DB_CATEGORIES = {
    "Most runs": ("c.runs", "DESC", "1=1", "Runs"),
    "Highest score": ("c.highest_score", "DESC", "1=1", "Highest score"),
    "Best batting average (min 20 matches)": ("c.batting_avg", "DESC", "c.matches >= 20", "Average"),
    "Highest strike rate (min 20 matches)": ("c.strike_rate", "DESC", "c.matches >= 20", "Strike rate"),
    "Most centuries": ("c.centuries", "DESC", "1=1", "Centuries"),
    "Most wickets": ("c.wickets", "DESC", "1=1", "Wickets"),
    "Best economy (min 30 wickets)": ("c.economy", "ASC", "c.wickets >= 30", "Economy"),
    "Most catches": ("c.catches", "DESC", "1=1", "Catches"),
}

with tab_db:
    c1, c2, c3 = st.columns(3)
    fmt_db = c1.selectbox("Format", ["ODI", "T20I", "Test"], key="db_fmt")
    cat = c2.selectbox("Category", list(DB_CATEGORIES), key="db_cat")
    n = c3.slider("Rows", 5, 25, 10)
    metric, direction, cond, axis_label = DB_CATEGORIES[cat]
    try:
        df = run_query(
            f"SELECT p.full_name AS player, p.country AS team, c.matches, {metric} AS value "
            f"FROM player_career_stats c JOIN players p ON p.player_id = c.player_id "
            f"WHERE c.format = :fmt AND {cond} AND {metric} IS NOT NULL "
            f"ORDER BY {metric} {direction} LIMIT {int(n)}", {"fmt": fmt_db})
        df = df.rename(columns={"value": axis_label})
        st.dataframe(df, use_container_width=True, hide_index=True)
        fig = px.bar(df, x=axis_label, y="player", color="team", orientation="h",
                     title=f"{cat} - {fmt_db}")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    except DatabaseError as exc:
        st.error(f"Database error: {exc}")
