"""
AST-aware code parser.
For Python we use the built-in `ast` module (zero dependencies).
For all other languages we fall back to a smart line-based chunker
that still identifies function/class boundaries via regex patterns.
"""

import ast
import re
from typing import List, Dict


# ── Python parser using built-in ast ──────────────────────────────────────────

def parse_python(code: str) -> List[Dict]:
    """Extract top-level functions and classes with their source."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    chunks = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Only grab top-level definitions (no nested)
            if not any(
                isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                for parent in ast.walk(tree)
                if hasattr(parent, "body") and node in getattr(parent, "body", [])
            ):
                source = ast.get_source_segment(code, node) or ""
                chunks.append({
                    "type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                    "source": source,
                })
    return chunks


# ── Generic regex-based chunker (JS, Go, Rust, etc.) ─────────────────────────

FUNC_PATTERNS = {
    "javascript": r"(?:async\s+)?function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(",
    "typescript": r"(?:async\s+)?function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(",
    "go":         r"func\s+(\w+)\s*\(",
    "rust":       r"fn\s+(\w+)\s*[<(]",
    "java":       r"(?:public|private|protected|static|\s)+\w+\s+(\w+)\s*\(",
    "cpp":        r"\w[\w\s*&]+\s+(\w+)\s*\(",
}

def parse_generic(code: str, language: str) -> List[Dict]:
    """Regex-based function boundary detector for non-Python languages."""
    pattern = FUNC_PATTERNS.get(language)
    if not pattern:
        return []

    chunks = []
    lines = code.split("\n")
    matches = list(re.finditer(pattern, code, re.MULTILINE))

    for i, match in enumerate(matches):
        name = next((g for g in match.groups() if g), "anonymous")
        start_line = code[:match.start()].count("\n") + 1
        end_line = (
            code[:matches[i + 1].start()].count("\n")
            if i + 1 < len(matches)
            else len(lines)
        )
        source = "\n".join(lines[start_line - 1 : end_line])
        chunks.append({
            "type": "function",
            "name": name,
            "line_start": start_line,
            "line_end": end_line,
            "source": source,
        })
    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def parse_code(code: str, language: str) -> dict:
    """
    Returns:
        {
            "chunks": [...],   # list of function/class dicts
            "summary": str,    # one-line structural summary for the LLM prompt
        }
    """
    if language == "python":
        chunks = parse_python(code)
    else:
        chunks = parse_generic(code, language)

    if chunks:
        names = [f"{c['type']} `{c['name']}`" for c in chunks]
        summary = f"Contains {len(chunks)} top-level definition(s): {', '.join(names)}."
    else:
        summary = "No named definitions found — treating as a script or snippet."

    return {"chunks": chunks, "summary": summary}
