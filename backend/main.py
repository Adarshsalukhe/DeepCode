from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta
import time
import os

from routes.explain import router as explain_router
from routes.debug import router as debug_router
from routes.challenge import router as challenge_router
from routes.analyze import router as analyze_router

app = FastAPI(
    title="DeepCode Tutor API",
    docs_url=None,      # disable /docs in production
    redoc_url=None,     # disable /redoc in production
    openapi_url=None,   # disable /openapi.json — hides your API structure
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# IMPORTANT: replace "*" with your actual frontend URL before going live
# e.g. "https://yourname.github.io" or "https://yourdomain.com"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
# Tracks requests per IP. Stored in memory (resets on server restart).
# For production, swap this with Redis for persistence across restarts.

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))  # max requests
RATE_LIMIT_WINDOW   = int(os.getenv("RATE_LIMIT_WINDOW", "60"))    # per N seconds

# { ip: [(timestamp), ...] }
request_log: dict = defaultdict(list)

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Remove requests outside the window
    request_log[ip] = [t for t in request_log[ip] if t > window_start]

    if len(request_log[ip]) >= RATE_LIMIT_REQUESTS:
        return True

    request_log[ip].append(now)
    return False

# ── Request size limiter ──────────────────────────────────────────────────────
MAX_BODY_SIZE = 20_000  # 20KB — no one needs to send more than this

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # 1. Block oversized requests (prevents prompt injection via huge payloads)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request too large."}
        )

    # 2. Rate limit by IP
    ip = request.client.host if request.client else "unknown"

    # Trust X-Forwarded-For from Railway/Vercel proxies
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()

    if request.url.path.startswith("/api") and is_rate_limited(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait a minute before trying again."}
        )

    # 3. Block requests with no Content-Type on POST routes
    if request.method == "POST" and "application/json" not in request.headers.get("content-type", ""):
        return JSONResponse(
            status_code=415,
            content={"detail": "Content-Type must be application/json."}
        )

    response = await call_next(request)

    # 4. Add security headers to every response
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Powered-By"] = ""   # hide server info

    return response

# ── Code size validator ───────────────────────────────────────────────────────
# Import and patch into routes so oversized code is rejected before hitting LLM

from fastapi import Request as FastAPIRequest

MAX_CODE_LENGTH = 8000  # ~200 lines max

def validate_code_length(code: str):
    if len(code) > MAX_CODE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Code is too long ({len(code)} chars). Maximum is {MAX_CODE_LENGTH} characters."
        )

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(explain_router,   prefix="/api")
app.include_router(debug_router,     prefix="/api")
app.include_router(challenge_router, prefix="/api")
app.include_router(analyze_router,   prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}   # don't expose model/provider info publicly
