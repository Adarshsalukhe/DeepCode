import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Switch provider via LLM_PROVIDER env variable
# Options: "gemini" | "groq" | "cerebras" | "ollama"
PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

MODELS = {
    "gemini":   "gemini-2.0-flash",
    "groq":     "openai/gpt-oss-120b",
    "cerebras": "llama-3.3-70b",
    "ollama":   os.getenv("OLLAMA_MODEL", "deepseek-coder:6.7b"),
}

BASE_URLS = {
    "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq":     "https://api.groq.com/openai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "ollama":   os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
}

API_KEYS = {
    "gemini":   os.getenv("GEMINI_API_KEY", ""),
    "groq":     os.getenv("GROQ_API_KEY", ""),
    "cerebras": os.getenv("CEREBRAS_API_KEY", ""),
    "ollama":   "ollama",
}


def get_client() -> OpenAI:
    """
    All 4 providers are OpenAI-compatible.
    Switching provider = change LLM_PROVIDER in .env, nothing else.
    """
    provider = PROVIDER if PROVIDER in BASE_URLS else "gemini"
    return OpenAI(
        api_key=API_KEYS[provider],
        base_url=BASE_URLS[provider],
    )


def get_model() -> str:
    return MODELS.get(PROVIDER, MODELS["gemini"])


def chat(messages: list, stream: bool = False, temperature: float = 0.4, max_tokens: int = 2000):
    """
    Single unified chat call — works identically across all providers.
    Routes to whichever provider is set in LLM_PROVIDER env variable.
    """
    client = get_client()
    return client.chat.completions.create(
        model=get_model(),
        messages=messages,
        stream=stream,
        temperature=temperature,
        max_tokens=max_tokens,
    )
