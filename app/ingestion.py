
import hashlib
import re
from pathlib import Path

import pymupdf

from app.retrieval import get_collection, embed_texts


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 1100,
    overlap: int = 180,
) -> list[str]:
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            boundary = max(
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
            )
            if boundary > start + chunk_size // 2:
                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def ingest_pdf(path: Path) -> dict:
    records = []

    with pymupdf.open(path) as pdf:
        for page_index, page in enumerate(pdf):
            text = clean_text(page.get_text("text"))

            for chunk_index, chunk in enumerate(chunk_text(text)):
                digest = hashlib.sha1(
                    (
                        f"{path.name}:{page_index + 1}:"
                        f"{chunk_index}:{chunk}"
                    ).encode("utf-8")
                ).hexdigest()

                records.append({
                    "id": digest,
                    "text": chunk,
                    "metadata": {
                        "source": path.name,
                        "page": page_index + 1,
                        "chunk": chunk_index,
                        "source_type": "internal_pdf",
                    },
                })

    if not records:
        return {
            "filename": path.name,
            "chunks_added": 0,
            "warning": (
                "No selectable text found. "
                "This PDF may require OCR."
            ),
        }

    collection = get_collection()

    # Remove old chunks for this PDF so re-indexing does not
    # leave outdated chunks in the collection.
    existing = collection.get(
        where={"source": path.name},
        include=["metadatas"],
    )
    if existing.get("ids"):
        collection.delete(ids=existing["ids"])

    embeddings = embed_texts([record["text"] for record in records])

    collection.upsert(
        ids=[record["id"] for record in records],
        documents=[record["text"] for record in records],
        metadatas=[record["metadata"] for record in records],
        embeddings=embeddings,
    )

    return {
        "filename": path.name,
        "chunks_added": len(records),
    }
