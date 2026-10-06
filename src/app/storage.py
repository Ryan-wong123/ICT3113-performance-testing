"""Local persistent SQLite storage. No cache or bulk dataset import is used."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Iterator

from .categories import CATEGORIES


@dataclass(frozen=True)
class StoredTicket:
    id: int
    ticket_row: int | None
    narrative: str
    category: str
    model: str
    created_at: str


class TicketStore:
    def __init__(self, database_path: str) -> None:
        self._database_path = Path(database_path)

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_row INTEGER,
                    narrative TEXT NOT NULL,
                    category TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def insert(self, ticket_row: int | None, narrative: str, category: str, model: str) -> StoredTicket:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO tickets (ticket_row, narrative, category, model, created_at) VALUES (?, ?, ?, ?, ?)",
                (ticket_row, narrative, category, model, created_at),
            )
            ticket_id = int(cursor.lastrowid)
        return StoredTicket(ticket_id, ticket_row, narrative, category, model, created_at)

    def search(self, query: str, limit: int) -> list[StoredTicket]:
        pattern = f"%{query}%"
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, ticket_row, narrative, category, model, created_at
                FROM tickets
                WHERE narrative LIKE ? COLLATE NOCASE
                ORDER BY id DESC
                LIMIT ?
                """,
                (pattern, limit),
            ).fetchall()
        return [StoredTicket(**dict(row)) for row in rows]

    def category_counts(self) -> dict[str, int]:
        counts = {category: 0 for category in CATEGORIES}
        with self._connection() as connection:
            rows = connection.execute("SELECT category, COUNT(*) AS count FROM tickets GROUP BY category").fetchall()
        counts.update({row["category"]: row["count"] for row in rows})
        return counts
