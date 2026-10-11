# Industrial Product Intelligence Assistant

A starter RAG chatbot for industrial product datasheets and manuals. It uses FastAPI, a browser UI (HTML/CSS/vanilla JavaScript), ChromaDB, Sentence Transformers, Ollama, and optional Tavily web search. No Streamlit.

## Features
- Browser-based chat UI served by FastAPI
- Upload PDF datasheets/manuals
- PDF text extraction with page metadata
- Chunking and embeddings in persistent ChromaDB
- RAG answers with filename/page citations
- Optional Tavily search for web/current questions or when internal documents lack evidence
- Local Ollama LLM generation

## Requirements
- Python 3.10+
- Ollama installed and running
- Tavily API key is optional; web search is disabled without it

## Setup (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull llama3.2:3b
```
Edit `.env` if needed. Set `TAVILY_API_KEY` to enable web search. Then run:
```powershell
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000. On first startup, the embedding model downloads automatically.

## Use
1. Open the web interface.
2. Upload a product datasheet/manual PDF.
3. Ask questions and inspect source cards.
4. Enable Tavily web search for external searches.

## API
- `GET /api/health`
- `POST /api/chat` with JSON `{ "message": "...", "use_web": false }`
- `POST /api/ingest` with multipart PDF upload

## Limitations
This is a learning MVP, not a production industrial decision system. Scanned PDFs need OCR and complex tables may not extract perfectly. Verify critical specifications against original manufacturer documentation. Before production, add authentication, role-based access, document versioning/deletion, malware scanning, audit logs, rate limits, robust table extraction, retrieval evaluation, and trusted-domain controls.
