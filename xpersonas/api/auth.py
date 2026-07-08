"""API key authentication middleware."""

from __future__ import annotations

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from xpersonas.storage.database import Database

_API_KEY_HEADER = "X-API-Key"


def generate_api_key() -> str:
    """Generate a new API key."""
    return f"sa_{secrets.token_hex(32)}"


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def verify_api_key(
    x_api_key: Annotated[str, Header()],
    db: Database = None,
) -> str:
    """Verify API key and return tenant_id."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    key_hash = hash_key(x_api_key)
    row = db.fetchone(
        "SELECT tenant_id FROM api_keys WHERE key_hash = ? AND is_active = 1",
        (key_hash,),
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return row["tenant_id"]
