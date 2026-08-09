import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Keep the database in the backend folder.
DATABASE_PATH = Path(__file__).resolve().parent.parent / "bharatmoney_memory.db"


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    """Create the caller memory table if it does not exist."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS caller_memory (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language_preference TEXT,
                facts TEXT NOT NULL DEFAULT '{}',
                last_interaction TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_user_memory(user_id: str) -> dict[str, Any] | None:
    """Look up a caller's saved memory."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                user_id,
                name,
                language_preference,
                facts,
                last_interaction
            FROM caller_memory
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    try:
        facts = json.loads(row["facts"])
    except (TypeError, json.JSONDecodeError):
        facts = {}

    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "language_preference": row["language_preference"],
        "facts": facts,
        "last_interaction": row["last_interaction"],
    }


def save_user_memory(
    user_id: str,
    name: str,
    language_preference: str | None = None,
    facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Save or update caller memory."""
    now = datetime.now(timezone.utc).isoformat()

    safe_facts = facts or {}

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO caller_memory (
                user_id,
                name,
                language_preference,
                facts,
                last_interaction
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                language_preference = excluded.language_preference,
                facts = excluded.facts,
                last_interaction = excluded.last_interaction
            """,
            (
                user_id,
                name,
                language_preference,
                json.dumps(safe_facts),
                now,
            ),
        )
        connection.commit()

    return {
        "user_id": user_id,
        "name": name,
        "language_preference": language_preference,
        "facts": safe_facts,
        "last_interaction": now,
    }


def update_last_interaction(user_id: str) -> None:
    """Update the last interaction time for an existing caller."""
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE caller_memory
            SET last_interaction = ?
            WHERE user_id = ?
            """,
            (now, user_id),
        )
        connection.commit()