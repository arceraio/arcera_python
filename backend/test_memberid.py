import uuid
import random

# Wix member IDs are UUID v4 strings e.g. "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
member_pool = []


def generate_member():
    member_id = str(uuid.uuid4())
    member_pool.append(member_id)
    return member_id


def pick_existing_member():
    if not member_pool:
        raise ValueError("No members in pool yet.")
    return random.choice(member_pool)


def get_test_member():
    if not member_pool or random.random() < 0.5:
        return generate_member()
    return pick_existing_member()
