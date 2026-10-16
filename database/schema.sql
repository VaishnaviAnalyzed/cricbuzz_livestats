-- =====================================================================
-- Cricbuzz LiveStats - Database schema (SQLite default; ANSI-friendly)
-- Dialect notes:
--   * PostgreSQL: use SERIAL / GENERATED ... AS IDENTITY for *_id keys and
--     replace "CREATE VIEW IF NOT EXISTS" with "CREATE OR REPLACE VIEW".
--   * MySQL: use INT AUTO_INCREMENT for *_id keys.
-- =====================================================================

-- ---------- Reference tables ----------
CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,
    cb_id       INTEGER UNIQUE,                 -- Cricbuzz team id (nullable)
    team_name   VARCHAR(100) NOT NULL UNIQUE,
    country     VARCHAR(60)  NOT NULL,
    short_name  VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id    INTEGER PRIMARY KEY,
    cb_id       INTEGER UNIQUE,
    venue_name  VARCHAR(150) NOT NULL,
    city        VARCHAR(80),
    country     VARCHAR(60)  NOT NULL,
    capacity    INTEGER CHECK (capacity IS NULL OR capacity > 0),
    UNIQUE (venue_name, city)
);

CREATE TABLE IF NOT EXISTS players (
    player_id      INTEGER PRIMARY KEY,
    cb_id          INTEGER UNIQUE,
    full_name      VARCHAR(120) NOT NULL,
    country        VARCHAR(60)  NOT NULL,
    playing_role   VARCHAR(30)  NOT NULL
        CHECK (playing_role IN ('Batsman','Bowler','All-rounder','Wicket-keeper')),
    batting_style  VARCHAR(40),
    bowling_style  VARCHAR(60)
);

CREATE TABLE IF NOT EXISTS series (
    series_id      INTEGER PRIMARY KEY,
    cb_id          INTEGER UNIQUE,
    series_name    VARCHAR(200) NOT NULL UNIQUE,
    host_country   VARCHAR(60),
    match_type     VARCHAR(10) CHECK (match_type IN ('Test','ODI','T20I')),
    start_date     DATE,
    end_date       DATE,
    total_matches  INTEGER CHECK (total_matches IS NULL OR total_matches >= 0)
);

-- ---------- Matches ----------
CREATE TABLE IF NOT EXISTS matches (
    match_id        INTEGER PRIMARY KEY,
    cb_id           INTEGER UNIQUE,
    series_id       INTEGER REFERENCES series(series_id),
    description     VARCHAR(200) NOT NULL,
    match_format    VARCHAR(10)  NOT NULL CHECK (match_format IN ('Test','ODI','T20I')),
    team1_id        INTEGER NOT NULL REFERENCES teams(team_id),
    team2_id        INTEGER NOT NULL REFERENCES teams(team_id),
    venue_id        INTEGER REFERENCES venues(venue_id),
    match_date      DATE NOT NULL,
    status          VARCHAR(40) NOT NULL DEFAULT 'Complete',
    winner_team_id  INTEGER REFERENCES teams(team_id),
    victory_margin  INTEGER CHECK (victory_margin IS NULL OR victory_margin >= 0),
    victory_type    VARCHAR(10) CHECK (victory_type IN ('runs','wickets','draw','tie')),
    toss_winner_id  INTEGER REFERENCES teams(team_id),
    toss_decision   VARCHAR(5)  CHECK (toss_decision IN ('bat','bowl')),
    CHECK (team1_id <> team2_id)
);

-- ---------- Per-match performances ----------
CREATE TABLE IF NOT EXISTS batting_performances (
    perf_id          INTEGER PRIMARY KEY,
    match_id         INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    player_id        INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    team_id          INTEGER NOT NULL REFERENCES teams(team_id),
    innings_no       INTEGER NOT NULL CHECK (innings_no BETWEEN 1 AND 4),
    batting_position INTEGER NOT NULL CHECK (batting_position BETWEEN 1 AND 11),
    runs             INTEGER NOT NULL CHECK (runs >= 0),
    balls            INTEGER NOT NULL CHECK (balls >= 0),
    fours            INTEGER NOT NULL DEFAULT 0,
    sixes            INTEGER NOT NULL DEFAULT 0,
    strike_rate      REAL,
    is_out           INTEGER NOT NULL DEFAULT 1 CHECK (is_out IN (0,1)),
    UNIQUE (match_id, innings_no, player_id)
);

