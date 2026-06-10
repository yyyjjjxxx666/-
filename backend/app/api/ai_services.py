from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional as Opt
from datetime import datetime as dt

from ..models import get_db
from ..models.user import User
from ..models.club import Club, ClubStatus
from ..models.activity import Activity
from ..schemas import RecommendRequest, GenerateTextRequest, GeneratePosterRequest, StarRatingRequest, FaceRegisterRequest
from ..core.security import decode_access_token
from ..core.config import settings
from ..services.deepseek import recommend_clubs, generate_copy, generate_poster_content
from ..services.star_rating import calculate_star_rating
from ..services.poster import generate_poster
from ..services.face_recognition import register_face, recognize_face
from ..services.knowledge_base import add_document, query as kb_query, delete_document, list_documents, get_collection_stats

router = APIRouter(tags=["AI服务"])


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return db.query(User).get(int(payload["sub"]))


@router.post("/recommend")
async def recommend(data: RecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).get(data.user_id)
    if not user:
        return {"error": "用户不存在"}

    clubs = db.query(Club).filter(Club.status == ClubStatus.APPROVED).all()
    clubs_data = [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description or "",
            "tags": c.tags or "",
            "activity_count": c.activity_count,
            "member_count": c.member_count,
            "star_rating": c.star_rating,
        }
        for c in clubs
    ]

    result = await recommend_clubs(user.interests or "无特别偏好", clubs_data)
    club_map = {c.id: c.name for c in clubs}
    for r in result:
        r["club_name"] = club_map.get(r["club_id"], f"社团#{r['club_id']}")
    return {"recommendations": result}


@router.post("/generate-copy")
async def generate_copy_api(data: GenerateTextRequest):
    result = await generate_copy(data.prompt, data.max_tokens)
    return {"text": result}


@router.post("/generate-poster-content")
async def generate_poster_content_api(data: GeneratePosterRequest, db: Session = Depends(get_db)):
    activity = db.query(Activity).get(data.activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    info = {
        "title": activity.title,
        "description": activity.description or "",
        "location": activity.location or "",
        "start_time": str(activity.start_time),
        "end_time": str(activity.end_time),
    }
    content = await generate_poster_content(info)
    # Merge activity details for the template
    content["category"] = activity.category if hasattr(activity, 'category') else "社团活动"
    content["date"] = str(activity.start_time).split("T")[0] if activity.start_time else ""
    content["time"] = activity.start_time.strftime("%H:%M") + " - " + activity.end_time.strftime("%H:%M") if activity.start_time and activity.end_time else ""
    content["location"] = activity.location or ""

    filename = f"poster_{data.activity_id}.png"
    poster_path = generate_poster(content, filename)
    activity.poster_url = "/" + poster_path.replace("\\", "/")
    db.commit()

    return {"content": content, "poster_url": activity.poster_url}


@router.post("/star-rating")
def star_rating(data: StarRatingRequest, db: Session = Depends(get_db)):
    stars = calculate_star_rating(db, data.club_id)
    return {"club_id": data.club_id, "stars": stars}


class PreviewPosterRequest(BaseModel):
    title: str
    description: Opt[str] = None
    location: Opt[str] = None
    start_time: Opt[str] = None
    end_time: Opt[str] = None
    category: str = "社团活动"


@router.post("/generate-poster-preview")
async def generate_poster_preview(data: PreviewPosterRequest):
    info = {
        "title": data.title,
        "description": data.description or "",
        "location": data.location or "",
        "start_time": data.start_time or "",
        "end_time": data.end_time or "",
    }
    content = await generate_poster_content(info)
    content["category"] = data.category
    content["date"] = data.start_time.split("T")[0] if data.start_time else ""
    content["location"] = data.location or ""

    if data.start_time and data.end_time:
        try:
            st = dt.fromisoformat(data.start_time.replace("Z", ""))
            et = dt.fromisoformat(data.end_time.replace("Z", ""))
            content["time"] = st.strftime("%H:%M") + " - " + et.strftime("%H:%M")
        except Exception:
            content["time"] = ""
    else:
        content["time"] = ""

    import uuid
    filename = f"poster_preview_{uuid.uuid4().hex}.png"
    poster_path = generate_poster(content, filename)
    url = "/" + poster_path.replace("\\", "/")
    return {"content": content, "poster_url": url}


@router.post("/face-register")
def face_register(data: FaceRegisterRequest, db: Session = Depends(get_db)):
    if not data.image_data:
        return {"success": False, "message": "未提供图片数据"}
    import base64, os
    img_path = os.path.join(settings.UPLOAD_DIR, f"face_{data.user_id}.jpg")
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(data.image_data))
    result = register_face(db, data.user_id, img_path)
    return result


# ── Knowledge Base ──

def _kb_or_error():
    try:
        from ..services.knowledge_base import get_collection_stats
        get_collection_stats()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/knowledge/add")
def kb_add_doc(data: dict, user: User = Depends(get_current_user)):
    """Add a document to the knowledge base. Requires {title, content, category?}."""
    _kb_or_error()
    if user.role.value not in ("admin", "president"):
        raise HTTPException(status_code=403, detail="仅管理员和负责人可上传文档")
    result = add_document(
        title=data.get("title", "Untitled"),
        content=data.get("content", ""),
        category=data.get("category", "general"),
    )
    return result


@router.get("/knowledge/query")
def kb_query_endpoint(q: str, top_k: int = 5):
    """Query the knowledge base. Returns relevant chunks."""
    _kb_or_error()
    results = kb_query(q, top_k)
    return {"question": q, "results": results}


@router.delete("/knowledge/{doc_id}")
def kb_delete_doc(doc_id: str, user: User = Depends(get_current_user)):
    """Delete a document from the knowledge base."""
    _kb_or_error()
    if user.role.value not in ("admin", "president"):
        raise HTTPException(status_code=403, detail="仅管理员和负责人可删除")
    delete_document(doc_id)
    return {"message": "已删除"}


@router.get("/knowledge/documents")
def kb_list_docs():
    """List all documents in the knowledge base."""
    _kb_or_error()
    return {"documents": list_documents()}


@router.get("/knowledge/stats")
def kb_stats():
    """Get knowledge base statistics."""
    _kb_or_error()
    return get_collection_stats()


@router.post("/knowledge/ask")
async def kb_ask(data: dict):
    """Ask a question with RAG-enhanced AI response."""
    _kb_or_error()
    question = data.get("question", "")
    results = kb_query(question, top_k=3)
    from ..services.deepseek import chat_completion
    if results:
        context = "\n\n".join([r["content"] for r in results])
        prompt = f"基于以下知识库内容回答问题。\n\n知识库内容：\n{context}\n\n问题：{question}\n\n请根据知识库内容回答，如果知识库中没有相关信息请如实说明。回答控制在200字以内。"
    else:
        prompt = f"问题：{question}\n\n知识库为空，请说明暂无相关资料。"
    answer = await chat_completion([{"role": "user", "content": prompt}], max_tokens=400)
    return {"question": question, "answer": answer, "sources": [r["metadata"]["title"] for r in results]}


@router.post("/face-recognize")
def face_recognize(data: FaceRegisterRequest, db: Session = Depends(get_db)):
    import base64, os, tempfile
    img_path = os.path.join(tempfile.gettempdir(), "face_checkin.jpg")
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(data.image_data))

    users = db.query(User).filter(User.face_encoding.isnot(None)).all()
    known = [{"user_id": u.id, "face_encoding": u.face_encoding} for u in users]
    result = recognize_face(img_path, known)
    return result

