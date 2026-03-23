import json
import urllib.request
import jwt
from flask import request
from config import SUPABASE_URL, SUPABASE_JWT_SECRET

_ec_public_key = None


def _get_ec_public_key():
    """Fetch and cache the EC public key from Supabase JWKS (ES256 projects)."""
    global _ec_public_key
    if _ec_public_key is None:
        try:
            from jwt.algorithms import ECAlgorithm
        except ImportError:
            raise RuntimeError(
                "PyJWT[cryptography] is required for ES256 token verification. "
                "Add PyJWT[cryptography] to requirements.txt."
            )
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        with urllib.request.urlopen(jwks_url, timeout=10) as resp:
            jwks = json.loads(resp.read())
        for k in jwks.get("keys", []):
            if k.get("kty") == "EC":
                _ec_public_key = ECAlgorithm.from_jwk(json.dumps(k))
                break
        if _ec_public_key is None:
            raise RuntimeError("No EC key found in Supabase JWKS.")
    return _ec_public_key


def get_member_id() -> str:
    """Extract and verify the Supabase JWT from the Authorization header.
    Supports ES256 (JWKS) and HS256 (JWT secret) signed tokens.
    Returns the member's UUID (Supabase user ID) on success.
    Raises ValueError on missing or invalid token.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("Missing or malformed Authorization header.")

    token = auth_header.split(" ", 1)[1]

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError as e:
        raise ValueError(f"Malformed token: {e}")

    alg = unverified_header.get("alg", "")

    try:
        if alg == "HS256":
            if not SUPABASE_JWT_SECRET:
                raise ValueError("SUPABASE_JWT_SECRET not configured.")
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            public_key = _get_ec_public_key()
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["ES256"],
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
