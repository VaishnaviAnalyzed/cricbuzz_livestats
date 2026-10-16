"""Generate a reproducible SAMPLE dataset so every module works offline.

NOTE: Player names are real, but ALL statistics, matches and venues' capacities
here are synthetic/approximate and exist only for learning and demos.
Live data comes from the Cricbuzz API (see utils/api_client.py).
"""
from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

FORMATS = ["Test", "ODI", "T20I"]

# Squad order = batting order. idx 0-3 Batsman, 4 Wicket-keeper, 5-6 All-rounder, 7-10 Bowler
ROLES = ["Batsman"] * 4 + ["Wicket-keeper"] + ["All-rounder"] * 2 + ["Bowler"] * 4

SQUADS: dict[str, list[str]] = {
    "India": ["Rohit Sharma", "Shubman Gill", "Virat Kohli", "Shreyas Iyer", "Rishabh Pant",
              "Hardik Pandya", "Ravindra Jadeja", "Kuldeep Yadav", "Mohammed Shami",
              "Jasprit Bumrah", "Mohammed Siraj"],
    "Australia": ["Travis Head", "Marnus Labuschagne", "Steve Smith", "Usman Khawaja", "Alex Carey",
                  "Glenn Maxwell", "Mitchell Marsh", "Pat Cummins", "Mitchell Starc",
                  "Josh Hazlewood", "Adam Zampa"],
    "England": ["Zak Crawley", "Joe Root", "Harry Brook", "Ben Duckett", "Jos Buttler",
                "Ben Stokes", "Moeen Ali", "Jofra Archer", "Mark Wood", "Adil Rashid",
                "Brydon Carse"],
    "Pakistan": ["Babar Azam", "Fakhar Zaman", "Imam-ul-Haq", "Saud Shakeel", "Mohammad Rizwan",
                 "Shadab Khan", "Faheem Ashraf", "Shaheen Afridi", "Naseem Shah", "Haris Rauf",
                 "Abrar Ahmed"],
    "South Africa": ["Temba Bavuma", "Aiden Markram", "Rassie van der Dussen", "Heinrich Klaasen",
                     "Quinton de Kock", "Marco Jansen", "Wiaan Mulder", "Kagiso Rabada",
                     "Anrich Nortje", "Keshav Maharaj", "Lungi Ngidi"],
    "New Zealand": ["Kane Williamson", "Devon Conway", "Daryl Mitchell", "Tom Latham",
                    "Tom Blundell", "Rachin Ravindra", "Mitchell Santner", "Trent Boult",
                    "Tim Southee", "Matt Henry", "Lockie Ferguson"],
    "Sri Lanka": ["Pathum Nissanka", "Charith Asalanka", "Dinesh Chandimal",
                  "Sadeera Samarawickrama", "Kusal Mendis", "Wanindu Hasaranga",
                  "Dhananjaya de Silva", "Maheesh Theekshana", "Dilshan Madushanka",
                  "Matheesha Pathirana", "Asitha Fernando"],
    "Bangladesh": ["Tamim Iqbal", "Najmul Hossain Shanto", "Towhid Hridoy", "Mahmudullah",
                   "Mushfiqur Rahim", "Shakib Al Hasan", "Mehidy Hasan Miraz",
                   "Mustafizur Rahman", "Taskin Ahmed", "Shoriful Islam", "Taijul Islam"],
}
SHORT = {"India": "IND", "Australia": "AUS", "England": "ENG", "Pakistan": "PAK",
         "South Africa": "SA", "New Zealand": "NZ", "Sri Lanka": "SL", "Bangladesh": "BAN"}

