import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from store import init_db, upsert_user, create_item, get_conn
from test_memberid import generate_member, pick_existing_member, get_test_member

# YOLO class IDs relevant to household items
CHAIR      = 56
COUCH      = 57
BED        = 59
DINING_TBL = 60
TV         = 62

# Room IDs matching ROOMS list in main.py
LIVING_ROOM = 1
BEDROOM     = 2
DINING_ROOM = 5
OFFICE      = 6


def verify(item_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    print(f"  DB row -> id={row['id']} | member={row['member_id']} | class={row['class_id']} "
          f"| year={row['purchase_year']} | cost=${row['cost']} "
          f"| room={row['room_id']} | file={os.path.basename(row['filepath'])}")


def scenario_new_user_first_item():
    print("\n[1] New user scans a chair in the living room")
    member_id = generate_member()
    upsert_user(member_id)
    item_id = create_item(member_id, CHAIR, 2021, 349.99, "uploads/furniture_1.jpeg", LIVING_ROOM)
    verify(item_id)


def scenario_same_user_second_item():
    print("\n[2] Same user scans a couch in the living room")
    member_id = pick_existing_member()
    item_id = create_item(member_id, COUCH, 2020, 899.00, "uploads/furniture_2.jpg", LIVING_ROOM)
    verify(item_id)


def scenario_new_user_different_room():
    print("\n[3] New user scans a bed in the bedroom")
    member_id = generate_member()
    upsert_user(member_id)
    item_id = create_item(member_id, BED, 2019, 1200.00, "uploads/furniture_3.jpg", BEDROOM)
    verify(item_id)


def scenario_random_member_scans_tv():
    print("\n[4] Random member (new or existing) scans a TV in the office")
    member_id = get_test_member()
    upsert_user(member_id)
    item_id = create_item(member_id, TV, 2023, 650.00, "uploads/furniture_4.jpg", OFFICE)
    verify(item_id)


if __name__ == "__main__":
    init_db()

    scenario_new_user_first_item()
    scenario_same_user_second_item()
    scenario_new_user_different_room()
    scenario_random_member_scans_tv()

    print("\n--- users in pool ---")
    from test_memberid import member_pool
    for m in member_pool:
        print(f"  {m}")
