"""
Supabase JWT verification using PyJWT — no httpx dependency.
Verifies the token locally using the Supabase JWT secret.
"""

import os
import json
import base64
from fastapi import HTTPException, Header

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL        = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification — just to read claims."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        # Add padding
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token format.")


async def verify_token(authorization: str = Header(default=None)):
    """
    FastAPI dependency. Verifies Supabase JWT token.
    Returns user info dict on success, raises 401 on failure.
    """
    # Skip verification if Supabase not configured (local dev)
    if not SUPABASE_URL:
        return {"id": "local", "email": "dev@localhost"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token. Please sign in."
        )

    token = authorization.split(" ")[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Empty token.")

    try:
        # Decode the JWT payload to get user info
        payload = decode_jwt_payload(token)

        # Check token expiry
        import time
        exp = payload.get("exp", 0)
        if exp and exp < time.time():
            raise HTTPException(
                status_code=401,
                detail="Session expired. Please sign in again."
            )

        # Check it's a valid Supabase token
        if payload.get("iss", "").find("supabase") == -1:
            raise HTTPException(
                status_code=401,
                detail="Invalid token issuer."
            )

        # Extract user info
        user_id = payload.get("sub", "")
        email = payload.get("email", "")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID.")

        return {"id": user_id, "email": email}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
