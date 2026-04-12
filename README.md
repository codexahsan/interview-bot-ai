# 🤖 Interview Bot AI API: Enterprise RAG & Interview System

An **Enterprise-Grade AI Interviewing and Resume Analysis Platform** using advanced RAG, PII masking, and adaptive AI interviews.

---

## ✨ Key Features

- 🔒 PII Masking with Redis Vault  
- 🧠 Advanced RAG (Qdrant + BM25 + Reranker)  
- 🎙️ AI Interviewer (dynamic Q&A + scoring + tips)  
- ⚡ Redis Caching (history + LLM responses)  
- 📂 Clean FastAPI Architecture  
- 🖥️ Simple Frontend (Tailwind + JS)  

---

## 🛠️ Tech Stack

- FastAPI (Backend)
- PostgreSQL (Database)
- Qdrant (Vector DB)
- Redis (Cache)
- Google Gemini (LLM)
- LangChain
- Presidio (PII Masking)

---

## 🚀 Setup

### 1. Clone
```
git clone https://github.com/codexahsan/interview-bot-ai.git
cd interview-bot-ai
```

### 2. Virtual Env
```
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install
```
pip install -r requirements.txt
```

### 4. .env
```
GOOGLE_API_KEY=[GCP_API_KEY]
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/resume_db
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 5. Run
```
uvicorn backend.app.main:app --reload
```

---

## 🔌 API

- POST /resume/upload  
- POST /chat/new/{resume_id}  
- POST /interview/start  
- POST /interview/answer  
- GET /chat/{session_id}/history  

---

## 📝 License
MIT
