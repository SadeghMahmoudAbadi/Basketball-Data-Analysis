import sqlite3


# Database name
database = 'basketball_reference.db'

# Connect to database (creates it if it doesn't exist)
conn = sqlite3.connect(database)
cursor = conn.cursor()
# Enable foreign key enforcement
cursor.execute("PRAGMA foreign_keys = ON;")

# Teams
cursor.execute("""
CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,
    name TEXT,
    city TEXT,
    state TEXT
);
""")

# Players
cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    name TEXT,
    birthdate DATE,
    height INTEGER,
    weight INTEGER,
    shoots TEXT,
    nationality TEXT,
    college TEXT
);
""")

# Coaches
cursor.execute("""
CREATE TABLE IF NOT EXISTS coaches (
    coach_id TEXT PRIMARY KEY,
    name TEXT,
    birthdate DATE,
    nationality TEXT
);
""")

# Awards
cursor.execute("""
CREATE TABLE IF NOT EXISTS awards (
    award_id TEXT PRIMARY KEY,
    name TEXT
);
""")

# Seasons
cursor.execute("""
CREATE TABLE IF NOT EXISTS seasons (
    season_id INTEGER PRIMARY KEY,
    champion_id TEXT,
    FOREIGN KEY (champion_id) REFERENCES teams(team_id)
);
""")

# Player positions
cursor.execute("""
CREATE TABLE IF NOT EXISTS player_position (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT NOT NULL,
    position TEXT NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
""")

# Award season
cursor.execute("""
CREATE TABLE IF NOT EXISTS award_season (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    award_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (award_id) REFERENCES awards(award_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
""")

# Player stats
cursor.execute("""
CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    games INTEGER,
    games_started INTEGER,
    minutes_played INTEGER,
    field_goals INTEGER,
    field_goal_attempts INTEGER,
    field_goal_percent REAL,
    three_point_field_goals INTEGER,
    three_point_field_goal_attempts INTEGER,
    three_point_field_goal_percent REAL,
    two_point_field_goals INTEGER,
    two_point_field_goal_attempts INTEGER,
    two_point_field_goal_percent REAL,
    effective_field_goal_percent REAL,
    free_throws INTEGER,
    free_throw_attempts INTEGER,
    free_throw_percent REAL,
    offensive_rebounds INTEGER,
    defensive_rebounds INTEGER,
    total_rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,
    points INTEGER,
    triple_doubles INTEGER,
    win_shares REAL,
    experience INTEGER,
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
""")

# Team stats
cursor.execute("""
CREATE TABLE IF NOT EXISTS team_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    team_id TEXT NOT NULL,
    wins INTEGER,
    losses INTEGER,
    win_loss_percent REAL,
    finish_rank INTEGER,
    playoff_result TEXT,
    offensive_rating REAL,
    defensive_rating REAL,
    net_rating REAL,
    pace REAL,
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
""")

# Coach stats
cursor.execute("""
CREATE TABLE IF NOT EXISTS coach_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    coach_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    wins_under_coach INTEGER,
    losses_under_coach INTEGER,
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (coach_id) REFERENCES coaches(coach_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
""")

# Save changes and close connection
conn.commit()
conn.close()

print(f'Database {database} created successfully.')