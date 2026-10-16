"""Cricbuzz Cricket API client (RapidAPI) + response parsers.

* Uses ``requests`` with a retry/backoff strategy for 429 / 5xx / network errors.
* Parsers are defensive (``.get`` everywhere) because Cricbuzz payloads vary by match state.
* Endpoint paths follow the RapidAPI "cricbuzz-cricket" documentation; if a path
  changes, update it in one place here.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import requests

from utils.config import get_settings

logger = logging.getLogger(__name__)

TOPSTATS_TYPES = {
    "Most runs": "mostRuns", "Highest score": "highestScore", "Highest average": "highestAvg",
    "Highest strike rate": "highestSr", "Most hundreds": "mostHundreds",
    "Most fifties": "mostFifties", "Most fours": "mostFours", "Most sixes": "mostSixes",
    "Most wickets": "mostWickets", "Best bowling innings": "bestBowlingInnings",
    "Most five-wicket hauls": "mostFiveWickets", "Lowest economy": "lowestEcon",
    "Lowest average": "lowestAvg",
}


class CricbuzzAPIError(Exception):
    """Raised when the Cricbuzz API cannot return usable data."""


class CricbuzzClient:
    """Thin wrapper around the Cricbuzz REST endpoints."""

    def __init__(self, api_key: str | None = None, host: str | None = None,
                 timeout: int = 15, max_retries: int = 3, backoff: float = 1.5) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.rapidapi_key
        self.host = host or settings.rapidapi_host
        self.base_url = f"https://{self.host}"
        self.timeout, self.max_retries, self.backoff = timeout, max_retries, backoff
        self.session = requests.Session()

    @property
    def configured(self) -> bool:
        """True when an API key is available."""
        return bool(self.api_key)

    # ------------------------------------------------------------ core request
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET ``path`` and return parsed JSON, retrying transient failures."""
        if not self.configured:
            raise CricbuzzAPIError("RAPIDAPI_KEY is not configured. Add it to .env or Streamlit secrets.")
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.host}
        last_error = "unknown error"
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(f"{self.base_url}{path}", headers=headers,
                                        params=params, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = f"network error: {exc.__class__.__name__}"
            else:
                if resp.status_code in (401, 403):
                    raise CricbuzzAPIError("API key rejected (401/403). Check your RapidAPI subscription.")
                if resp.status_code == 404:
                    raise CricbuzzAPIError(f"Endpoint or resource not found: {path}")
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code} (rate limit / server error)"
                elif resp.ok:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        raise CricbuzzAPIError("API returned invalid JSON.") from exc
                else:
                    raise CricbuzzAPIError(f"Unexpected HTTP {resp.status_code}: {resp.text[:150]}")
            logger.warning("Cricbuzz request %s failed (%s), attempt %d/%d",
                           path, last_error, attempt, self.max_retries)
            if attempt < self.max_retries:
                time.sleep(self.backoff ** attempt)
        raise CricbuzzAPIError(f"Request failed after {self.max_retries} attempts: {last_error}")

    # ------------------------------------------------------------ endpoints
    def matches(self, kind: str = "live") -> dict[str, Any]:
        """kind: live | recent | upcoming."""
        if kind not in ("live", "recent", "upcoming"):
            raise ValueError("kind must be live, recent or upcoming")
        return self._get(f"/matches/v1/{kind}")

    def match_info(self, match_id: int) -> dict[str, Any]:
        return self._get(f"/mcenter/v1/{match_id}")

    def scorecard(self, match_id: int) -> dict[str, Any]:
        return self._get(f"/mcenter/v1/{match_id}/scard")

    def top_stats(self, stats_type: str = "mostRuns") -> dict[str, Any]:
        return self._get("/stats/v1/topstats/0", {"statsType": stats_type})

    def rankings(self, category: str = "batsmen", format_type: str = "odi") -> dict[str, Any]:
        """category: batsmen | bowlers | allrounders | teams; format_type: test | odi | t20."""
        return self._get(f"/stats/v1/rankings/{category}", {"formatType": format_type})

    def international_teams(self) -> dict[str, Any]:
        return self._get("/teams/v1/international")

    def team_players(self, team_id: int) -> dict[str, Any]:
        return self._get(f"/teams/v1/{team_id}/players")

    def series_list(self, kind: str = "international") -> dict[str, Any]:
        return self._get(f"/series/v1/{kind}")

    def player_search(self, name: str) -> dict[str, Any]:
        return self._get("/stats/v1/player/search", {"plrN": name})

    def player_info(self, player_id: int) -> dict[str, Any]:
        return self._get(f"/stats/v1/player/{player_id}")

    def player_batting(self, player_id: int) -> dict[str, Any]:
        return self._get(f"/stats/v1/player/{player_id}/batting")

    def player_bowling(self, player_id: int) -> dict[str, Any]:
        return self._get(f"/stats/v1/player/{player_id}/bowling")


