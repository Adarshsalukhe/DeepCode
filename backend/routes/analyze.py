from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.llm import chat
from services.stream_utils import stream_clean
from services.auth import verify_token

router = APIRouter()

ALLOWED_LANGUAGES = {"python","javascript","typescript","rust","go","cpp","c","ruby","html","sql"}
MAX_CODE_LENGTH   = 8000


class AnalyzeRequest(BaseModel):
    code: str
    language: str

    @field_validator("code")
    def code_not_empty(cls, v):
        v = v.strip()
        if not v: raise ValueError("Code cannot be empty.")
        if len(v) > MAX_CODE_LENGTH: raise ValueError("Code too long.")
        return v

    @field_validator("language")
    def lang_allowed(cls, v):
        if v not in ALLOWED_LANGUAGES: raise ValueError("Unsupported language.")
        return v


# ── Complexity Analyzer ───────────────────────────────────────────────────────

COMPLEXITY_SYSTEM = (
    "You are an expert algorithm analyst. Analyse code complexity precisely.\n"
    "RULES:\n"
    "1. Write in sentence case. Never all-caps.\n"
    "2. Use exact ## section headers.\n"
    "3. Be precise and concise. No padding.\n"
    "4. Always justify your complexity claims with the specific loop/recursion that drives it."
)

def complexity_prompt(code: str, language: str) -> str:
    return (
        f"Analyse the time and space complexity of this {language} code.\n\n"
        f"```{language}\n{code}\n```\n\n"
        "Use EXACTLY these sections:\n\n"
        "## Time Complexity\n"
        "State the Big O notation. Then explain in 1-2 sentences which specific loop, recursion, or operation drives it.\n\n"
        "## Space Complexity\n"
        "State the Big O notation. Then explain what data structures or call stack usage drives it.\n\n"
        "## Breakdown\n"
        "For each significant function or block, one line each:\n"
        "`function_name` — O(?) because [one short reason]\n\n"
        "## How to Improve\n"
        "If a better complexity is achievable, explain how in 2-3 sentences. If already optimal, write: This implementation is already optimal for this problem.\n\n"
        "Stop here."
    )


def stream_complexity(code, language):
    stream = chat(
        messages=[
            {"role": "system", "content": COMPLEXITY_SYSTEM},
            {"role": "user",   "content": complexity_prompt(code, language)},
        ],
        stream=True,
        temperature=0.2,
    )
    for token in stream_clean(stream):
        yield f"data: {token}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/complexity")
async def complexity(req: AnalyzeRequest, user=Depends(verify_token)):
    return StreamingResponse(
        stream_complexity(req.code, req.language),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Bug Finder ────────────────────────────────────────────────────────────────

BUG_SYSTEM = (
    "You are a senior code reviewer specialising in finding bugs proactively.\n"
    "RULES:\n"
    "1. Write in sentence case. Never all-caps.\n"
    "2. Only report real bugs — issues that will cause wrong results, crashes, or security problems.\n"
    "3. Do not report style issues, missing comments, or minor refactors as bugs.\n"
    "4. Use exact ## section headers.\n"
    "5. If there are no bugs, say so clearly."
)

def bugfinder_prompt(code: str, language: str) -> str:
    return (
        f"Find all bugs in this {language} code. No error message is provided — proactively identify issues.\n\n"
        f"```{language}\n{code}\n```\n\n"
        "Use EXACTLY these sections:\n\n"
        "## Summary\n"
        "One sentence: how many bugs found and overall severity (none / minor / moderate / critical).\n\n"
        "## Bugs Found\n"
        "For each bug use this exact format:\n\n"
        "**Bug N — [short name]** (severity: low/medium/high)\n"
        "`the problematic line` — what goes wrong and why\n"
        "Fix: `corrected version of the line`\n\n"
        "If no bugs found, write: No bugs found. The code logic appears correct within its stated assumptions.\n\n"
        "## What Was Checked\n"
        "List the categories you checked, one per line starting with -:\n"
        "- Off-by-one errors\n"
        "- Null/undefined/None handling\n"
        "- Type mismatches\n"
        "- Infinite loop conditions\n"
        "- Edge cases (empty input, single element, duplicates)\n"
        "- Integer overflow / underflow\n"
        "- Resource leaks\n\n"
        "Stop here."
    )


def stream_bugs(code, language):
    stream = chat(
        messages=[
            {"role": "system", "content": BUG_SYSTEM},
            {"role": "user",   "content": bugfinder_prompt(code, language)},
        ],
        stream=True,
        temperature=0.2,
    )
    for token in stream_clean(stream):
        yield f"data: {token}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/bugs")
async def find_bugs(req: AnalyzeRequest, user=Depends(verify_token)):
    return StreamingResponse(
        stream_bugs(req.code, req.language),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
