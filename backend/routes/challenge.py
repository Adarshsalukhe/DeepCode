import json
import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from services.llm import chat
from services.parser import parse_code
from services.auth import verify_token

router = APIRouter()

ALLOWED_LANGUAGES = {"python","javascript","typescript","rust","go","cpp","c","ruby","html","sql"}
ALLOWED_LEVELS    = {"beginner","intermediate","expert"}
MAX_CODE_LENGTH   = 8000

SYSTEM_CHALLENGE = (
    "You are a programming quiz generator. "
    "You ONLY output valid JSON arrays. "
    "No explanation, no markdown, no text outside the JSON array. "
    "Start your response with [ and end with ]."
)


class ChallengeRequest(BaseModel):
    code: str
    language: str
    level: str

    @field_validator("code")
    def code_not_empty(cls, v):
        v = v.strip()
        if not v: raise ValueError("Code cannot be empty.")
        if len(v) > MAX_CODE_LENGTH: raise ValueError("Code too long.")
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


def build_prompt(code: str, language: str, level: str) -> str:
    return f"""Generate exactly 5 quiz questions about this {language} code. Level: {level}.

Code:
```{language}
{code}
```

Output ONLY a JSON array with exactly 5 objects. Mix types: 3 mcq + 1 complete_function + 1 write_test.

JSON format:
[
  {{
    "type": "mcq",
    "question": "question text?",
    "options": ["A", "B", "C", "D"],
    "correct": 0,
    "explanation": "why correct"
  }},
  {{
    "type": "complete_function",
    "question": "Complete this function:",
    "starter_code": "def example(x):\\n    # YOUR CODE HERE\\n    pass",
    "solution": "def example(x):\\n    return x * 2",
    "explanation": "explanation"
  }},
  {{
    "type": "write_test",
    "question": "Write a unit test for this function:",
    "function_to_test": "def add(a, b):\\n    return a + b",
    "test_starter": "def test_add():\\n    # write assertions\\n    pass",
    "sample_solution": "def test_add():\\n    assert add(2,3)==5",
    "explanation": "explanation"
  }}
]

Output ONLY the JSON array. Start with ["""


def extract_json(raw: str) -> str:
    """Robustly extract JSON array from model output."""
    # Remove think blocks
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    # Remove markdown fences
    raw = re.sub(r"```(?:json)?", "", raw)
    raw = raw.strip()
    # Find array boundaries
    start = raw.find("[")
    if start == -1:
        raise ValueError("No JSON array found")
    # Find matching closing bracket
    depth = 0
    end = -1
    for i, ch in enumerate(raw[start:], start):
        if ch == "[": depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        # Try rfind as fallback
        end = raw.rfind("]")
    if end == -1 or end <= start:
        raise ValueError("No closing bracket found")
    return raw[start:end+1]


@router.post("/challenge/generate")
async def generate_challenge(req: ChallengeRequest, user=Depends(verify_token)):
    prompt = build_prompt(req.code, req.language, req.level)

    response = chat(
        messages=[
            {"role": "system", "content": SYSTEM_CHALLENGE},
            {"role": "user",   "content": prompt},
        ],
        stream=False,
        temperature=0.6,
        max_tokens=3000,  # increased to fit 5 questions
    )

    raw = response.choices[0].message.content

    try:
        cleaned = extract_json(raw)
        questions = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM returned invalid JSON: {raw[:400]}"
        )

    if not isinstance(questions, list) or len(questions) == 0:
        raise HTTPException(status_code=500, detail="LLM returned empty questions list.")

    # Lenient validation — just ensure minimum fields exist
    valid = []
    for q in questions:
        if not isinstance(q, dict): continue
        if "question" not in q: continue
        # Set defaults for missing fields
        q.setdefault("type", "mcq")
        q.setdefault("explanation", "")
        if q["type"] == "mcq":
            q.setdefault("options", ["A", "B", "C", "D"])
            q.setdefault("correct", 0)
        elif q["type"] == "complete_function":
            q.setdefault("starter_code", "# write your solution here")
            q.setdefault("solution", "")
        elif q["type"] == "write_test":
            q.setdefault("function_to_test", "")
            q.setdefault("test_starter", "# write your test here")
            q.setdefault("sample_solution", "")
        valid.append(q)

    if not valid:
        raise HTTPException(status_code=500, detail="No valid questions generated.")

    return {"questions": valid[:5]}