# ====================================================================== parsers
def _fmt_score(team_score: dict[str, Any] | None) -> str:
    """Turn {'inngs1': {'runs': 210, 'wickets': 3, 'overs': 45.2}} into '210/3 (45.2 ov)'."""
    if not team_score:
        return "-"
    parts = []
    for key in sorted(k for k in team_score if k.startswith("inngs")):
        inn = team_score[key]
        runs, wkts, overs = inn.get("runs"), inn.get("wickets"), inn.get("overs")
        text = f"{runs}" if wkts is None else f"{runs}/{wkts}"
        if overs is not None:
            text += f" ({overs} ov)"
        parts.append(text)
    return " & ".join(parts) or "-"


def flatten_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the nested typeMatches -> seriesMatches -> matches structure."""
    rows: list[dict[str, Any]] = []
    for type_block in payload.get("typeMatches", []):
        for series_block in type_block.get("seriesMatches", []):
            wrapper = series_block.get("seriesAdWrapper")
            if not wrapper:
                continue
            for match in wrapper.get("matches", []):
                info, score = match.get("matchInfo", {}), match.get("matchScore", {})
                t1, t2, venue = info.get("team1", {}), info.get("team2", {}), info.get("venueInfo", {})
                rows.append({
                    "match_id": info.get("matchId"),
                    "series_id": info.get("seriesId"),
                    "series": info.get("seriesName") or wrapper.get("seriesName"),
                    "description": info.get("matchDesc"),
                    "format": info.get("matchFormat"),
                    "state": info.get("state"),
                    "status": info.get("status"),
                    "team1": t1.get("teamName"), "team1_id": t1.get("teamId"),
                    "team1_short": t1.get("teamSName"),
                    "team2": t2.get("teamName"), "team2_id": t2.get("teamId"),
                    "team2_short": t2.get("teamSName"),
                    "team1_score": _fmt_score(score.get("team1Score")),
                    "team2_score": _fmt_score(score.get("team2Score")),
                    "venue": venue.get("ground"), "city": venue.get("city"),
                    "venue_id": venue.get("id"),
                    "start_ms": info.get("startDate"),
                })
    return rows


def parse_scorecard(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of innings dicts: title, batting DataFrame, bowling DataFrame."""
    innings = []
    for inn in payload.get("scoreCard", []):
        bat = inn.get("batTeamDetails", {})
        bowl = inn.get("bowlTeamDetails", {})
        score = inn.get("scoreDetails", {})
        batters = [{
            "Batter": b.get("batName"), "Dismissal": b.get("outDesc") or "not out",
            "Runs": b.get("runs"), "Balls": b.get("balls"), "4s": b.get("fours"),
            "6s": b.get("sixes"), "SR": b.get("strikeRate"),
        } for b in (bat.get("batsmenData") or {}).values()]
        bowlers = [{
            "Bowler": b.get("bowlName"), "Overs": b.get("overs"), "Maidens": b.get("maidens"),
            "Runs": b.get("runs"), "Wickets": b.get("wickets"), "Economy": b.get("economy"),
        } for b in (bowl.get("bowlersData") or {}).values()]
        title = f"{bat.get('batTeamName', 'Team')} - {score.get('runs', '?')}/{score.get('wickets', '?')} " \
                f"({score.get('overs', '?')} ov)"
        innings.append({"title": title, "batting": pd.DataFrame(batters),
                        "bowling": pd.DataFrame(bowlers)})
    return innings


def parse_topstats(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert a topstats payload (headers + values) into a DataFrame."""
    headers = payload.get("headers") or []
    rows = []
    for item in payload.get("values", []):
        rows.append(item.get("values") if isinstance(item, dict) else item)
    if headers and rows and len(headers) == len(rows[0]):
        return pd.DataFrame(rows, columns=headers)
    return pd.DataFrame(rows)


def parse_rankings(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert a rankings payload into a tidy DataFrame."""
    df = pd.DataFrame(payload.get("rank", []))
    keep = [c for c in ("rank", "name", "country", "rating", "points", "avg", "lastUpdatedOn") if c in df]
    return df[keep] if keep else df
