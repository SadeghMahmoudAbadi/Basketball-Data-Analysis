# In order to suppress warning related to forward references
from __future__ import annotations
from datetime import date
import sqlite3


class Season:
    season_id: int
    champion_id: str

    def __init__(self, season_id: int, champion_id: str) -> None:
        self.season_id = season_id
        self.champion_id = champion_id

    def insert_season(self, cursor: sqlite3.Cursor) -> None:
        """Insert the season into seasons table"""
        # Insert data into seasons table
        cursor.execute(
            "INSERT INTO seasons (season_id, champion_id) VALUES (?, ?)",
            (self.season_id, self.champion_id))


class Team:
    team_id: str
    name: str
    city: str
    state: str

    def __init__(self, team_id: str, name: str, city: str, state: str) -> None:
        self.team_id = team_id
        self.name = name
        self.city = city
        self.state = state

    def insert_team(self, cursor: sqlite3.Cursor) -> None:
        """Insert the team into teams table"""
        # Insert data into teams table
        cursor.execute(
            """
            INSERT INTO teams (
                team_id,
                name,
                city,
                state
            )
            VALUES (?, ?, ?, ?)
            """,
            (self.team_id, self.name, self.city, self.state))


class Player:
    player_id: str
    name: str
    birthdate: date
    height: int
    weight: int
    shoots: str
    nationality: str
    college: str
    position: list[str]

    def __init__(self, player_id: str, name: str, birthdate: date, height: int,
                 weight: int, shoots: str, nationality: str, college: str,
                 position: list[str]) -> None:
        self.player_id = player_id
        self.name = name
        self.birthdate = birthdate
        self.height = height
        self.weight = weight
        self.shoots = shoots
        self.nationality = nationality
        self.college = college
        self.position = position

    def insert_player(self, cursor: sqlite3.Cursor) -> None:
        """Insert the player into players table"""
        # Insert data into players table
        cursor.execute(
            """
            INSERT INTO players (
                player_id,
                name,
                birthdate,
                height,
                weight,
                shoots,
                nationality,
                college
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (self.player_id, self.name, self.birthdate.isoformat(), self.height,
             self.weight, self.shoots, self.nationality, self.college))
        # Insert data into player-position table
        for position in self.position:
            cursor.execute(
                "INSERT INTO player_position (player_id, position) VALUES (?, ?)",
                (self.player_id, position))


class Coach:
    coach_id: str
    name: str
    birthdate: str
    nationality: str

    def __init__(self, coach_id: str, name: str, birthdate: str, nationality: str) -> None:
        self.coach_id = coach_id
        self.name = name
        self.birthdate = birthdate
        self.nationality = nationality

    def insert_coach(self, cursor: sqlite3.Cursor) -> None:
        """Insert the coach into coaches table"""
        # Insert data into coaches table
        cursor.execute(
            """
            INSERT INTO coaches (
                coach_id,
                name,
                birthdate,
                nationality
            )
            VALUES (?, ?, ?, ?)
            """,
            (self.coach_id, self.name, self.birthdate, self.nationality))


class Award:
    award_id: str
    name: str

    def __init__(self, award_id: str, name: str) -> None:
        self.award_id = award_id
        self.name = name

    def insert_award(self, cursor: sqlite3.Cursor) -> None:
        """Insert the award into awards table"""
        # Insert data into awards table
        cursor.execute(
            "INSERT INTO awards (award_id, name) VALUES (?, ?)",
            (self.award_id, self.name))
        

class AwardSeason:
    season_id: int
    award_id: str
    player_id: str

    def __init__(self, season_id: int, award_id: str, player_id: str) -> None:
        self.season_id = season_id
        self.award_id = award_id
        self.player_id = player_id

    def insert_award_season(self, cursor: sqlite3.Cursor) -> None:
        """Insert the award into award_season table"""
        # Insert data into award_season table
        cursor.execute(
            "INSERT INTO award_season (season_id, award_id, player_id) VALUES (?, ?, ?)",
            (self.season_id, self.award_id, self.player_id))
               

class PlayerStats:
    season_id: int
    player_id: str
    team_id: str
    g: int
    gs: int
    mp: int
    fg: int
    fga: int
    fg_pct: float
    three_p: int
    three_pa: int
    three_p_pct: float
    two_p: int
    two_pa: int
    two_p_pct: float
    efg_pct: float
    ft: int
    fta: int
    ft_pct: float
    orb: int
    drb: int
    trb: int
    ast: int
    stl: int
    blk: int
    tov: int
    pf: int
    pts: int
    trp_dbl: int
    ws: float
    xp: int

    def __init__(self, season_id: int, player_id: str, team_id: str, g: int, gs: int,
                 mp: int, fg: int, fga: int, fg_pct: float, three_p: int, three_pa: int,
                 three_p_pct: float, two_p: int, two_pa: int, two_p_pct: float,
                 efg_pct: float, ft: int, fta: int, ft_pct: float, orb: int, drb: int,
                 trb: int, ast: int, stl: int, blk: int, tov: int, pf: int, pts: int,
                 trp_dbl: int, ws: float, xp: str) -> None:
        self.season_id = season_id
        self.player_id = player_id
        self.team_id = team_id
        self.g = g
        self.gs = gs
        self.mp = mp
        self.fg = fg
        self.fga = fga
        self.fg_pct = fg_pct
        self.three_p = three_p
        self.three_pa = three_pa
        self.three_p_pct = three_p_pct
        self.two_p = two_p
        self.two_pa = two_pa
        self.two_p_pct = two_p_pct
        self.efg_pct = efg_pct
        self.ft = ft
        self.fta = fta
        self.ft_pct = ft_pct
        self.orb = orb
        self.drb = drb
        self.trb = trb
        self.ast = ast
        self.stl = stl
        self.blk = blk
        self.tov = tov
        self.pf = pf
        self.pts = pts
        self.trp_dbl = trp_dbl
        self.ws = ws
        self.xp = 0 if xp == 'R' else int(xp)

    def insert_player_stats(self, cursor: sqlite3.Cursor) -> None:
        """Insert the player stats into player_stats table"""
        # Insert data into player_stats table
        cursor.execute(
            """
            INSERT INTO player_stats (
                season_id,
                player_id,
                team_id,
                games,
                games_started,
                minutes_played,
                field_goals,
                field_goal_attempts,
                field_goal_percent,
                three_point_field_goals,
                three_point_field_goal_attempts,
                three_point_field_goal_percent,
                two_point_field_goals,
                two_point_field_goal_attempts,
                two_point_field_goal_percent,
                effective_field_goal_percent,
                free_throws,
                free_throw_attempts,
                free_throw_percent,
                offensive_rebounds,
                defensive_rebounds,
                total_rebounds,
                assists,
                steals,
                blocks,
                turnovers,
                personal_fouls,
                points,
                triple_doubles,
                win_shares,
                experience
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (self.season_id, self.player_id, self.team_id, self.g, self.gs, self.mp,
             self.fg, self.fga, self.fg_pct, self.three_p, self.three_pa,
             self.three_p_pct, self.two_p, self.two_pa, self.two_p_pct,
             self.efg_pct, self.ft, self.fta, self.ft_pct, self.orb, self.drb,
             self.trb, self.ast, self.stl, self.blk, self.tov, self.pf, self.pts,
             self.trp_dbl, self.ws, self.xp))
        

class TeamStats:
    season_id: int
    team_id: str
    wins: int
    losses: int
    wl_pct: float
    finish_rank: int
    playoff_result: str
    ortg: float
    drtg: float
    nrtg: float
    pace: float

    def __init__(self, season_id: int, team_id: str, wins: int, losses: int,
                 wl_pct: float, finish_rank: int, playoff_result: str,
                 ortg: float, drtg: float, nrtg: float, pace: float) -> None:
        self.season_id = season_id
        self.team_id = team_id
        self.wins = wins
        self.losses = losses
        self.wl_pct = wl_pct
        self.finish_rank = finish_rank
        self.playoff_result = playoff_result
        self.ortg = ortg
        self.drtg = drtg
        self.nrtg = nrtg
        self.pace = pace

    def insert_team_stats(self, cursor: sqlite3.Cursor) -> None:
        """Insert the team stats into team_stats table"""
        # Insert data into team_stats table
        cursor.execute(
            """
            INSERT INTO team_stats (
                season_id,
                team_id,
                wins,
                losses,
                win_loss_percent,
                finish_rank,
                playoff_result,
                offensive_rating,
                defensive_rating,
                net_rating,
                pace
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (self.season_id, self.team_id, self.wins, self.losses, self.wl_pct, 
             self.finish_rank, self.playoff_result, self.ortg, self.drtg,
             self.nrtg, self.pace))
        

class CoachStats:
    season_id: int
    coach_id: str
    team_id: str
    wins: int
    losses: int

    def __init__(self, season_id: int, coach_id: str, team_id: str, wins: int,
                 losses: int) -> None:
        self.season_id = season_id
        self.coach_id = coach_id
        self.team_id = team_id
        self.wins = wins
        self.losses = losses

    def insert_coach_stats(self, cursor: sqlite3.Cursor) -> None:
        """Insert the coach stats into coach_stats table"""
        # Insert data into coach_stats table
        cursor.execute(
            """
            INSERT INTO coach_stats (
                season_id,
                coach_id,
                team_id,
                wins_under_coach,
                losses_under_coach    
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (self.season_id, self.coach_id, self.team_id, self.wins, self.losses))