CREATE TABLE IF NOT EXISTS bowling_performances (
    perf_id        INTEGER PRIMARY KEY,
    match_id       INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    player_id      INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    team_id        INTEGER NOT NULL REFERENCES teams(team_id),
    innings_no     INTEGER NOT NULL CHECK (innings_no BETWEEN 1 AND 4),
    overs          REAL    NOT NULL CHECK (overs > 0),
    maidens        INTEGER NOT NULL DEFAULT 0,
    runs_conceded  INTEGER NOT NULL CHECK (runs_conceded >= 0),
    wickets        INTEGER NOT NULL DEFAULT 0 CHECK (wickets BETWEEN 0 AND 10),
    economy        REAL,
    UNIQUE (match_id, innings_no, player_id)
);

CREATE TABLE IF NOT EXISTS fielding_performances (
    perf_id     INTEGER PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    player_id   INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    catches     INTEGER NOT NULL DEFAULT 0,
    stumpings   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (match_id, player_id)
);

-- ---------- Career aggregates (what the Cricbuzz stats endpoints return) ----------
CREATE TABLE IF NOT EXISTS player_career_stats (
    stat_id        INTEGER PRIMARY KEY,
    player_id      INTEGER NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    format         VARCHAR(10) NOT NULL CHECK (format IN ('Test','ODI','T20I')),
    matches        INTEGER NOT NULL DEFAULT 0 CHECK (matches >= 0),
    innings        INTEGER NOT NULL DEFAULT 0,
    runs           INTEGER NOT NULL DEFAULT 0,
    balls_faced    INTEGER NOT NULL DEFAULT 0,
    batting_avg    REAL,
    strike_rate    REAL,
    highest_score  INTEGER NOT NULL DEFAULT 0,
    centuries      INTEGER NOT NULL DEFAULT 0,
    fifties        INTEGER NOT NULL DEFAULT 0,
    wickets        INTEGER NOT NULL DEFAULT 0,
    bowling_avg    REAL,
    economy        REAL,
    catches        INTEGER NOT NULL DEFAULT 0,
    stumpings      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (player_id, format)
);

-- ---------- Indexes for frequently filtered / joined columns ----------
CREATE INDEX IF NOT EXISTS idx_players_country      ON players(country);
CREATE INDEX IF NOT EXISTS idx_players_role         ON players(playing_role);
CREATE INDEX IF NOT EXISTS idx_matches_date         ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_team1        ON matches(team1_id);
CREATE INDEX IF NOT EXISTS idx_matches_team2        ON matches(team2_id);
CREATE INDEX IF NOT EXISTS idx_matches_winner       ON matches(winner_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_venue        ON matches(venue_id);
CREATE INDEX IF NOT EXISTS idx_matches_format       ON matches(match_format);
CREATE INDEX IF NOT EXISTS idx_bat_player           ON batting_performances(player_id);
CREATE INDEX IF NOT EXISTS idx_bat_match            ON batting_performances(match_id, innings_no);
CREATE INDEX IF NOT EXISTS idx_bowl_player          ON bowling_performances(player_id);
CREATE INDEX IF NOT EXISTS idx_bowl_match           ON bowling_performances(match_id);
CREATE INDEX IF NOT EXISTS idx_career_player_format ON player_career_stats(player_id, format);
CREATE INDEX IF NOT EXISTS idx_series_start         ON series(start_date);

-- ---------- Views ----------
CREATE VIEW IF NOT EXISTS v_match_results AS
SELECT m.match_id, m.match_date, m.match_format, m.description,
       t1.team_name AS team1, t2.team_name AS team2,
       v.venue_name, v.city, w.team_name AS winner,
       m.victory_type, m.victory_margin, m.status
FROM matches m
JOIN teams t1 ON t1.team_id = m.team1_id
JOIN teams t2 ON t2.team_id = m.team2_id
LEFT JOIN venues v ON v.venue_id = m.venue_id
LEFT JOIN teams  w ON w.team_id = m.winner_team_id;

CREATE VIEW IF NOT EXISTS v_player_overview AS
SELECT p.player_id, p.full_name, p.country, p.playing_role,
       SUM(c.matches) AS total_matches,
       SUM(c.runs)    AS total_runs,
       SUM(c.wickets) AS total_wickets
FROM players p
LEFT JOIN player_career_stats c ON c.player_id = p.player_id
GROUP BY p.player_id, p.full_name, p.country, p.playing_role;
