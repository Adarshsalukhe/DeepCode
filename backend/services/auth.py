"""
Supabase JWT verification.
Every API route depends on this — if the token is missing or invalid,
the request is rejected with 401 before touching the LLM.
"""

import os
import httpx
from fastapi import HTTPException, Header

SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


async def verify_token(authorization: str = Header(default=None)):
    """
    FastAPI dependency. Use with Depends(verify_token) on any route.
    Returns the Supabase user object on success.
    Raises 401 if token is missing, invalid, or expired.
    """

    # If Supabase is not configured (local dev), skip verification
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
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
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_SERVICE_KEY,
                },
            )

        if res.status_code == 200:
            return res.json()  # user object: { id, email, ... }

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please sign in again."
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Auth service timeout. Please try again."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth error: {str(e)}")
