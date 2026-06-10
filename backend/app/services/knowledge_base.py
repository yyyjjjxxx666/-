"""
AI Knowledge Base using ChromaDB + sentence-transformers for RAG.
Documents are chunked, embedded, and stored locally.
"""

import os
import hashlib
from typing import List, Optional

_kb_available = False
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from sentence_transformers import SentenceTransformer
    _kb_available = True
except ImportError:
    pass

# Paths
KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")
os.makedirs(KB_DIR, exist_ok=True)

# Lazy-loaded singletons
_client = None
_model = None
_collection = None

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_collection():
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(path=KB_DIR, settings=ChromaSettings(anonymized_telemetry=False))
    if _collection is None:
        _collection = _client.get_or_create_collection(name="club_knowledge")
    return _collection


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _check_available():
    if not _kb_available:
        raise RuntimeError("知识库未安装依赖。请运行: pip install chromadb sentence-transformers")

def add_document(title: str, content: str, category: str = "general") -> dict:
    """Add a document to the knowledge base. Returns {doc_id, chunks}."""
    _check_available()
    collection = _get_collection()
    model = _get_model()

    doc_id = hashlib.md5(f"{title}:{content}".encode()).hexdigest()[:12]
    chunks = _chunk_text(content)

    # Remove existing chunks for this doc
    try:
        existing = collection.get(ids=[f"{doc_id}_{i}" for i in range(100)])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    for i, chunk in enumerate(chunks):
        embedding = model.encode([chunk])[0].tolist()
        collection.add(
            ids=[f"{doc_id}_{i}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"title": title, "category": category, "chunk_index": i, "total_chunks": len(chunks)}],
        )

    return {"doc_id": doc_id, "chunks": len(chunks), "title": title, "category": category}


def query(question: str, top_k: int = 5) -> List[dict]:
    """Query the knowledge base and return relevant chunks with metadata."""
    _check_available()
    collection = _get_collection()
    model = _get_model()

    if collection.count() == 0:
        return []

    embedding = model.encode([question])[0].tolist()
    results = collection.query(query_embeddings=[embedding], n_results=top_k)

    chunks = []
    for i, doc_id in enumerate(results["ids"][0]):
        chunks.append({
            "id": doc_id,
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results.get("distances", [[0]] * top_k)[0][i],
        })
    return chunks


def delete_document(doc_id: str) -> bool:
    """Delete all chunks for a document by its doc_id prefix."""
    _check_available()
    collection = _get_collection()
    try:
        all_ids = collection.get()
        matching = [i for i in all_ids["ids"] if i.startswith(doc_id)]
        if matching:
            collection.delete(ids=matching)
        return True
    except Exception:
        return False


def list_documents() -> List[dict]:
    """List unique documents in the knowledge base."""
    _check_available()
    collection = _get_collection()
    try:
        all_data = collection.get()
        if not all_data["ids"]:
            return []
        seen = set()
        docs = []
        for i, doc_id in enumerate(all_data["ids"]):
            meta = all_data["metadatas"][i]
            title = meta.get("title", "Untitled")
            if title not in seen:
                seen.add(title)
                docs.append({
                    "doc_id": doc_id.rsplit("_", 1)[0],
                    "title": title,
                    "category": meta.get("category", "general"),
                    "chunks": meta.get("total_chunks", 1),
                })
        return docs
    except Exception:
        return []


def get_collection_stats() -> dict:
    """Get collection statistics."""
    _check_available()
    collection = _get_collection()
    return {"document_count": len(list_documents()), "chunk_count": collection.count()}