# (venue_name, city, country, approx capacity)
VENUES = [
    ("Wankhede Stadium", "Mumbai", "India", 33108),
    ("Eden Gardens", "Kolkata", "India", 66000),
    ("Narendra Modi Stadium", "Ahmedabad", "India", 132000),
    ("Melbourne Cricket Ground", "Melbourne", "Australia", 100024),
    ("Sydney Cricket Ground", "Sydney", "Australia", 48000),
    ("Lord's", "London", "England", 31100),
    ("The Oval", "London", "England", 27500),
    ("Gaddafi Stadium", "Lahore", "Pakistan", 34000),
    ("National Stadium", "Karachi", "Pakistan", 34228),
    ("Newlands", "Cape Town", "South Africa", 25000),
    ("The Wanderers", "Johannesburg", "South Africa", 34000),
    ("Eden Park", "Auckland", "New Zealand", 50000),
    ("R. Premadasa Stadium", "Colombo", "Sri Lanka", 35000),
    ("Shere Bangla Stadium", "Dhaka", "Bangladesh", 26000),
]

BAT_MEAN = [38, 36, 40, 34, 32, 30, 26, 18, 9, 6, 4]       # by batting position
RUN_FACTOR = {"Test": 1.15, "ODI": 1.0, "T20I": 0.62}
SR_BASE = {"Test": 52, "ODI": 88, "T20I": 135}
ECON_BASE = {"Test": 3.1, "ODI": 5.3, "T20I": 8.2}
BOWL_STYLES = ["Right-arm fast", "Left-arm fast", "Right-arm offbreak", "Legbreak",
               "Left-arm orthodox", "Right-arm medium"]


def _bulk(conn, table: str, rows: list[dict[str, Any]]) -> None:
    """Bulk insert helper (one executemany)."""
    if rows:
        cols = list(rows[0])
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
        conn.execute(text(sql), rows)


