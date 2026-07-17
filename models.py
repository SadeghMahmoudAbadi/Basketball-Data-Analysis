from datetime import date
import sqlite3
# In order to suppress warning related to forward references
from __future__ import annotations


class Season():
    year: int
    champion_id: str

    def __init__(self, year: int, champion_id: str) -> None:
        self.year = year
        self.champion_id = champion_id

    def insert_season(self) -> None:
        """Insert the season into seasons table"""
        # Connect to SQLite database
        conn = sqlite3.connect('basketball_reference.db')
        cursor = conn.cursor()
        # Insert data into seasons table
        cursor.execute(
            "INSERT INTO seasons (season_id, champion_id) VALUES (?, ?)",
            (self.year, self.champion_id, self.mvp_id, self.roty_id))
        # Commit changes and close connection
        conn.commit()
        conn.close()


class Team():
    id: str
    name: str
    city: str
    state: str

    def __init__(self, id: str, name: str, city: str, state: str):
        self.id = id
        self.name = name
        self.city = city
        self.state = state

    def insert_team(self) -> None:
        """Insert the team into teams table"""
        # Connect to SQLite database
        conn = sqlite3.connect('basketball_reference.db')
        cursor = conn.cursor()
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
            (self.id, self.name, self.city, self.state))
        # Commit changes and close connection
        conn.commit()
        conn.close()


class Player():
    id: str
    name: str
    birthdate: date
    height: int
    weight: int
    shoots: str
    nationality: str
    college: str
    position: list[str]

    def __init__(self, id: str, name: str, birthdate: date, height: int,
                 weight: int, shoots: str, nationality: str, college: str,
                 position: list[str]) -> None:
        self.id = id
        self.name = name
        self.birthdate = birthdate
        self.height = height
        self.weight = weight
        self.shoots = shoots
        self.nationality = nationality
        self.college = college
        self.position = position

    def insert_player(self) -> None:
        """Insert the player into players table"""
        # Connect to SQLite database
        conn = sqlite3.connect('basketball_reference.db')
        cursor = conn.cursor()
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
            (self.id, self.name, self.birthdate.isoformat(), self.height,
             self.weight, self.shoots, self.nationality, self.college))
        # Insert data into player-position table
        for position in self.position:
            cursor.execute(
                "INSERT INTO player_position (id, position) VALUES (?, ?)",
                (self.id, position))
        # Commit changes and close connection
        conn.commit()
        conn.close()


class Coach():
    id: str
    name: str
    birthdate: date
    nationality: str

    def __init__(self, id: str, name: str, birthdate: date, nationality: str) -> None:
        self.id = id
        self.name = name
        self.birthdate = birthdate
        self.nationality = nationality

    def insert_coach(self) -> None:
        """Insert the coach into coaches table"""
        # Connect to SQLite database
        conn = sqlite3.connect('basketball_reference.db')
        cursor = conn.cursor()
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
            (self.id, self.name, self.birthdate.isoformat(), self.height,
             self.nationality))
        # Commit changes and close connection
        conn.commit()
        conn.close()


class Award():
    id: str
    name: str
    season: int
    winner_id: str

    def __init__(self, id: str, name: str, season: int, winner_id: str) -> None:
        self.id = id
        self.name = name
        self.season = season
        self.winner_id = winner_id

    def insert_award(self) -> None:
        """Insert the award into awards table"""
        # Connect to SQLite database
        conn = sqlite3.connect('basketball_reference.db')
        cursor = conn.cursor()
        # Insert data into awards table
        cursor.execute(
            """
            INSERT INTO awards (
                award_id,
                name,
                season_id,
                player_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (self.id, self.name, self.season, self.winner_id))
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
