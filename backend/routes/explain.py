from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.llm import chat
from services.stream_utils import stream_clean
from services.parser import parse_code
from services.sandbox import run_python
from services.prompts import explain_prompt, SYSTEM_EXPLAIN
from services.auth import verify_token

router = APIRouter()

ALLOWED_LANGUAGES = {"python", "javascript", "typescript", "rust", "go", "cpp", "c", "ruby", "html", "sql"}
ALLOWED_LEVELS    = {"beginner", "intermediate", "expert"}
MAX_CODE_LENGTH   = 8000


class ExplainRequest(BaseModel):
    code: str
    language: str
    level: str
    length: str = "medium"

    @field_validator("length")
    def length_allowed(cls, v):
        if v not in {"short", "medium", "detailed"}:
            return "medium"
        return v

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

    @field_validator("level")
    def level_allowed(cls, v):
        if v not in ALLOWED_LEVELS:
            raise ValueError(f"Level must be one of: {', '.join(ALLOWED_LEVELS)}")
        return v


def stream_tokens(code, language, level, ast_summary, exec_output, length="medium"):
    prompt = explain_prompt(code, language, level, ast_summary, exec_output, length)
    stream = chat(
        messages=[
            {"role": "system", "content": SYSTEM_EXPLAIN},
            {"role": "user",   "content": prompt},
        ],
        stream=True,
        temperature=0.5,
    )
    for token in stream_clean(stream):
        yield f"data: {token}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/explain")
async def explain(req: ExplainRequest, user=Depends(verify_token)):
    parsed = parse_code(req.code, req.language)
    exec_output = ""
    if req.language == "python":
        result = run_python(req.code)
        if result["stdout"] and not result["blocked"]:
            exec_output = f"stdout:\n{result['stdout']}"
        if result["stderr"] and not result["blocked"]:
            exec_output += f"\nstderr:\n{result['stderr']}"

    return StreamingResponse(
        stream_tokens(req.code, req.language, req.level, parsed["summary"], exec_output, req.length),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
