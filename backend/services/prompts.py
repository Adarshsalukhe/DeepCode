"""
Prompts designed to produce code-annotated explanations.
Format mirrors the sketch: show each line of code with a short annotation next to it.
"""

# ── System prompts ────────────────────────────────────────────────────────────

SYSTEM_EXPLAIN = (
    "You are a concise senior engineer explaining code.\n\n"
    "CRITICAL FORMATTING RULES — violations are not acceptable:\n"
    "1. Use normal sentence case throughout. Example: 'This function searches the list' not 'THIS FUNCTION SEARCHES THE LIST'. Every single sentence must be lowercase except the first word.\n"
    "2. Line by Line section format: each entry is ONE line only — the code in backticks, a dash, then ONE short phrase. No sub-bullets under each line.\n"
    "   Good: `x = 5` — assigns integer 5 to variable x\n"
    "   Bad: `x = 5` followed by 3 bullet points explaining it\n"
    "3. Be concise. One annotation per line. Never expand a simple line into multiple bullets.\n"
    "4. Only reference what is literally in the code.\n"
    "5. Use the EXACT ## section headers. No extras.\n"
    "6. Stop after the last section. No closing remarks."
)

SYSTEM_DEBUG = (
    "You are a senior engineer doing root cause analysis.\n\n"
    "CRITICAL FORMATTING RULES:\n"
    "1. Use normal sentence case throughout. Never all-caps. Example: 'The variable z is undefined' not 'THE VARIABLE Z IS UNDEFINED'.\n"
    "2. Root cause must explain WHY mechanically in 2-3 sentences max.\n"
    "3. The Fix section MUST show complete corrected code inside ```language fences.\n"
    "4. Only analyse what is shown. Do not invent.\n"
    "5. Use the EXACT ## section headers given.\n"
    "6. If the error does not match the code, say so explicitly."
)

SYSTEM_CHALLENGE = (
    "You are an expert programming educator creating a mixed-format quiz.\n\n"
    "STRICT RULES:\n"
    "1. Return ONLY a valid JSON array. No markdown, no explanation, no text outside the array.\n"
    "2. Every question must relate directly to the provided code.\n"
    "3. Mix question types as instructed — do not use only one type.\n"
    "4. For complete_function type: the starter code must be valid syntax with a clear gap to fill.\n"
    "5. For write_test type: the function shown must come from the provided code.\n"
    "6. Explanations must cite specific lines from the code.\n"
    "7. Write in sentence case. Never all-caps."
)


# ── Level tone ────────────────────────────────────────────────────────────────

LEVEL_TONE = {
    "beginner": (
        "LEVEL: Beginner — person is new to programming.\n"
        "- Use plain English. No jargon without explanation.\n"
        "- For each code line: explain what it does like explaining to a 10-year-old.\n"
        "- Keep every annotation under 15 words."
    ),
    "intermediate": (
        "LEVEL: Intermediate — person knows basics, wants design insight.\n"
        "- Skip obvious lines. Focus on non-trivial logic.\n"
        "- For each block: explain the design decision and any tradeoff.\n"
        "- Mention time/space complexity where relevant."
    ),
    "expert": (
        "LEVEL: Expert — senior engineer, peer review tone.\n"
        "- Only cover non-trivial decisions, invariants, and correctness risks.\n"
        "- Call out edge cases, overflow risks, missing validations.\n"
        "- Name stdlib alternatives where better options exist.\n"
        "- Be critical and dense. Skip anything self-evident."
    ),
}


# ── Prompt builders ───────────────────────────────────────────────────────────

