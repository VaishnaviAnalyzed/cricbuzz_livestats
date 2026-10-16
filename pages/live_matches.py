"""Live Matches page: matches + detailed scorecards from the Cricbuzz API."""
import plotly.express as px
import streamlit as st

from utils.api_client import (CricbuzzAPIError, CricbuzzClient, flatten_matches,
                              parse_scorecard)
from utils.api_to_db import save_matches
from utils.db_connection import DatabaseError, run_query

st.title("⚡ Live Matches")


@st.cache_data(ttl=30, show_spinner="Fetching matches from Cricbuzz...")
def load_matches(kind: str) -> list[dict]:
    """Fetch + flatten a match list (cached 30s to respect API rate limits)."""
    return flatten_matches(CricbuzzClient().matches(kind))


@st.cache_data(ttl=30, show_spinner="Fetching scorecard...")
def load_scorecard(match_id: int) -> dict:
    """Fetch the raw scorecard payload for one match."""
    return CricbuzzClient().scorecard(match_id)


client = CricbuzzClient()

# ------------------------------------------------------------------ fallback
if not client.configured:
    st.warning(
        "No `RAPIDAPI_KEY` found, so live data is unavailable. Add it to `.env` "
        "(see README) to enable this page. Showing recent matches from the database instead."
    )
    try:
        df = run_query("SELECT match_date, description, venue_name, city, winner, victory_margin, "
                       "victory_type FROM v_match_results ORDER BY match_date DESC LIMIT 25")
        st.dataframe(df, use_container_width=True, hide_index=True)
    except DatabaseError as exc:
        st.error(f"Database error: {exc}")
    st.stop()

# ------------------------------------------------------------------ controls
top = st.columns([3, 1])
kind = top[0].radio("Match type", ["live", "recent", "upcoming"], horizontal=True,
                    format_func=str.capitalize)
if top[1].button("🔄 Refresh", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

try:
    matches = load_matches(kind)
except CricbuzzAPIError as exc:
    st.error(f"Cricbuzz API error: {exc}")
    st.stop()

if not matches:
    st.info(f"No {kind} matches right now.")
    st.stop()

# ------------------------------------------------------------------ list
labels = {m["match_id"]: f"{m['team1']} vs {m['team2']} · {m['description']} · {m['series']}"
          for m in matches}
match_id = st.selectbox("Select a match", list(labels), format_func=labels.get)
match = next(m for m in matches if m["match_id"] == match_id)

st.subheader(f"{match['team1']} vs {match['team2']}")
st.caption(f"{match['series']} · {match['description']} · {match['format']}")
c1, c2 = st.columns(2)
c1.metric(match["team1_short"] or match["team1"], match["team1_score"])
c2.metric(match["team2_short"] or match["team2"], match["team2_score"])
st.success(match["status"] or match["state"] or "Status not available")
st.write(f"📍 **Venue:** {match['venue'] or 'N/A'}, {match['city'] or ''}")

with st.expander("All matches in this list"):
    st.dataframe(
        [{k: m[k] for k in ("series", "description", "team1", "team1_score", "team2",
                            "team2_score", "status")} for m in matches],
        use_container_width=True, hide_index=True)

if st.button("💾 Save these matches to the database"):
    try:
        saved, skipped = save_matches(matches)
        st.success(f"Saved/updated {saved} matches ({skipped} skipped: non-international or incomplete).")
    except DatabaseError as exc:
        st.error(f"Could not save: {exc}")

# ------------------------------------------------------------------ scorecard
st.divider()
st.markdown("### 📋 Scorecard")
try:
    innings = parse_scorecard(load_scorecard(int(match_id)))
except CricbuzzAPIError as exc:
    st.info(f"Scorecard not available for this match yet ({exc}).")
    st.stop()

if not innings:
    st.info("Scorecard not available yet (match may not have started).")
for inn in innings:
    with st.expander(inn["title"], expanded=True):
        if not inn["batting"].empty:
            st.markdown("**Batting**")
            st.dataframe(inn["batting"], use_container_width=True, hide_index=True)
            chart_df = inn["batting"].dropna(subset=["Runs"])
            if not chart_df.empty:
                fig = px.bar(chart_df, x="Batter", y="Runs", title="Runs by batter")
                st.plotly_chart(fig, use_container_width=True)
        if not inn["bowling"].empty:
            st.markdown("**Bowling**")
            st.dataframe(inn["bowling"], use_container_width=True, hide_index=True)
