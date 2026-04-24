from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.llm import chat
from services.stream_utils import stream_clean
from services.prompts import debug_prompt, SYSTEM_DEBUG
from services.auth import verify_token

router = APIRouter()

ALLOWED_LANGUAGES = {"python", "javascript", "typescript", "rust", "go", "cpp", "c", "ruby", "html", "sql"}
MAX_CODE_LENGTH   = 8000


class DebugRequest(BaseModel):
    code: str
    language: str
    error: str

    @field_validator("code")
    def code_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Code cannot be empty.")
        if len(v) > MAX_CODE_LENGTH:
            raise ValueError(f"Code too long. Max {MAX_CODE_LENGTH} characters.")
        return v

    @field_validator("language")
    def language_allowed(cls, v):
        if v not in ALLOWED_LANGUAGES:
            raise ValueError(f"Language must be one of: {', '.join(ALLOWED_LANGUAGES)}")
        return v

    @field_validator("error")
    def error_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Error message cannot be empty.")
        if len(v) > 500:
            raise ValueError("Error message too long. Max 500 characters.")
        return v


def stream_debug(code, language, error):
    prompt = debug_prompt(code, language, error)
    stream = chat(
        messages=[
            {"role": "system", "content": SYSTEM_DEBUG},
            {"role": "user",   "content": prompt},
        ],
        stream=True,
        temperature=0.3,
    )
    for token in stream_clean(stream):
        yield f"data: {token}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/debug")
async def debug(req: DebugRequest, user=Depends(verify_token)):
    return StreamingResponse(
        stream_debug(req.code, req.language, req.error),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
