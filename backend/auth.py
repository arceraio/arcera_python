import os
import jwt
from flask import request
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")

def get_member_id() -> str:
    """Extract and verify the Supabase JWT from the Authorization header.
    Returns the member's UUID (Supabase user ID) on success.
    Raises ValueError on missing or invalid token.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("Missing or malformed Authorization header.")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")

    member_id = payload.get("sub")
    if not member_id:
        raise ValueError("Token missing subject claim.")

    return member_id