def seed_sample_data(engine: Engine, n_matches: int = 420, seed_value: int = 42) -> dict[str, int]:
    """Populate every table with sample data. Returns row counts."""
    rnd = random.Random(seed_value)
    today = date.today()
    start = date(2022, 1, 1)

    # ---------------- teams / venues / players ----------------
    teams = [{"team_id": i + 1, "team_name": n, "country": n, "short_name": SHORT[n]}
             for i, n in enumerate(SQUADS)]
    team_id = {t["team_name"]: t["team_id"] for t in teams}
    venues = [{"venue_id": i + 1, "venue_name": v[0], "city": v[1], "country": v[2],
               "capacity": v[3]} for i, v in enumerate(VENUES)]
    home_venues: dict[str, list[int]] = defaultdict(list)
    for v in venues:
        home_venues[v["country"]].append(v["venue_id"])

    players, meta = [], {}
    pid = 0
    for team, names in SQUADS.items():
        for idx, name in enumerate(names):
            pid += 1
            role = ROLES[idx]
            bowl = None if role in ("Batsman", "Wicket-keeper") and rnd.random() < 0.8 \
                else rnd.choice(BOWL_STYLES)
            players.append({
                "player_id": pid, "full_name": name, "country": team, "playing_role": role,
                "batting_style": rnd.choice(["Right-hand bat", "Left-hand bat"]),
                "bowling_style": bowl})
            meta[pid] = {"team": team, "idx": idx,
                         "base": rnd.uniform(0.85, 1.15), "slope": rnd.uniform(-0.10, 0.10)}
    squad_ids = {t: [p["player_id"] for p in players if p["country"] == t] for t in SQUADS}
    strength = {t: rnd.uniform(1.0, 1.45) for t in SQUADS}
    qfactor: dict[tuple, float] = {}

    def form(player_id: int, d: date) -> float:
        key = (player_id, d.year, (d.month - 1) // 3)
        if key not in qfactor:
            m = meta[player_id]
            trend = max(0.4, m["base"] * (1 + m["slope"] * (d.year - 2022)))
            qfactor[key] = trend * rnd.uniform(0.8, 1.2)
        return qfactor[key]

    # ---------------- series ----------------
    series: list[dict[str, Any]] = []
    for fmt in FORMATS:
        series.append({"match_type": fmt, "start": start, "host": "India"})
    for year in range(2022, today.year + 1):
        for k in range(6):
            s = date(year, rnd.randint(1, 12), rnd.randint(1, 28))
            if s > today:
                s = today - timedelta(days=rnd.randint(30, 150))
            series.append({"match_type": rnd.choice(FORMATS), "start": s,
                           "host": rnd.choice(list(SQUADS))})
    for i, s in enumerate(series, start=1):
        s["series_id"] = i
        s["name"] = f"{s['host']} {s['match_type']} Series {s['start'].year} #{i}"
        s["count"] = 0

    # ---------------- matches + performances ----------------
    dates = sorted(start + timedelta(days=rnd.randint(0, (today - start).days))
                   for _ in range(n_matches))
    matches, bat, bowl, field = [], [], [], []
    ids = {"bat": 0, "bowl": 0, "field": 0}
    for mid, d in enumerate(dates, start=1):
        fmt = rnd.choices(FORMATS, weights=[25, 35, 40])[0]
        t1, t2 = rnd.sample(list(SQUADS), 2)
        venue = rnd.choice(home_venues[t1]) if rnd.random() < 0.65 else rnd.choice(venues)["venue_id"]
        cands = [s for s in series if s["match_type"] == fmt and s["start"] <= d]
        ser = max(cands, key=lambda s: s["start"])
        ser["count"] += 1

        toss_winner = rnd.choice([t1, t2])
        decision = "bowl" if rnd.random() < 0.6 else "bat"
        first = toss_winner if decision == "bat" else (t2 if toss_winner == t1 else t1)
        second = t2 if first == t1 else t1

        p1 = strength[t1] / (strength[t1] + strength[t2])
        draw = fmt == "Test" and rnd.random() < 0.15
        winner = None if draw else (t1 if rnd.random() < p1 else t2)
        if draw:
            vtype, margin = "draw", None
        elif winner == first:
            vtype, margin = "runs", rnd.randint(1, 60 if fmt == "T20I" else 150)
        else:
            vtype, margin = "wickets", rnd.randint(1, 9)

        matches.append({
            "match_id": mid, "series_id": ser["series_id"],
            "description": f"{t1} vs {t2} - {fmt}", "match_format": fmt,
            "team1_id": team_id[t1], "team2_id": team_id[t2], "venue_id": venue,
            "match_date": d.isoformat(), "status": "Complete",
            "winner_team_id": team_id[winner] if winner else None,
            "victory_margin": margin, "victory_type": vtype,
            "toss_winner_id": team_id[toss_winner], "toss_decision": decision})

        for inn, (bat_team, bowl_team) in enumerate([(first, second), (second, first)], start=1):
            win_boost = 1.1 if bat_team == winner else 1.0
            for pos, p in enumerate(squad_ids[bat_team], start=1):
                mean = BAT_MEAN[pos - 1] * RUN_FACTOR[fmt] * form(p, d) * win_boost
                runs = min(int(rnd.expovariate(1 / max(mean, 1))), 250)
                balls = rnd.randint(1, 10) if runs == 0 else \
                    max(1, round(runs * 100 / (SR_BASE[fmt] * rnd.uniform(0.7, 1.3))))
                ids["bat"] += 1
                bat.append({
                    "perf_id": ids["bat"], "match_id": mid, "player_id": p,
                    "team_id": team_id[bat_team], "innings_no": inn, "batting_position": pos,
                    "runs": runs, "balls": balls,
                    "fours": int(runs * rnd.uniform(0.35, 0.55) / 4),
                    "sixes": int(runs * rnd.uniform(0.0, 0.3) / 6),
                    "strike_rate": round(runs * 100 / balls, 2),
                    "is_out": 1 if rnd.random() < 0.85 else 0})

            # bowling for the fielding side
            attack = rnd.sample(squad_ids[bowl_team][5:], 5)
            wk_split = {p: 0 for p in attack}
            for _ in range(rnd.randint(4, 10)):
                wk_split[rnd.choices(attack, weights=[1, 1, 1.2, 1.2, 1.2])[0]] += 1
            for p in attack:
                overs = {"T20I": rnd.randint(2, 4), "ODI": rnd.randint(4, 10),
                         "Test": rnd.randint(8, 26)}[fmt]
                conceded = max(1, int(overs * ECON_BASE[fmt] * rnd.uniform(0.6, 1.5)))
                ids["bowl"] += 1
                bowl.append({
                    "perf_id": ids["bowl"], "match_id": mid, "player_id": p,
                    "team_id": team_id[bowl_team], "innings_no": inn, "overs": float(overs),
                    "maidens": 0 if fmt == "T20I" else rnd.randint(0, 2),
                    "runs_conceded": conceded, "wickets": min(wk_split[p], 10),
                    "economy": round(conceded / overs, 2)})

        # fielding: catches / stumpings for both sides, aggregated per player
        tally: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        for side in (t1, t2):
            for _ in range(rnd.randint(3, 8)):
                if rnd.random() < 0.08:
                    tally[squad_ids[side][4]][1] += 1
                else:
                    tally[rnd.choice(squad_ids[side])][0] += 1
        for p, (c, s) in tally.items():
            ids["field"] += 1
            field.append({"perf_id": ids["field"], "match_id": mid, "player_id": p,
                          "catches": c, "stumpings": s})

    series_rows = [{
        "series_id": s["series_id"], "series_name": s["name"], "host_country": s["host"],
        "match_type": s["match_type"], "start_date": s["start"].isoformat(),
        "end_date": (s["start"] + timedelta(days=30)).isoformat(),
        "total_matches": max(s["count"], 3)} for s in series]

    # ---------------- career stats ----------------
    career, sid = [], 0
    for p in players:
        idx = meta[p["player_id"]]["idx"]
        fmts = ["ODI", "T20I"] + (["Test"] if rnd.random() < 0.6 else [])
        for fmt in fmts:
            sid += 1
            n = {"Test": rnd.randint(15, 140), "ODI": rnd.randint(30, 300),
                 "T20I": rnd.randint(20, 150)}[fmt]
            innings = int(n * (0.95 if idx <= 6 else 0.6))
            mean = [40, 40, 42, 38, 34, 30, 27, 12, 10, 8, 6][idx]
            avg = mean * rnd.uniform(0.8, 1.2) * {"Test": 1.0, "ODI": 1.05, "T20I": 0.6}[fmt]
            runs = int(innings * avg)
            sr = SR_BASE[fmt] * rnd.uniform(0.85, 1.15)
            wk_rate = {5: 0.5, 6: 0.9}.get(idx, 1.5 if idx >= 7 else 0.0) * (1.6 if fmt == "Test" else 1)
            wickets = int(n * wk_rate * rnd.uniform(0.7, 1.2))
            hs_cap = {"Test": 380, "ODI": 264, "T20I": 175}[fmt]
            career.append({
                "stat_id": sid, "player_id": p["player_id"], "format": fmt, "matches": n,
                "innings": innings, "runs": runs, "balls_faced": int(runs * 100 / sr),
                "batting_avg": round(avg, 2), "strike_rate": round(sr, 2),
                "highest_score": min(hs_cap, int(avg * rnd.uniform(2.5, 5))),
                "centuries": runs // {"Test": 700, "ODI": 600, "T20I": 2500}[fmt],
                "fifties": runs // 200, "wickets": wickets,
                "bowling_avg": round({"Test": 28, "ODI": 32, "T20I": 24}[fmt] * rnd.uniform(0.8, 1.2), 2)
                if wickets else None,
                "economy": round(ECON_BASE[fmt] * rnd.uniform(0.85, 1.15), 2) if wickets else None,
                "catches": int(n * rnd.uniform(0.2, 0.9)),
                "stumpings": int(n * rnd.uniform(0.2, 0.5)) if idx == 4 else 0})

    with engine.begin() as conn:
        _bulk(conn, "teams", teams)
        _bulk(conn, "venues", venues)
        _bulk(conn, "players", players)
        _bulk(conn, "series", series_rows)
        _bulk(conn, "matches", matches)
        _bulk(conn, "batting_performances", bat)
        _bulk(conn, "bowling_performances", bowl)
        _bulk(conn, "fielding_performances", field)
        _bulk(conn, "player_career_stats", career)

    return {"teams": len(teams), "venues": len(venues), "players": len(players),
            "series": len(series_rows), "matches": len(matches), "batting": len(bat),
            "bowling": len(bowl), "fielding": len(field), "career": len(career)}
