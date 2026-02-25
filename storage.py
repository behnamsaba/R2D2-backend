import json
import os
import sqlite3
from typing import Any, Dict, List, Optional


def get_database_path() -> str:
    configured_path = os.environ.get("DATABASE_PATH")
    if configured_path:
        return configured_path

    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "r2d2.sqlite3")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(get_database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature TEXT NOT NULL,
                input_json TEXT NOT NULL,
                output_json TEXT NOT NULL,
                user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        if not _column_exists(connection, "generations", "user_id"):
            connection.execute("ALTER TABLE generations ADD COLUMN user_id INTEGER")
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_generations_feature_created_at
            ON generations(feature, created_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_generations_user_feature_created_at
            ON generations(user_id, feature, created_at DESC)
            """
        )
        connection.commit()


def save_generation(
    feature: str,
    input_payload: Dict[str, Any],
    output_payload: Dict[str, Any],
    user_id: Optional[int] = None,
) -> int:
    input_json = json.dumps(input_payload, ensure_ascii=False)
    output_json = json.dumps(output_payload, ensure_ascii=False)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO generations (feature, input_json, output_json, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (feature, input_json, output_json, user_id),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_generations(
    feature: Optional[str] = None, limit: int = 20, user_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(limit, 100))
    query = "SELECT id, feature, input_json, output_json, created_at FROM generations"
    params: List[Any] = []
    where_clauses: List[str] = []

    if user_id is not None:
        where_clauses.append("user_id = ?")
        params.append(user_id)

    if feature:
        where_clauses.append("feature = ?")
        params.append(feature)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(safe_limit)

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    history: List[Dict[str, Any]] = []
    for row in rows:
        try:
            input_payload = json.loads(row["input_json"])
        except json.JSONDecodeError:
            input_payload = {}

        try:
            output_payload = json.loads(row["output_json"])
        except json.JSONDecodeError:
            output_payload = {}

        history.append(
            {
                "id": row["id"],
                "feature": row["feature"],
                "input": input_payload,
                "output": output_payload,
                "createdAt": row["created_at"],
            }
        )

    return history


def create_user(email: str, password_hash: str) -> Dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (email, password_hash)
            VALUES (?, ?)
            """,
            (email, password_hash),
        )
        connection.commit()
        user_id = int(cursor.lastrowid)

    user = get_user_by_id(user_id)
    return user if user else {"id": user_id, "email": email}


def _normalize_user(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "passwordHash": row["password_hash"],
        "createdAt": row["created_at"],
    }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE lower(email) = lower(?)
            """,
            (email,),
        ).fetchone()

    if row is None:
        return None
    return _normalize_user(row)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None
    return _normalize_user(row)
