"""The 25 SQL practice questions from the project brief.

Dialect: SQLite (default). For PostgreSQL/MySQL swap:
  date('now','-30 day')      -> CURRENT_DATE - INTERVAL '30 days'
  strftime('%Y', d)          -> EXTRACT(YEAR FROM d)
  MIN(a,b) / MAX(a,b)        -> LEAST(a,b) / GREATEST(a,b)   (scalar versions)
  SQRT(AVG(x*x)-AVG(x)^2)    -> STDDEV_POP(x)
"""
from __future__ import annotations

from typing import TypedDict


class Query(TypedDict, total=False):
    """Shape of one entry in QUERIES."""

    id: int
    level: str
    title: str
    question: str
    sql: str
    extra_title: str
    extra_sql: str


QUERIES: list[Query] = [
    # ======================= BEGINNER (1-8) =======================
    {
        "id": 1, "level": "Beginner",
        "title": "Players who represent India",
        "question": "Find all players who represent India: full name, playing role, batting style, bowling style.",
        "sql": """
SELECT full_name, playing_role, batting_style, bowling_style
FROM players
WHERE country = 'India'
ORDER BY full_name;
""",
    },
    {
        "id": 2, "level": "Beginner",
        "title": "Matches played in the last 30 days",
        "question": "Matches in the last 30 days: description, both teams, venue + city, date. Most recent first.",
        "sql": """
SELECT m.description,
       t1.team_name AS team1,
       t2.team_name AS team2,
       v.venue_name || ', ' || v.city AS venue,
       m.match_date
FROM matches m
JOIN teams t1 ON t1.team_id = m.team1_id
JOIN teams t2 ON t2.team_id = m.team2_id
LEFT JOIN venues v ON v.venue_id = m.venue_id
WHERE m.match_date >= date('now', '-30 day')
  AND m.match_date <= date('now')
ORDER BY m.match_date DESC;
""",
    },
    {
        "id": 3, "level": "Beginner",
        "title": "Top 10 ODI run scorers",
        "question": "Top 10 highest run scorers in ODI cricket: name, total runs, batting average, centuries.",
        "sql": """
SELECT p.full_name AS player_name,
       c.runs AS total_runs,
       c.batting_avg,
       c.centuries
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
WHERE c.format = 'ODI'
ORDER BY c.runs DESC
LIMIT 10;
""",
    },
    {
        "id": 4, "level": "Beginner",
        "title": "Venues with capacity over 50,000",
        "question": "Venues with seating capacity > 50,000: name, city, country, capacity. Largest first.",
        "sql": """
SELECT venue_name, city, country, capacity
FROM venues
WHERE capacity > 50000
ORDER BY capacity DESC;
""",
    },
    {
        "id": 5, "level": "Beginner",
        "title": "Total wins per team",
        "question": "How many matches each team has won. Most wins first.",
        "sql": """
SELECT t.team_name, COUNT(*) AS total_wins
FROM matches m
JOIN teams t ON t.team_id = m.winner_team_id
GROUP BY t.team_id, t.team_name
ORDER BY total_wins DESC;
""",
    },
    {
        "id": 6, "level": "Beginner",
        "title": "Players per playing role",
        "question": "Count how many players belong to each playing role.",
        "sql": """
SELECT playing_role AS role, COUNT(*) AS player_count
FROM players
GROUP BY playing_role
ORDER BY player_count DESC;
""",
    },
    {
        "id": 7, "level": "Beginner",
        "title": "Highest individual score per format",
        "question": "Highest individual batting score in each format (Test, ODI, T20I).",
        "sql": """
SELECT format, MAX(highest_score) AS highest_score
FROM player_career_stats
GROUP BY format
ORDER BY highest_score DESC;
""",
    },
    {
        "id": 8, "level": "Beginner",
        "title": "Series that started in 2024",
        "question": "Series that started in 2024: name, host country, match type, start date, matches planned.",
        "sql": """
SELECT series_name, host_country, match_type, start_date, total_matches
FROM series
WHERE strftime('%Y', start_date) = '2024'
ORDER BY start_date;
""",
    },
    # ======================= INTERMEDIATE (9-16) =======================
    {
        "id": 9, "level": "Intermediate",
        "title": "All-rounders: 1000+ runs and 50+ wickets",
        "question": "All-rounders with > 1000 runs AND > 50 wickets: name, runs, wickets, format.",
        "sql": """
SELECT p.full_name AS player_name,
       c.runs AS total_runs,
       c.wickets AS total_wickets,
       c.format
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
WHERE p.playing_role = 'All-rounder'
  AND c.runs > 1000
  AND c.wickets > 50
ORDER BY c.runs DESC;
""",
    },
    {
        "id": 10, "level": "Intermediate",
        "title": "Last 20 completed matches",
        "question": "Last 20 completed matches: description, teams, winner, margin, victory type, venue.",
        "sql": """
SELECT m.description,
       t1.team_name AS team1,
       t2.team_name AS team2,
       w.team_name  AS winning_team,
       m.victory_margin,
       m.victory_type,
       v.venue_name
FROM matches m
JOIN teams t1 ON t1.team_id = m.team1_id
JOIN teams t2 ON t2.team_id = m.team2_id
LEFT JOIN teams w  ON w.team_id = m.winner_team_id
LEFT JOIN venues v ON v.venue_id = m.venue_id
WHERE m.status = 'Complete'
ORDER BY m.match_date DESC, m.match_id DESC
LIMIT 20;
""",
    },
    {
        "id": 11, "level": "Intermediate",
        "title": "Player performance across formats",
        "question": "Players with 2+ formats: runs in Test / ODI / T20I and overall batting average.",
        "sql": """
SELECT p.full_name AS player_name,
       SUM(CASE WHEN c.format = 'Test' THEN c.runs END) AS test_runs,
       SUM(CASE WHEN c.format = 'ODI'  THEN c.runs END) AS odi_runs,
       SUM(CASE WHEN c.format = 'T20I' THEN c.runs END) AS t20i_runs,
       ROUND(AVG(c.batting_avg), 2) AS overall_batting_avg
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT c.format) >= 2
ORDER BY overall_batting_avg DESC;
""",
    },
    {
        "id": 12, "level": "Intermediate",
        "title": "Home vs away wins per team",
        "question": "Each team's wins at home (venue country = team country) vs away.",
        "sql": """
WITH team_matches AS (
    SELECT match_id, team1_id AS team_id, venue_id, winner_team_id
    FROM matches WHERE status = 'Complete'
    UNION ALL
    SELECT match_id, team2_id AS team_id, venue_id, winner_team_id
    FROM matches WHERE status = 'Complete'
)
SELECT t.team_name,
       SUM(CASE WHEN v.country =  t.country THEN 1 ELSE 0 END) AS home_matches,
       SUM(CASE WHEN v.country =  t.country AND tm.winner_team_id = tm.team_id THEN 1 ELSE 0 END) AS home_wins,
       SUM(CASE WHEN v.country <> t.country THEN 1 ELSE 0 END) AS away_matches,
       SUM(CASE WHEN v.country <> t.country AND tm.winner_team_id = tm.team_id THEN 1 ELSE 0 END) AS away_wins
FROM team_matches tm
JOIN teams  t ON t.team_id  = tm.team_id
JOIN venues v ON v.venue_id = tm.venue_id
GROUP BY t.team_id, t.team_name
ORDER BY home_wins + away_wins DESC;
""",
    },
    {
        "id": 13, "level": "Intermediate",
        "title": "100+ run partnerships (consecutive batsmen)",
        "question": "Consecutive batsmen whose combined runs in an innings are >= 100.",
        "sql": """
SELECT p1.full_name AS batsman_1,
       p2.full_name AS batsman_2,
       b1.runs + b2.runs AS partnership_runs,
       b1.innings_no,
       m.description,
       m.match_date
FROM batting_performances b1
JOIN batting_performances b2
  ON  b2.match_id = b1.match_id
  AND b2.innings_no = b1.innings_no
  AND b2.team_id = b1.team_id
  AND b2.batting_position = b1.batting_position + 1
JOIN players p1 ON p1.player_id = b1.player_id
JOIN players p2 ON p2.player_id = b2.player_id
JOIN matches m  ON m.match_id = b1.match_id
WHERE b1.runs + b2.runs >= 100
ORDER BY partnership_runs DESC
LIMIT 200;
""",
    },
    {
        "id": 14, "level": "Intermediate",
        "title": "Bowling performance by venue",
        "question": "Bowlers with 3+ matches at a venue (4+ overs each): avg economy, wickets, matches.",
        "sql": """
SELECT p.full_name AS bowler,
       v.venue_name,
       COUNT(DISTINCT bp.match_id) AS matches_played,
       ROUND(AVG(bp.economy), 2)   AS avg_economy,
       SUM(bp.wickets)             AS total_wickets
FROM bowling_performances bp
JOIN players p ON p.player_id = bp.player_id
JOIN matches m ON m.match_id  = bp.match_id
JOIN venues  v ON v.venue_id  = m.venue_id
WHERE bp.overs >= 4
GROUP BY p.player_id, p.full_name, v.venue_id, v.venue_name
HAVING COUNT(DISTINCT bp.match_id) >= 3
ORDER BY avg_economy ASC
LIMIT 200;
""",
    },
    {
        "id": 15, "level": "Intermediate",
        "title": "Performance in close matches",
        "question": "Close = won by < 50 runs OR < 5 wickets. Avg runs, close matches played and won per player.",
        "sql": """
SELECT p.full_name AS player_name,
       ROUND(AVG(b.runs), 2) AS avg_runs,
       COUNT(DISTINCT b.match_id) AS close_matches_played,
       COUNT(DISTINCT CASE WHEN m.winner_team_id = b.team_id THEN b.match_id END) AS close_matches_won
FROM batting_performances b
JOIN matches m ON m.match_id  = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE (m.victory_type = 'runs'    AND m.victory_margin < 50)
   OR (m.victory_type = 'wickets' AND m.victory_margin < 5)
GROUP BY p.player_id, p.full_name
ORDER BY avg_runs DESC;
""",
    },
    {
        "id": 16, "level": "Intermediate",
        "title": "Yearly batting trend since 2020",
        "question": "Per player per year (since 2020, 5+ matches): average runs and average strike rate.",
        "sql": """
SELECT p.full_name AS player_name,
       CAST(strftime('%Y', m.match_date) AS INTEGER) AS year,
       COUNT(DISTINCT b.match_id) AS matches_played,
       ROUND(AVG(b.runs), 2)        AS avg_runs,
       ROUND(AVG(b.strike_rate), 2) AS avg_strike_rate
FROM batting_performances b
JOIN matches m ON m.match_id  = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE m.match_date >= '2020-01-01'
GROUP BY p.player_id, p.full_name, strftime('%Y', m.match_date)
HAVING COUNT(DISTINCT b.match_id) >= 5
ORDER BY p.full_name, year;
""",
    },
    # ======================= ADVANCED (17-25) =======================
    {
        "id": 17, "level": "Advanced",
        "title": "Does winning the toss help?",
        "question": "% of matches won by the toss winner, split by toss decision (bat / bowl).",
        "sql": """
SELECT toss_decision,
       COUNT(*) AS matches,
       SUM(CASE WHEN toss_winner_id = winner_team_id THEN 1 ELSE 0 END) AS won_after_toss,
       ROUND(100.0 * SUM(CASE WHEN toss_winner_id = winner_team_id THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_pct
FROM matches
WHERE status = 'Complete' AND winner_team_id IS NOT NULL AND toss_winner_id IS NOT NULL
GROUP BY toss_decision
UNION ALL
SELECT 'overall',
       COUNT(*),
       SUM(CASE WHEN toss_winner_id = winner_team_id THEN 1 ELSE 0 END),
       ROUND(100.0 * SUM(CASE WHEN toss_winner_id = winner_team_id THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM matches
WHERE status = 'Complete' AND winner_team_id IS NOT NULL AND toss_winner_id IS NOT NULL;
""",
    },
    {
        "id": 18, "level": "Advanced",
        "title": "Most economical limited-overs bowlers",
        "question": "ODI + T20I bowlers: economy and wickets; 10+ matches and avg 2+ overs per match.",
        "sql": """
SELECT p.full_name AS bowler,
       ROUND(SUM(bp.runs_conceded) * 1.0 / SUM(bp.overs), 2) AS economy_rate,
       SUM(bp.wickets) AS total_wickets,
       COUNT(DISTINCT bp.match_id) AS matches_bowled,
       ROUND(AVG(bp.overs), 2) AS avg_overs_per_match
FROM bowling_performances bp
JOIN matches m ON m.match_id  = bp.match_id
JOIN players p ON p.player_id = bp.player_id
WHERE m.match_format IN ('ODI', 'T20I')
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT bp.match_id) >= 10 AND AVG(bp.overs) >= 2
ORDER BY economy_rate ASC;
""",
    },
    {
        "id": 19, "level": "Advanced",
        "title": "Most consistent batsmen (std. deviation)",
        "question": "Avg runs and standard deviation per player (10+ balls faced, since 2022). Lower SD = more consistent.",
        "sql": """
SELECT p.full_name AS player_name,
       COUNT(*) AS innings,
       ROUND(AVG(b.runs), 2) AS avg_runs,
       ROUND(SQRT(MAX(AVG(b.runs * b.runs) - AVG(b.runs) * AVG(b.runs), 0)), 2) AS std_dev_runs
FROM batting_performances b
JOIN matches m ON m.match_id  = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE b.balls >= 10
  AND m.match_date >= '2022-01-01'
GROUP BY p.player_id, p.full_name
HAVING COUNT(*) >= 10
ORDER BY std_dev_runs ASC;
""",
    },
    {
        "id": 20, "level": "Advanced",
        "title": "Matches and batting average by format",
        "question": "Test/ODI/T20 match counts and batting averages per player (20+ total matches).",
        "sql": """
SELECT p.full_name AS player_name,
       COALESCE(SUM(CASE WHEN c.format = 'Test' THEN c.matches END), 0) AS test_matches,
       COALESCE(SUM(CASE WHEN c.format = 'ODI'  THEN c.matches END), 0) AS odi_matches,
       COALESCE(SUM(CASE WHEN c.format = 'T20I' THEN c.matches END), 0) AS t20_matches,
       MAX(CASE WHEN c.format = 'Test' THEN c.batting_avg END) AS test_avg,
       MAX(CASE WHEN c.format = 'ODI'  THEN c.batting_avg END) AS odi_avg,
       MAX(CASE WHEN c.format = 'T20I' THEN c.batting_avg END) AS t20_avg
FROM player_career_stats c
JOIN players p ON p.player_id = c.player_id
GROUP BY p.player_id, p.full_name
HAVING SUM(c.matches) >= 20
ORDER BY SUM(c.matches) DESC;
""",
    },
    {
        "id": 21, "level": "Advanced",
        "title": "Weighted player performance ranking",
        "question": "Batting + bowling + fielding points per format using the brief's formula; top 10 per format.",
        "sql": """
WITH scored AS (
    SELECT p.player_id, p.full_name, c.format,
           (c.runs * 0.01) + (COALESCE(c.batting_avg, 0) * 0.5) + (COALESCE(c.strike_rate, 0) * 0.3)
               AS batting_points,
           CASE WHEN COALESCE(c.wickets, 0) > 0
                THEN (c.wickets * 2) + ((50 - c.bowling_avg) * 0.5) + ((6 - c.economy) * 2)
                ELSE 0 END AS bowling_points,
           (COALESCE(c.catches, 0) * 3) + (COALESCE(c.stumpings, 0) * 5) AS fielding_points
    FROM player_career_stats c
    JOIN players p ON p.player_id = c.player_id
),
ranked AS (
    SELECT *,
           batting_points + bowling_points + fielding_points AS total_points,
           RANK() OVER (PARTITION BY format
                        ORDER BY batting_points + bowling_points + fielding_points DESC) AS rank_in_format
    FROM scored
)
SELECT format, rank_in_format AS rank, full_name AS player_name,
       ROUND(batting_points, 2)  AS batting_points,
       ROUND(bowling_points, 2)  AS bowling_points,
       fielding_points,
       ROUND(total_points, 2)    AS total_points
FROM ranked
WHERE rank_in_format <= 10
ORDER BY format, rank_in_format;
""",
    },
    {
        "id": 22, "level": "Advanced",
        "title": "Head-to-head match prediction analysis",
        "question": "Team pairs with 5+ matches in the last 3 years: wins, avg margins, bat-first vs chase, win %.",
        "sql": """
WITH h2h AS (
    SELECT match_id,
           MIN(team1_id, team2_id) AS team_a,
           MAX(team1_id, team2_id) AS team_b,
           winner_team_id, victory_type, victory_margin
    FROM matches
    WHERE status = 'Complete'
      AND match_date >= date('now', '-3 years')
)
SELECT ta.team_name AS team_a,
       tb.team_name AS team_b,
       COUNT(*) AS total_matches,
       SUM(CASE WHEN h.winner_team_id = h.team_a THEN 1 ELSE 0 END) AS wins_a,
       SUM(CASE WHEN h.winner_team_id = h.team_b THEN 1 ELSE 0 END) AS wins_b,
       ROUND(AVG(CASE WHEN h.winner_team_id = h.team_a AND h.victory_type = 'runs'    THEN h.victory_margin END), 1) AS a_avg_run_margin,
       ROUND(AVG(CASE WHEN h.winner_team_id = h.team_a AND h.victory_type = 'wickets' THEN h.victory_margin END), 1) AS a_avg_wkt_margin,
       ROUND(AVG(CASE WHEN h.winner_team_id = h.team_b AND h.victory_type = 'runs'    THEN h.victory_margin END), 1) AS b_avg_run_margin,
       ROUND(AVG(CASE WHEN h.winner_team_id = h.team_b AND h.victory_type = 'wickets' THEN h.victory_margin END), 1) AS b_avg_wkt_margin,
       SUM(CASE WHEN h.victory_type = 'runs'    THEN 1 ELSE 0 END) AS batting_first_wins,
       SUM(CASE WHEN h.victory_type = 'wickets' THEN 1 ELSE 0 END) AS bowling_first_wins,
       ROUND(100.0 * SUM(CASE WHEN h.winner_team_id = h.team_a THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct_a,
       ROUND(100.0 * SUM(CASE WHEN h.winner_team_id = h.team_b THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct_b
FROM h2h h
JOIN teams ta ON ta.team_id = h.team_a
JOIN teams tb ON tb.team_id = h.team_b
GROUP BY h.team_a, h.team_b, ta.team_name, tb.team_name
HAVING COUNT(*) >= 5
ORDER BY total_matches DESC;
""",
        "extra_title": "22b. Batting-first vs bowling-first wins by venue (last 3 years)",
        "extra_sql": """
SELECT v.venue_name, v.city,
       COUNT(*) AS decided_matches,
       SUM(CASE WHEN m.victory_type = 'runs'    THEN 1 ELSE 0 END) AS batting_first_wins,
       SUM(CASE WHEN m.victory_type = 'wickets' THEN 1 ELSE 0 END) AS bowling_first_wins,
       ROUND(100.0 * SUM(CASE WHEN m.victory_type = 'runs' THEN 1 ELSE 0 END) / COUNT(*), 1) AS bat_first_win_pct
FROM matches m
JOIN venues v ON v.venue_id = m.venue_id
WHERE m.status = 'Complete'
  AND m.victory_type IN ('runs', 'wickets')
  AND m.match_date >= date('now', '-3 years')
GROUP BY v.venue_id, v.venue_name, v.city
ORDER BY decided_matches DESC;
""",
    },
    {
        "id": 23, "level": "Advanced",
        "title": "Recent player form and momentum",
        "question": "Last 5 vs last 10 batting performances, strike-rate trend, 50+ scores, consistency, form category.",
        "sql": """
WITH ranked AS (
    SELECT b.player_id, b.runs, b.strike_rate,
           ROW_NUMBER() OVER (PARTITION BY b.player_id
                              ORDER BY m.match_date DESC, b.perf_id DESC) AS rn
    FROM batting_performances b
    JOIN matches m ON m.match_id = b.match_id
    WHERE m.status = 'Complete'
),
form AS (
    SELECT player_id,
           COUNT(*) AS innings_used,
           AVG(CASE WHEN rn <= 5 THEN runs END)        AS avg_last5,
           AVG(runs)                                   AS avg_last10,
           AVG(CASE WHEN rn <= 5 THEN strike_rate END) AS sr_last5,
           AVG(strike_rate)                            AS sr_last10,
           SUM(CASE WHEN runs >= 50 THEN 1 ELSE 0 END) AS scores_50_plus,
           SQRT(MAX(AVG(runs * runs) - AVG(runs) * AVG(runs), 0)) AS std_dev
    FROM ranked
    WHERE rn <= 10
    GROUP BY player_id
    HAVING COUNT(*) >= 5
)
SELECT p.full_name AS player_name,
       ROUND(f.avg_last5, 1)  AS avg_last5,
       ROUND(f.avg_last10, 1) AS avg_last10,
       ROUND(f.sr_last5 - f.sr_last10, 1) AS strike_rate_trend,
       f.scores_50_plus,
       ROUND(f.std_dev, 1) AS consistency_std_dev,
       CASE WHEN f.avg_last5 >= 45 AND f.scores_50_plus >= 3 THEN 'Excellent Form'
            WHEN f.avg_last5 >= 30 THEN 'Good Form'
            WHEN f.avg_last5 >= 18 THEN 'Average Form'
            ELSE 'Poor Form' END AS form_category
FROM form f
JOIN players p ON p.player_id = f.player_id
ORDER BY f.avg_last5 DESC;
""",
    },
    {
        "id": 24, "level": "Advanced",
        "title": "Best batting partnerships",
        "question": "Pairs batting consecutively in 5+ partnerships: avg, 50+ count, highest, success rate.",
        "sql": """
WITH partnerships AS (
    SELECT b1.match_id, b1.innings_no,
           MIN(b1.player_id, b2.player_id) AS player_a,
           MAX(b1.player_id, b2.player_id) AS player_b,
           b1.runs + b2.runs AS runs
    FROM batting_performances b1
    JOIN batting_performances b2
      ON  b2.match_id = b1.match_id
      AND b2.innings_no = b1.innings_no
      AND b2.team_id = b1.team_id
      AND b2.batting_position = b1.batting_position + 1
)
SELECT pa.full_name AS player_1,
       pb.full_name AS player_2,
       COUNT(*)            AS partnerships,
       ROUND(AVG(x.runs), 1) AS avg_partnership_runs,
       SUM(CASE WHEN x.runs > 50 THEN 1 ELSE 0 END) AS partnerships_over_50,
       MAX(x.runs)         AS highest_partnership,
       ROUND(100.0 * SUM(CASE WHEN x.runs > 50 THEN 1 ELSE 0 END) / COUNT(*), 1) AS success_rate_pct
FROM partnerships x
JOIN players pa ON pa.player_id = x.player_a
JOIN players pb ON pb.player_id = x.player_b
GROUP BY x.player_a, x.player_b, pa.full_name, pb.full_name
HAVING COUNT(*) >= 5
ORDER BY success_rate_pct DESC, avg_partnership_runs DESC;
""",
    },
    {
        "id": 25, "level": "Advanced",
        "title": "Quarterly time-series: career trajectory",
        "question": "Quarterly averages, quarter-on-quarter change, and Ascending / Declining / Stable career phase.",
        "sql": """
WITH quarterly AS (
    SELECT b.player_id,
           strftime('%Y', m.match_date) || '-Q' ||
               ((CAST(strftime('%m', m.match_date) AS INTEGER) + 2) / 3) AS quarter,
           AVG(b.runs)        AS avg_runs,
           AVG(b.strike_rate) AS avg_sr,
           COUNT(DISTINCT b.match_id) AS matches
    FROM batting_performances b
    JOIN matches m ON m.match_id = b.match_id
    GROUP BY b.player_id, quarter
    HAVING COUNT(DISTINCT b.match_id) >= 3
),
changes AS (
    SELECT *,
           LAG(avg_runs) OVER (PARTITION BY player_id ORDER BY quarter) AS prev_runs,
           COUNT(*)      OVER (PARTITION BY player_id)                  AS n_quarters
    FROM quarterly
)
SELECT p.full_name AS player_name,
       MAX(c.n_quarters) AS quarters_analysed,
       ROUND(AVG(c.avg_runs), 1) AS overall_avg_runs,
       ROUND(AVG(c.avg_sr), 1)   AS overall_strike_rate,
       SUM(CASE WHEN c.avg_runs - c.prev_runs >  2 THEN 1 ELSE 0 END) AS improving_quarters,
       SUM(CASE WHEN c.avg_runs - c.prev_runs < -2 THEN 1 ELSE 0 END) AS declining_quarters,
       SUM(CASE WHEN ABS(c.avg_runs - c.prev_runs) <= 2 THEN 1 ELSE 0 END) AS stable_quarters,
       CASE
         WHEN SUM(CASE WHEN c.avg_runs - c.prev_runs >  2 THEN 1 ELSE 0 END)
            - SUM(CASE WHEN c.avg_runs - c.prev_runs < -2 THEN 1 ELSE 0 END) >= 2 THEN 'Career Ascending'
         WHEN SUM(CASE WHEN c.avg_runs - c.prev_runs < -2 THEN 1 ELSE 0 END)
            - SUM(CASE WHEN c.avg_runs - c.prev_runs >  2 THEN 1 ELSE 0 END) >= 2 THEN 'Career Declining'
         ELSE 'Career Stable' END AS career_phase
FROM changes c
JOIN players p ON p.player_id = c.player_id
GROUP BY p.player_id, p.full_name
HAVING MAX(c.n_quarters) >= 6
ORDER BY overall_avg_runs DESC;
""",
    },
]


def get_query(query_id: int) -> Query:
    """Return a query by its 1-based id."""
    return next(q for q in QUERIES if q["id"] == query_id)
