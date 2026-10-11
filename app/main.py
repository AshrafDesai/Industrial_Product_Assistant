
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel, Field

from app.config import settings
from app.ingestion import ingest_pdf
from app.llm import generate_answer
from app.retrieval import retrieve, get_collection


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Industrial Product Intelligence Assistant",
    version="0.3.0",
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1500)
    use_web: bool = True


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    try:
        indexed_chunks = get_collection().count()
    except Exception:
        indexed_chunks = 0

    return {
        "status": "ok",
        "embedding_model": settings.ollama_embedding_model,
        "answer_model": settings.openrouter_model,
        "openrouter_key_configured": bool(
            settings.openrouter_api_key
        ),
        "indexed_chunks": indexed_chunks,
        "web_search_enabled": True,
    }


@app.post("/api/ingest")
async def upload_pdf(
    file: Annotated[UploadFile, File()],
):
    filename = Path(file.filename or "upload.pdf").name

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    content = await file.read()

    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds 20 MB.",
        )

    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file.",
        )

    destination = settings.upload_dir / filename
    destination.write_bytes(content)

    try:
        result = ingest_pdf(destination)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF indexing failed. Check that Ollama is running "
                f"and '{settings.ollama_embedding_model}' is installed. "
                f"Details: {type(exc).__name__}: {exc}"
            ),
        ) from exc

    return {
        "status": "success",
        **result,
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    question = request.message.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    # Step 1: Search uploaded PDF documents.
    try:
        internal_hits = retrieve(question)

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local document search failed. Check Ollama and "
                f"'{settings.ollama_embedding_model}'. "
                f"Details: {type(exc).__name__}: {exc}"
            ),
        ) from exc

    evidence_parts = []
    sources = []

    for hit in internal_hits:
        metadata = hit.get("metadata", {})

        source_name = metadata.get("source", "Document")
        page_number = metadata.get("page", "?")

        label = f"{source_name} (page {page_number})"

        evidence_parts.append(
            f"[INTERNAL SOURCE: {label}]\n{hit['text']}"
        )

        sources.append({
            "type": "document",
            "title": label,
            "url": None,
            "page": metadata.get("page"),
            "excerpt": hit["text"][:280],
        })

    evidence = "\n\n---\n\n".join(evidence_parts[:10])

    # Step 2: Generate an answer and enable online search.
    try:
        answer = generate_answer(
            question,
            evidence,
            use_web=request.use_web,
        )

    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "OpenRouter request failed. Check your API key, "
                "account credits, model ID, web-search availability, "
                f"and internet connection. Details: {exc}"
            ),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Answer generation failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    # Step 3: Warn when no internal PDF passages were retrieved.
    if not internal_hits:
        answer += (
            "\n\nNote: No relevant passages were retrieved from "
            "your uploaded documents. Verify product specifications "
            "against official manufacturer documentation."
        )

    return {
        "answer": answer,
        "sources": sources,
        "used_internal_rag": bool(internal_hits),
        "web_search_enabled": request.use_web,
    }
