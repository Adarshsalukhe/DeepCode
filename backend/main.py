from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
import time
import os

from routes.explain import router as explain_router
from routes.debug import router as debug_router
from routes.challenge import router as challenge_router
from routes.analyze import router as analyze_router

app = FastAPI(
    title="DeepCode API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW   = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

request_log: dict = defaultdict(list)

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    request_log[ip] = [t for t in request_log[ip] if t > window_start]
    if len(request_log[ip]) >= RATE_LIMIT_REQUESTS:
        return True
    request_log[ip].append(now)
    return False

# ── Security middleware ───────────────────────────────────────────────────────
MAX_BODY_SIZE = 20_000

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Skip OPTIONS preflight — let CORS middleware handle it
    if request.method == "OPTIONS":
        return await call_next(request)

    # Block oversized requests
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(status_code=413, content={"detail": "Request too large."})

    # Rate limit by IP
    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()

    if request.url.path.startswith("/api") and is_rate_limited(ip):
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please wait a minute."})

    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    return response

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(explain_router,   prefix="/api")
app.include_router(debug_router,     prefix="/api")
app.include_router(challenge_router, prefix="/api")
app.include_router(analyze_router,   prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
