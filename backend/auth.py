import json
import urllib.request
import jwt
from flask import request
from config import SUPABASE_URL, SUPABASE_JWT_SECRET

_ec_public_key_cache: dict = {}  # kid → key


def _get_ec_public_key(kid: str = None):
    """Fetch and cache EC public keys from Supabase JWKS, matched by kid.
    Falls back to the first available key if kid is None or not found.
    """
    global _ec_public_key_cache
    if kid and kid in _ec_public_key_cache:
        return _ec_public_key_cache[kid]

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
            k_id = k.get("kid")
            key = ECAlgorithm.from_jwk(json.dumps(k))
            if k_id:
                _ec_public_key_cache[k_id] = key

    if not _ec_public_key_cache:
        raise RuntimeError("No EC key found in Supabase JWKS.")

    if kid and kid in _ec_public_key_cache:
        return _ec_public_key_cache[kid]

    return next(iter(_ec_public_key_cache.values()))


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
    kid = unverified_header.get("kid")

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
            public_key = _get_ec_public_key(kid=kid)
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
