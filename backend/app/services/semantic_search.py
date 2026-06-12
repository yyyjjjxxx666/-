"""
Semantic search for clubs and activities using ChromaDB + sentence-transformers.
Maintains a separate collection from the knowledge base for fast entity search.
"""

import os

_search_available = False
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from sentence_transformers import SentenceTransformer
    _search_available = True
except ImportError:
    pass

SEARCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")
os.makedirs(SEARCH_DIR, exist_ok=True)

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
        _client = chromadb.PersistentClient(path=SEARCH_DIR, settings=ChromaSettings(anonymized_telemetry=False))
    if _collection is None:
        _collection = _client.get_or_create_collection(name="entity_search_index")
    return _collection


def _build_text(name: str, tags: str, description: str, extra: str = "") -> str:
    """Build a searchable text blob from entity fields."""
    parts = [name]
    if tags:
        parts.append(f"标签：{tags}")
    if description:
        parts.append(description[:300])
    if extra:
        parts.append(extra)
    return "。".join(parts)


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def index_club(club) -> bool:
    """Index or update a club in the semantic search collection."""
    try:
        collection = _get_collection()
        model = _get_model()
        text = _build_text(club.name, getattr(club, 'tags', '') or '', getattr(club, 'description', '') or '')
        embedding = model.encode([text])[0].tolist()
        collection.upsert(
            ids=[f"club_{club.id}"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"type": "club", "id": club.id, "name": club.name}],
        )
        return True
    except Exception:
        return False


def index_activity(activity, club_name: str = "") -> bool:
    """Index or update an activity in the semantic search collection."""
    try:
        collection = _get_collection()
        model = _get_model()
        extra = f"社团：{club_name}" if club_name else ""
        text = _build_text(
            activity.title,
            "",
            getattr(activity, 'description', '') or '',
            extra,
        )
        embedding = model.encode([text])[0].tolist()
        collection.upsert(
            ids=[f"activity_{activity.id}"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"type": "activity", "id": activity.id, "name": activity.title}],
        )
        return True
    except Exception:
        return False


def remove_entity(entity_type: str, entity_id: int) -> bool:
    """Remove a club or activity from the search index."""
    try:
        collection = _get_collection()
        collection.delete(ids=[f"{entity_type}_{entity_id}"])
        return True
    except Exception:
        return False


def search_semantic(query: str, top_k: int = 10, filter_type: str | None = None) -> list:
    """Semantic search across clubs and/or activities."""
    try:
        collection = _get_collection()
        model = _get_model()
        embedding = model.encode([query])[0].tolist()
        where = {"type": filter_type} if filter_type else None
        results = collection.query(query_embeddings=[embedding], n_results=top_k, where=where)
        items = []
        ids_list = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for i, eid in enumerate(ids_list):
            meta = metadatas[i] if i < len(metadatas) else {}
            dist = distances[i] if i < len(distances) else 0
            items.append({
                "id": meta.get("id"),
                "name": meta.get("name", ""),
                "type": meta.get("type", ""),
                "score": round(1 - dist, 3) if dist else 1.0,
            })
        return items
    except Exception:
        return []


def reindex_all(db) -> dict:
    """Re-index all clubs and activities."""
    from ..models.club import Club
    from ..models.activity import Activity

    clubs = db.query(Club).all()
    activities = db.query(Activity).all()

    club_count = 0
    act_count = 0
    for c in clubs:
        if index_club(c):
            club_count += 1
    for a in activities:
        club_name = ""
        try:
            owner = db.query(Club).filter(Club.id == a.club_id).first()
            club_name = owner.name if owner else ""
        except Exception:
            pass
        if index_activity(a, club_name):
            act_count += 1

    return {"clubs": club_count, "activities": act_count}
