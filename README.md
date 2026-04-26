# DeepCode

> AI-powered code understanding platform for developers and learners.

Live at → **[adarshsalukhe.github.io/DeepCode](https://adarshsalukhe.github.io/DeepCode/)**

---

## What It Does

Paste any code and get instant AI-powered analysis — powered by **GPT-OSS 120B** via Groq.

| Mode | Description |
|---|---|
| **Understand** | Line-by-line explanation at beginner, intermediate, or expert level |
| **Debug** | Root cause analysis with mechanical explanation and fix |
| **Complexity** | Time and space complexity with Big O breakdown |
| **Bug Finder** | Proactive bug detection — no error message needed |
| **Challenge** | Mixed quiz — MCQ, complete the function, write a test |

---

## Supported Languages

Python · JavaScript · TypeScript · Rust · Go · C++ · C · Ruby · HTML · SQL

---

## Features

- 🔐 Google and GitHub OAuth via Supabase
- ⚡ Streaming responses — results appear token by token
- 📊 Usage tracking — see who used what in Supabase dashboard
- 🕐 History panel — revisit your last 20 analyses
- 🛡️ Rate limiting, input validation, CORS protection
- 📏 Explanation length control — Short / Medium / Detailed

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | GPT-OSS 120B via Groq API |
| Backend | FastAPI + Python |
| Auth & DB | Supabase |
| Frontend | Vanilla React (single HTML file) |
| Streaming | Server-Sent Events (SSE) |
| Hosting | Railway (backend) + GitHub Pages (frontend) |

---

## Local Development

### Prerequisites
- Python 3.11+
- Groq API key — [console.groq.com](https://console.groq.com)
- Supabase project — [supabase.com](https://supabase.com)

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

ALLOWED_ORIGINS=*
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

Start backend:
```bash
python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend/public
python -m http.server 3000
```

Open `http://localhost:3000`

---

## Supabase Setup

Run this SQL in your Supabase SQL editor:

```sql
create table usage_logs (
  id          uuid default gen_random_uuid() primary key,
  user_id     uuid references auth.users(id),
  user_email  text,
  mode        text,
  language    text,
  level       text,
  code_length int,
  created_at  timestamptz default now()
);

create table user_logins (
  id           uuid default gen_random_uuid() primary key,
  user_id      uuid references auth.users(id),
  user_email   text,
  provider     text,
  logged_in_at timestamptz default now()
);

alter table usage_logs enable row level security;
alter table user_logins enable row level security;

create policy "insert own usage" on usage_logs
  for insert with check (auth.uid() = user_id);

create policy "insert own login" on user_logins
  for insert with check (auth.uid() = user_id);
```

---

## Project Structure

```
DeepCode/
├── backend/
│   ├── main.py                  # FastAPI app + security middleware
│   ├── requirements.txt
│   ├── routes/
│   │   ├── explain.py           # Understand mode
│   │   ├── debug.py             # Debug mode
│   │   ├── challenge.py         # Challenge mode
│   │   └── analyze.py           # Complexity + Bug Finder
│   └── services/
│       ├── llm.py               # Multi-provider LLM client
│       ├── prompts.py           # All prompt templates
│       ├── parser.py            # AST code parser
│       ├── sandbox.py           # Python code executor
│       ├── stream_utils.py      # SSE streaming utilities
│       └── auth.py              # Supabase JWT verification
└── frontend/
    └── public/
        └── index.html           # Entire frontend — single file
```

---

## Security

- JWT verification on every API route via Supabase
- Rate limiting — 10 requests per minute per IP
- Input validation — code length, language whitelist, field checks
- CORS locked to frontend domain in production
- API docs disabled in production
- Secrets never in frontend code

---

## Built By

**Adarsh Salukhe** — AI/LLM Engineer

[GitHub](https://github.com/AdarshSalukhe) · [LinkedIn](https://linkedin.com/in/adarshsalukhe)
