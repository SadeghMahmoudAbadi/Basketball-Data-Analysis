from datetime import date
import sqlite3


class Player():
    id: str
    name: str
    position: list[str]
    shoots: str
    height: int
    weight: int
    birthdate: date

    def __init__(self, id: str, name: str, position: list[str], shoots: str,
                 height: int, weight: int, birthdate: date) -> None:
        self.id = id
        self.name = name
        self.position = position
        self.shoots = shoots
        self.height = height
        self.weight = weight
        self.birthdate = birthdate

    def insert_player(self) -> None:
        # Connect to SQLite database
        conn = sqlite3.connect('basketball_reference.db')
        cursor = conn.cursor()
        # Insert data into players table
        cursor.execute(
            """
            INSERT INTO players (id, name, shoots, height, weight, birthdate)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.id, self.name, self.shoots, self.height, self.weight, self.birthdate.isoformat()))
        # Insert data into player-position table
        for position in self.position:
            cursor.execute(
                "INSERT INTO player_position (id, position) VALUES (?, ?)",
                (self.id, position))
        # Commit changes and close connection
        conn.commit()
        conn.close()
