
import chromadb
import ollama
from app.config import settings


def get_ollama_client():
    return ollama.Client(host=settings.ollama_base_url)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    response = get_ollama_client().embed(
        model=settings.ollama_embedding_model,
        input=texts,
    )
    return response["embeddings"]


def get_chroma_client():
    return chromadb.PersistentClient(path=str(settings.chroma_dir))


def get_collection():
    return get_chroma_client().get_or_create_collection(
        name="industrial_product_docs",
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    collection = get_collection()
    count = collection.count()

    if count == 0:
        return []

    query_embedding = embed_texts([query])[0]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k or settings.top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    items = []
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for doc, meta, distance in zip(docs, metas, distances):
        items.append({
            "text": doc,
            "metadata": meta or {},
            "distance": distance,
        })

    return items
