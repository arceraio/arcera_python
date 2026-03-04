from supabase_client import get_supabase

BUCKET = "img"


def upload_bytes(storage_path: str, data: bytes, content_type: str) -> str:
    get_supabase().storage.from_(BUCKET).upload(
        storage_path, data, {"content-type": content_type, "upsert": "true"}
    )
    return storage_path


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str | None:
    try:
        res = get_supabase().storage.from_(BUCKET).create_signed_url(
            storage_path, expires_in
        )
        return res.get("signedURL") or res.get("signed_url")
    except Exception:
        return None
