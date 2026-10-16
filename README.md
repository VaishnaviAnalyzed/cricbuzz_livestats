# 🏏 Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics

A multi-page **Streamlit** dashboard that combines live data from the **Cricbuzz API** (REST, via RapidAPI) with a **SQL database** (SQLite by default; PostgreSQL / MySQL supported).

| Page | What it does |
|---|---|
| **Home** | Project overview, tools, instructions, folder structure, DB snapshot |
| **Live Matches** | Live / recent / upcoming matches, scorecards (batting + bowling), save matches to DB |
| **Top Player Stats** | API leaderboards (most runs, wickets...), ICC rankings, database leaders with charts |
| **SQL Queries & Analytics** | The 25 SQL questions (Beginner → Advanced) + read-only custom SQL, CSV download, quick chart |
| **CRUD Operations** | Create / Read / Update / Delete for players, career stats, matches, teams, venues, series |

## 🚀 Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then add your RAPIDAPI_KEY (optional)
streamlit run app.py                                   # or: streamlit run main.py
```

On first launch the app **creates the database and loads sample data automatically**, so every page except the live API ones works with no key.

Reset / rebuild the DB manually: `python -m database.init_db --reset` (use `--no-seed` for empty tables).
Run the tests: `pip install pytest && pytest -q`

### 🔑 API key setup
1. Subscribe (free tier) to **Cricbuzz Cricket** on RapidAPI: <https://rapidapi.com/cricketapilive/api/cricbuzz-cricket>
2. Put the key in `.env` as `RAPIDAPI_KEY=...` (or in `.streamlit/secrets.toml` / Streamlit Cloud secrets).
3. Keys are never hard-coded; `.env` and `secrets.toml` are git-ignored.

> ⚠️ Endpoint paths/response shapes are implemented from the RapidAPI documentation and parsed defensively. If a path or field differs for your plan, adjust it in one place: `utils/api_client.py`. Test calls interactively in `notebooks/data_fetching.ipynb`.

### 🗄️ Using PostgreSQL or MySQL
Set `DATABASE_URL` in `.env` (examples in `.env.example`), install the driver (`psycopg2-binary` / `PyMySQL`), then run `python -m database.init_db`. See the dialect notes at the top of `database/schema.sql` and `sql/queries.py` (date functions, `MIN/MAX` scalar → `LEAST/GREATEST`, std-dev → `STDDEV_POP`).

## 🏗️ Architecture

```
┌──────────────────────── Streamlit UI (app.py + pages/) ────────────────────────┐
│  Home │ Live Matches │ Top Stats │ SQL Analytics │ CRUD                         │
└───────┬───────────────────┬──────────────────┬────────────────┬─────────────────┘
        │                   │                  │                │
        │            utils/api_client.py   sql/queries.py   utils/crud.py
        │            (requests+retry,      (25 queries)     (validation,
        │             parsers)                │              transactions)
        │                   │                  │                │
        │            utils/api_to_db.py ───────┴────────────────┘
        ▼                   │
  Cricbuzz API (RapidAPI)   ▼
                      utils/db_connection.py  ← utils/config.py (.env / secrets)
                            │
                  SQLAlchemy engine → SQLite / PostgreSQL / MySQL
```

**Data flow:** API → `api_client` (retry, JSON parse) → pages (display) → optional `api_to_db` (get-or-create into SQL) → SQL analytics & CRUD read the same tables.

## 🧱 Database design (3NF)

```
teams ──┐                 series
        │ 1..n               │ 1..n
        ├──────────► matches ◄┘ ◄── venues
        │ (team1, team2,       │ 1..n
        │  winner, toss)       ├──► batting_performances ◄── players ──► player_career_stats
        │                      ├──► bowling_performances ◄──┘      │
        │                      └──► fielding_performances ◄────────┘
```

* **PKs** on every table; **FKs** with `ON DELETE CASCADE` for player/match child rows, restrictive for teams/venues/series.
* **Constraints:** `CHECK` on roles, formats, victory types, capacity > 0, `team1 <> team2`; `UNIQUE` on (match, innings, player) etc.
* **Indexes** on match date, teams, venue, format, player/match keys in the performance tables.
* **Views:** `v_match_results`, `v_player_overview`.
* Full DDL: `database/schema.sql`.

### API endpoint → table mapping
| Endpoint (RapidAPI) | Used for | Table(s) |
|---|---|---|
| `/matches/v1/{live,recent,upcoming}` | match lists | `matches`, `teams`, `venues`, `series` |
| `/mcenter/v1/{id}/scard` | scorecards | displayed live; maps to `batting_/bowling_performances` |
| `/stats/v1/topstats/0?statsType=` | leaderboards | displayed (and comparable with `player_career_stats`) |
| `/stats/v1/rankings/{batsmen,bowlers,allrounders,teams}` | ICC rankings | displayed |
| `/teams/v1/international`, `/stats/v1/player/{id}` | teams / player profiles | `teams`, `players`, `player_career_stats` |

## 🔍 The 25 SQL questions
Implemented in `sql/queries.py` (Beginner 1-8: SELECT/WHERE/GROUP BY; Intermediate 9-16: JOINs, CTEs, subset filters; Advanced 17-25: window functions, `RANK`, `LAG`, `ROW_NUMBER`, std-dev, partnerships, time series). Each is runnable from the **SQL Queries & Analytics** page and covered by `tests/test_database_and_queries.py`.

## 📂 Project structure
```
cricbuzz_livestats/
├── app.py / main.py         # entry point (navigation)
├── requirements.txt, .env.example, .gitignore, README.md
├── pages/                   # home, live_matches, top_stats, sql_queries, crud_operations
├── utils/                   # config, db_connection, api_client, api_to_db, crud
├── database/                # schema.sql, seed_sample_data.py, init_db.py
├── sql/queries.py           # 25 SQL questions
├── notebooks/data_fetching.ipynb
├── tests/                   # 37 pytest tests (DB, queries, CRUD, UI smoke)
└── data/                    # SQLite file is created here
```

## ☁️ Deployment (Streamlit Community Cloud)
1. Push to GitHub (`.env` is git-ignored).
2. On <https://share.streamlit.io> create an app → main file `app.py`.
3. Add secrets (`RAPIDAPI_KEY`, optional `DATABASE_URL`) in *App settings → Secrets*.
4. For persistence use a hosted PostgreSQL/MySQL `DATABASE_URL`; Cloud's local SQLite file resets on redeploy.

## ✅ Deliverables checklist
- [x] Source code (`app.py`, `main.py`, `pages/`, `utils/`)
- [x] Database schema + sample data (`database/`)
- [x] Documentation + API key configuration (this file, `.env.example`)
- [x] `requirements.txt`
- [x] All four modules: Live Matches, Top Stats, SQL Analytics, CRUD
- [x] 25 SQL questions (easy / medium / hard)
- [ ] Demo recording video (record your screen walking through each page)
- [ ] Git repository + commits (`git init && git add . && git commit`)

## ⚠️ Notes
* Sample player **names are real but all statistics are synthetic** (generated by `database/seed_sample_data.py`) purely for learning/demo.
* Sample dates are generated relative to the day of first launch, so "last 30 days" queries have data; rebuild with `--reset` to refresh.
* Future improvements: scheduled API → DB sync, authentication for the CRUD page, caching layer, Dockerfile, more charts.
