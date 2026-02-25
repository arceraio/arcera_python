#!/usr/bin/env python3
"""
export.py - Export a user's items from the SQLite database to a CSV file.
Usage: python export.py <member_id>
"""

import sqlite3
import csv
import sys
import os
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO

DB_PATH    = os.path.join(os.path.dirname(__file__), '..', 'arcera.db')
EXPORTS_DIR = Path(os.path.join(os.path.dirname(__file__), '..', 'exports'))

ROOMS = [
    "Living Room", "Bedroom", "Kitchen", "Bathroom",
    "Dining Room", "Office", "Garage", "Other",
]

model = YOLO('yolo12n.pt')


def format_dt(iso_str):
    """Convert ISO 8601 timestamp to simple YYYY-MM-DD HH:MM:SS."""
    try:
        return datetime.fromisoformat(iso_str).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return iso_str


def export_to_csv(member_id: str) -> str:
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT class_id, purchase_year, cost, count,
                   filepath, room_id, created_at, modified_at
            FROM items
            WHERE member_id = ?
        """, (member_id,))
        rows = cursor.fetchall()

        if not rows:
            print(f"No items found for member_id: {member_id}")
            return None

        safe_id = "".join(c for c in member_id if c.isalnum() or c in ('-', '_'))
        if not safe_id:
            safe_id = "unknown"

        EXPORTS_DIR.mkdir(exist_ok=True)
        csv_path = EXPORTS_DIR / f"user_{safe_id}_items.csv"

        headers = ["item name", "purchase_year", "cost", "count",
                   "filepath", "room", "created", "modified"]

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            for row in rows:
                class_id, purchase_year, cost, count, filepath, room_id, created_at, modified_at = row
                writer.writerow([
                    model.names[class_id],
                    purchase_year,
                    cost,
                    count,
                    filepath,
                    ROOMS[room_id - 1] if room_id and 1 <= room_id <= len(ROOMS) else room_id,
                    format_dt(created_at),
                    format_dt(modified_at),
                ])

        print(f"Exported {len(rows)} row(s) to {csv_path}")
        return str(csv_path)

    except sqlite3.Error as e:
        raise RuntimeError(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python export.py <member_id>")
        sys.exit(1)
    member_id = sys.argv[1].strip()
    if not member_id:
        print("Error: member_id cannot be empty.")
        sys.exit(1)
    export_to_csv(member_id)


if __name__ == "__main__":
    main()
