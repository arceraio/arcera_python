import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'arcera.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (member_id TEXT PRIMARY KEY)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id       TEXT    NOT NULL REFERENCES users(member_id),
                class_id        INTEGER NOT NULL,
                purchase_year   INTEGER,
                cost            REAL,
                count           INTEGER NOT NULL DEFAULT 1,
                filepath        TEXT,
                room_id         INTEGER,
                crop_path       TEXT,
                x1              INTEGER,
                y1              INTEGER,
                x2              INTEGER,
                y2              INTEGER,
                duplicate_of    INTEGER,
                created_at      TEXT    NOT NULL,
                modified_at     TEXT    NOT NULL
            )
        """)
        for col, col_type in [
            ("crop_path", "TEXT"),
            ("x1", "INTEGER"),
            ("y1", "INTEGER"),
            ("x2", "INTEGER"),
            ("y2", "INTEGER"),
            ("duplicate_of", "INTEGER"),
        ]:
            try:
                conn.execute(f"ALTER TABLE items ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.commit()


def find_duplicate(member_id: str, class_id: int, x1: int, y1: int, x2: int, y2: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM items "
            "WHERE member_id = ? AND class_id = ? AND x1 = ? AND y1 = ? AND x2 = ? AND y2 = ?",
            (member_id, class_id, x1, y1, x2, y2)
        ).fetchone()
    return row["id"] if row else None


def create_item(member_id: str, class_id: int, purchase_year: int, cost: float, filepath: str, room_id: int, crop_path: str = None, x1: int = None, y1: int = None, x2: int = None, y2: int = None, duplicate_of: int = None):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO items (member_id, class_id, purchase_year, cost, filepath, room_id, crop_path, x1, y1, x2, y2, duplicate_of, created_at, modified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (member_id, class_id, purchase_year, cost, filepath, room_id, crop_path, x1, y1, x2, y2, duplicate_of, now, now)
        )
        conn.commit()
        return cursor.lastrowid


def update_item(item_id: int, purchase_year: int = None, cost: float = None):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        if purchase_year is not None:
            conn.execute("UPDATE items SET purchase_year = ?, modified_at = ? WHERE id = ?",
                         (purchase_year, now, item_id))
        if cost is not None:
            conn.execute("UPDATE items SET cost = ?, modified_at = ? WHERE id = ?",
                         (cost, now, item_id))
        conn.execute("UPDATE items SET count = count + 1, modified_at = ? WHERE id = ?",
                     (now, item_id))
        conn.commit()


def get_items(member_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, class_id, purchase_year, cost, count, filepath, room_id, crop_path, x1, y1, x2, y2, duplicate_of, created_at, modified_at "
            "FROM items WHERE member_id = ? ORDER BY created_at DESC",
            (member_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def delete_item(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()


def verify_member(member_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT member_id FROM users WHERE member_id = ?", (member_id,)
        ).fetchone()
    return row is not None


def upsert_user(member_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (member_id) VALUES (?)",
            (member_id,)
        )
        conn.commit()
    return member_id
