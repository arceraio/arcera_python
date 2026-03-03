from datetime import datetime, timezone
from supabase_client import get_supabase


def init_db():
    pass  # Schema is managed via Supabase migrations


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def find_duplicate(member_id: str, class_id: int, x1: int, y1: int, x2: int, y2: int):
    coord = "{%d,%d,%d,%d}" % (x1, y1, x2, y2)  # PostgreSQL array literal
    result = (
        get_supabase()
        .table("item")
        .select("id")
        .eq("user_id", member_id)
        .eq("class_id", class_id)
        .filter("coordinate", "eq", coord)
        .limit(1)
        .execute()
    )
    return result.data[0]["id"] if result.data else None


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def create_item(member_id: str, class_id: int, purchase_year: int, cost: float,
                filepath: str, room_id: int, name: str = None, crop_path: str = None,
                x1: int = None, y1: int = None, x2: int = None, y2: int = None,
                duplicate_of: int = None):
    now = datetime.now(timezone.utc).isoformat()
    coordinate = [x1, y1, x2, y2] if x1 is not None else None
    result = (
        get_supabase()
        .table("item")
        .insert({
            "user_id":      member_id,
            "class_id":     class_id,
            "purchase_year": purchase_year,
            "cost":         cost,
            "original_url": filepath,
            "room_id":      room_id,
            "name":         name,
            "crop_path":    crop_path,
            "coordinate":   coordinate,
            "duplicate_of": duplicate_of,
            "created_at":   now,
            "modified_at":  now,
        })
        .execute()
    )
    return result.data[0]["id"]


def update_item(item_id: int, purchase_year: int = None, cost: float = None,
                name: str = None, description: str = None,
                count: int = None, room_id: int = None):
    now = datetime.now(timezone.utc).isoformat()
    updates = {"modified_at": now}
    if purchase_year is not None:
        updates["purchase_year"] = purchase_year
    if cost is not None:
        updates["cost"] = cost
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if count is not None:
        updates["count"] = count
    if room_id is not None:
        updates["room_id"] = room_id
    get_supabase().table("item").update(updates).eq("id", item_id).execute()


def delete_item(item_id: int):
    get_supabase().table("item").delete().eq("id", item_id).execute()


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_items(member_id: str):
    result = (
        get_supabase()
        .table("item")
        .select("*")
        .eq("user_id", member_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = []
    for row in result.data:
        coord = row.get("coordinate") or []
        rows.append({
            "id":            row["id"],
            "class_id":      row["class_id"],
            "purchase_year": row.get("purchase_year"),
            "cost":          row.get("cost"),
            "count":         row.get("count") or 1,
            "filepath":      row.get("original_url"),
            "room_id":       row.get("room_id"),
            "crop_path":     row.get("crop_path"),
            "x1": coord[0] if len(coord) > 0 else None,
            "y1": coord[1] if len(coord) > 1 else None,
            "x2": coord[2] if len(coord) > 2 else None,
            "y2": coord[3] if len(coord) > 3 else None,
            "duplicate_of":  row.get("duplicate_of"),
            "name":          row.get("name"),
            "description":   row.get("description"),
            "created_at":    row.get("created_at"),
            "modified_at":   row.get("modified_at"),
        })
    return rows


def get_item_filepath(item_id: int):
    result = (
        get_supabase()
        .table("item")
        .select("original_url")
        .eq("id", item_id)
        .limit(1)
        .execute()
    )
    return result.data[0]["original_url"] if result.data else None


# ---------------------------------------------------------------------------
# User helpers  (auth is handled by Supabase — these are kept for interface
#               compatibility with main.py and the test suite)
# ---------------------------------------------------------------------------

def verify_member(member_id: str) -> bool:
    # JWT validation in auth.py already guarantees the user exists in auth.users
    return True


def upsert_user(member_id: str):
    # User creation is handled by Supabase Auth
    return member_id