def explain_prompt(code: str, language: str, level: str, ast_summary: str, execution_output: str = "", length: str = "medium") -> str:
    tone = LEVEL_TONE.get(level, LEVEL_TONE["intermediate"])

    exec_block = ""
    if execution_output:
        exec_block = (
            "\nActual output when run:\n"
            + execution_output.strip() + "\n"
        )

    lines = code.strip().split("\n")
    line_count = len(lines)

    if length == "short":
        length_rule = "Be very brief. Max 120 words total."
    elif length == "detailed":
        length_rule = "Be thorough. Cover every line and all edge cases."
    else:
        if line_count <= 10:
            length_rule = "Code is short. Keep explanation under 180 words."
        elif line_count <= 30:
            length_rule = "Keep explanation under 320 words."
        else:
            length_rule = "Focus on key blocks only. Do not repeat."

    return (
        "Explain this " + language + " code.\n\n"
        + tone + "\n\n"
        + length_rule + "\n"
        + exec_block + "\n"
        "Code:\n"
        "```" + language + "\n"
        + code + "\n"
        "```\n\n"
        "OUTPUT FORMAT RULES — follow exactly:\n"
        "- Use these EXACT section headers with ## prefix\n"
        "- Write in sentence case. Never all-caps.\n"
        "- Each annotation must be on its OWN LINE. Never run multiple annotations together.\n"
        "- Put a blank line between each annotation entry.\n\n"
        "## What It Does\n"
        "One sentence only.\n\n"
        "## Line by Line\n"
        "Format EACH line as its own separate entry like this example — each on a NEW LINE with a blank line between:\n"
        "`def binary_search(arr, target):` — defines the function with two parameters\n"
        "\n"
        "`left, right = 0, len(arr) - 1` — sets start and end boundaries\n"
        "\n"
        "`while left <= right:` — loops until search space is empty\n"
        "\n"
        "Now do the same for this code. Every meaningful line gets its OWN entry on its OWN line with a blank line after it.\n\n"
        "## Watch Out\n"
        "List 1-3 risks, one per line starting with -\n\n"
        "Stop here."
    )


def debug_prompt(code: str, language: str, error: str) -> str:
    return (
        "Debug this " + language + " code.\n\n"
        "Error: " + error + "\n\n"
        "Code:\n"
        "```" + language + "\n"
        + code + "\n"
        "```\n\n"
        "IMPORTANT: Use exactly these section headers with ## prefix. Write in sentence case (not ALL CAPS).\n\n"
        "## Root Cause\n"
        "2-3 sentences. Explain mechanically WHY this error occurs. Quote the responsible line in backticks.\n\n"
        "## The Fix\n"
        "Show the COMPLETE corrected code in a ```" + language + " code block. Then one sentence explaining the change.\n\n"
        "## Prevent It Next Time\n"
        "List 2 techniques. Format each as: **Technique name** — explanation with example.\n\n"
        "Stop here. No extra text."
    )


def challenge_prompt(code: str, language: str, level: str, ast_summary: str) -> str:
    tone = LEVEL_TONE.get(level, LEVEL_TONE["intermediate"])

    return (
        "Generate a mixed-format quiz for this " + language + " code.\n\n"
        + tone + "\n\n"
        "Code:\n"
        "```" + language + "\n"
        + code + "\n"
        "```\n\n"
        "Generate EXACTLY 5 questions with this mix:\n"
        "- 2 questions of type \"mcq\" (multiple choice)\n"
        "- 2 questions of type \"complete_function\" (fill in missing code)\n"
        "- 1 question of type \"write_test\" (write a unit test)\n\n"
        "Return ONLY this JSON array. No markdown. No text before or after:\n"
        "[\n"
        "  {\n"
        "    \"type\": \"mcq\",\n"
        "    \"question\": \"Question text?\",\n"
        "    \"options\": [\"A\", \"B\", \"C\", \"D\"],\n"
        "    \"correct\": 0,\n"
        "    \"explanation\": \"Why this is correct, citing the specific line.\"\n"
        "  },\n"
        "  {\n"
        "    \"type\": \"complete_function\",\n"
        "    \"question\": \"Complete the missing part of this function:\",\n"
        "    \"starter_code\": \"def example(x):\\n    # YOUR CODE HERE\\n    pass\",\n"
        "    \"solution\": \"def example(x):\\n    return x * 2\",\n"
        "    \"explanation\": \"The solution does X because of line Y in the original code.\"\n"
        "  },\n"
        "  {\n"
        "    \"type\": \"write_test\",\n"
        "    \"question\": \"Write a unit test for the function shown:\",\n"
        "    \"function_to_test\": \"def add(a, b):\\n    return a + b\",\n"
        "    \"test_starter\": \"def test_add():\\n    # write your assertions here\\n    pass\",\n"
        "    \"sample_solution\": \"def test_add():\\n    assert add(2, 3) == 5\\n    assert add(-1, 1) == 0\\n    assert add(0, 0) == 0\",\n"
        "    \"explanation\": \"Good tests should cover normal input, edge cases, and boundary values.\"\n"
        "  }\n"
        "]\n\n"
        "correct is 0-based index for mcq. starter_code must have # YOUR CODE HERE comment. "
        "function_to_test must be a real function from the provided code above."
    )


