#!/usr/bin/env python3
"""
export.py - Export a user's items from Supabase to a CSV file.
Usage: python export.py <member_id>
"""

import csv
import sys
import os
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
from store import get_items

EXPORTS_DIR = Path(os.path.join(os.path.dirname(__file__), '..', 'exports'))

ROOMS = [
    "Living Room", "Bedroom", "Kitchen", "Bathroom",
    "Dining Room", "Office", "Garage", "Other",
]

model = YOLO('yolo12n.pt')


def format_dt(iso_str):
    try:
        return datetime.fromisoformat(iso_str).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return iso_str


def export_to_csv(member_id: str) -> str:
    rows = get_items(member_id)

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
            class_id = row["class_id"]
            room_id  = row.get("room_id")
            writer.writerow([
                model.names.get(class_id, f"class_{class_id}"),
                row.get("purchase_year"),
                row.get("cost"),
                row.get("count") or 1,
                row.get("filepath"),
                ROOMS[room_id - 1] if room_id and 1 <= room_id <= len(ROOMS) else room_id,
                format_dt(row.get("created_at")),
                format_dt(row.get("modified_at")),
            ])

    print(f"Exported {len(rows)} row(s) to {csv_path}")
    return str(csv_path)


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
