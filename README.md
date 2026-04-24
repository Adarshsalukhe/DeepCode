# DeepCode Tutor

AI-powered code understanding engine. Paste any code, get a deep explanation at your level.
Powered by **Llama 3.3 70B** via Groq (free, ~0.5s response).

---

## Features

- **Understand mode** — explains any code at beginner / intermediate / expert level with streaming output
- **Debug mode** — root cause analysis, not just a fix
- **Challenge mode** — fresh AI-generated quiz questions every time, based on YOUR code

---

## Stack

| Layer     | Tech                              |
|-----------|-----------------------------------|
| LLM       | Llama 3.3 70B via Groq (free)     |
| Local dev | Ollama + DeepSeek Coder 6.7B      |
| Backend   | FastAPI + SSE streaming           |
| Parser    | Python AST + regex chunker        |
| Sandbox   | Python subprocess (safe)          |
| Frontend  | React + Monaco Editor             |

---

## Setup — Day 1 (takes ~10 minutes)

### 1. Get a free Groq API key
Go to https://console.groq.com → sign up → create API key → copy it

### 2. Backend

```bash
cd backend
pip install -r requirements.txt

# Add your key
cp .env .env.local
# Edit .env and paste your GROQ_API_KEY

uvicorn main:app --reload --port 8000
```

Visit http://localhost:8000/health — should return `{"status":"ok"}`

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

App opens at http://localhost:3000

---

## Switch to fully local (no API key)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a code model
ollama pull deepseek-coder:6.7b

# In backend/.env
LLM_PROVIDER=ollama
```

No internet required, zero cost. Slightly slower than Groq.

---

## Project structure

```
deepcode-tutor/
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── routes/
│   │   ├── explain.py           # SSE streaming explanation
│   │   ├── debug.py             # SSE streaming debug
│   │   └── challenge.py        # Quiz generation endpoint
│   ├── services/
│   │   ├── llm.py               # Groq / Ollama switcher
│   │   ├── parser.py            # AST + regex code chunker
│   │   ├── sandbox.py           # Safe Python execution
│   │   └── prompts.py           # All LLM prompt templates
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── hooks/
        │   ├── useStream.js      # SSE streaming hook
        │   └── useChallenge.js   # Quiz fetch hook
        └── components/
            ├── Header.jsx
            ├── EditorPanel.jsx   # Left: code editor
            ├── ExplainPanel.jsx  # Right: streaming output
            └── ChallengePanel.jsx # Right: dynamic quiz
```

---

## Week 2 improvements (after Day 7)

- Swap `<textarea>` for Monaco Editor (`@monaco-editor/react`)
- Add shareable permalink per code snippet
- Deploy backend to Railway, frontend to Vercel
- Record demo video with a real algorithm (merge sort, Dijkstra)
