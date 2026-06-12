from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional as Opt
from datetime import datetime as dt

from ..models import get_db
from ..models.user import User
from ..models.club import Club, ClubStatus
from ..models.activity import Activity, ActivityRegistration, ActivityStatus
from ..schemas import RecommendRequest, GenerateTextRequest, GeneratePosterRequest, StarRatingRequest, FaceRegisterRequest
from ..core.security import decode_access_token
from ..core.config import settings
from ..services.deepseek import recommend_clubs, generate_copy, generate_poster_content, chat_completion
from ..services.star_rating import calculate_star_rating
from ..services.poster import generate_poster
from ..services.face_recognition import register_face, recognize_face
from ..services.knowledge_base import add_document, query as kb_query, delete_document, list_documents, get_collection_stats
from ..services.ai_chat import stream_chat_response

router = APIRouter(tags=["AI服务"])


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return db.query(User).get(int(payload["sub"]))


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Like get_current_user but returns None when no valid token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_access_token(auth[7:])
        if payload:
            return db.query(User).get(int(payload["sub"]))
    except Exception:
        pass
    return None


@router.get("/assistant/chat")
async def assistant_chat(
    q: str = Query(..., description="用户问题"),
    user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """SSE streaming AI assistant chat endpoint."""

    user_ctx = None
    if user:
        club_name = None
        if user.club_id:
            club = db.query(Club).filter(Club.id == user.club_id).first()
            club_name = club.name if club else None
        user_ctx = {
            "name": user.real_name or user.username,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "interests": user.interests or "",
            "club_id": user.club_id,
            "club_name": club_name,
        }

    async def event_stream():
        async for chunk in stream_chat_response(q, user_ctx):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Interest tag expansion map ──
_INTEREST_EXPANSION = {
    "篮球": ["球类运动", "体育", "竞技", "健身"],
    "足球": ["球类运动", "体育", "竞技", "团队"],
    "乒乓球": ["球类运动", "体育", "竞技"],
    "羽毛球": ["球类运动", "体育", "休闲"],
    "编程": ["软件开发", "IT技术", "人工智能", "算法", "计算机"],
    "摄影": ["视觉艺术", "设计", "影像", "短视频", "媒体"],
    "音乐": ["乐器", "唱歌", "表演", "文艺"],
    "舞蹈": ["表演", "文艺", "健身", "形体"],
    "绘画": ["视觉艺术", "设计", "创意", "手工", "美术"],
    "公益": ["志愿服务", "社会实践", "支教", "环保"],
    "英语": ["语言学习", "国际交流", "留学", "辩论"],
    "辩论": ["语言表达", "逻辑思维", "演讲", "思辨"],
    "读书": ["文学", "阅读", "写作", "人文"],
    "创业": ["商业", "创新", "管理", "实践"],
}


def _expand_interests(interests_str: str) -> str:
    if not interests_str or interests_str == "无特别偏好":
        return interests_str
    tags = [t.strip() for t in interests_str.replace("，", ",").split(",") if t.strip()]
    expanded = set(tags)
    for tag in tags:
        if tag in _INTEREST_EXPANSION:
            expanded.update(_INTEREST_EXPANSION[tag])
    return ",".join(expanded)


@router.post("/recommend")
async def recommend(data: RecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).get(data.user_id)
    if not user:
        return {"error": "用户不存在"}

    # User's joined club
    user_joined = [user.club_id] if user.club_id else []

    # User's recently participated activity clubs
    regs = (
        db.query(ActivityRegistration)
        .filter(ActivityRegistration.user_id == user.id)
        .order_by(ActivityRegistration.registered_at.desc())
        .limit(10)
        .all()
    )
    activity_club_ids = []
    if regs:
        act_ids = [r.activity_id for r in regs]
        acts = db.query(Activity).filter(Activity.id.in_(act_ids)).all()
        activity_club_ids = list(set(a.club_id for a in acts))

    # Gather clubs with rich data
    clubs = db.query(Club).filter(Club.status == ClubStatus.APPROVED).all()
    clubs_data = []
    for c in clubs:
        recent_acts = (
            db.query(Activity)
            .filter(
                Activity.club_id == c.id,
                Activity.status.in_([
                    ActivityStatus.APPROVED,
                    ActivityStatus.REGISTRATION,
                    ActivityStatus.ONGOING,
                ]),
            )
            .order_by(Activity.start_time.desc())
            .limit(3)
            .all()
        )
        clubs_data.append({
            "id": c.id,
            "name": c.name,
            "description": c.description or "",
            "tags": c.tags or "",
            "activity_count": c.activity_count,
            "member_count": c.member_count,
            "star_rating": c.star_rating,
            "recent_activities": [
                {"title": a.title} for a in recent_acts
            ],
        })

    expanded = _expand_interests(user.interests or "无特别偏好")

    result = await recommend_clubs(
        user_interests=expanded,
        clubs_data=clubs_data,
        user_joined_club_ids=user_joined,
        user_activity_club_ids=activity_club_ids,
    )

    club_map = {c.id: c.name for c in clubs}
    for r in result:
        r["club_name"] = club_map.get(r["club_id"], f"社团#{r['club_id']}")

    return {"recommendations": result}


# ── Recommendation Feedback ──

class RecommendFeedbackRequest(BaseModel):
    user_id: int
    club_id: int
    feedback: str  # "liked" or "disliked"


@router.post("/recommend/feedback")
def recommend_feedback(data: RecommendFeedbackRequest):
    """Record user feedback on a recommendation."""
    import os as _os
    _feedback_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "data")
    _os.makedirs(_feedback_dir, exist_ok=True)
    _feedback_file = _os.path.join(_feedback_dir, "recommend_feedback.json")

    all_fb = {}
    if _os.path.exists(_feedback_file):
        import json as _json
        with open(_feedback_file, "r", encoding="utf-8") as f:
            all_fb = _json.load(f)

    key = str(data.user_id)
    if key not in all_fb:
        all_fb[key] = {"liked": [], "disliked": []}

    other = "disliked" if data.feedback == "liked" else "liked"
    if data.club_id in all_fb[key][other]:
        all_fb[key][other].remove(data.club_id)
    if data.club_id not in all_fb[key][data.feedback]:
        all_fb[key][data.feedback].append(data.club_id)

    import json as _json
    with open(_feedback_file, "w", encoding="utf-8") as f:
        _json.dump(all_fb, f, ensure_ascii=False)

    return {"message": "反馈已记录", "liked": all_fb[key]["liked"], "disliked": all_fb[key]["disliked"]}


# ── Activity Recommendations ──

class ActivityRecommendRequest(BaseModel):
    user_id: int
    top_k: int = 5


@router.post("/activities/recommend")
async def recommend_activities(data: ActivityRecommendRequest, db: Session = Depends(get_db)):
    """Recommend upcoming activities based on user interests and history."""
    user = db.query(User).get(data.user_id)
    if not user:
        return {"error": "用户不存在"}

    upcoming = (
        db.query(Activity)
        .filter(Activity.status.in_([ActivityStatus.REGISTRATION, ActivityStatus.ONGOING]))
        .all()
    )

    if not upcoming:
        return {"recommendations": []}

    # Build activity data for AI
    acts_data = []
    for a in upcoming:
        club = db.query(Club).filter(Club.id == a.club_id).first()
        acts_data.append({
            "id": a.id,
            "title": a.title,
            "description": (a.description or "")[:100],
            "location": a.location or "",
            "start_time": str(a.start_time),
            "club_name": club.name if club else "",
            "club_tags": club.tags if club else "",
        })

    acts_text = "\n".join(
        f"- ID:{a['id']} | {a['title']} | 社团:{a['club_name']} | 标签:{a['club_tags']} | 描述:{a['description']} | 时间:{a['start_time'][:16]}"
        for a in acts_data
    )

    expanded = _expand_interests(user.interests or "无特别偏好")

    prompt = f"""你是一个活动推荐系统。根据用户兴趣，从以下活动列表中推荐最匹配的活动。

用户兴趣: {expanded}

活动列表:
{acts_text}

请返回JSON数组格式，每个推荐包含:
- activity_id: 活动ID
- reason: 推荐理由（15字以内）
- category: 推荐类别，从["兴趣匹配","热门活动","社团相关","值得体验"]中选择

按推荐优先级降序排列，最多{data.top_k}个。只返回JSON数组。"""

    result = await chat_completion([{"role": "user", "content": prompt}])

    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        if not text.startswith("["):
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                text = text[start:end + 1]
        import json as _json
        recs = _json.loads(text)
        for r in recs:
            r.setdefault("category", "推荐活动")
        return {"recommendations": recs}
    except Exception:
        return {"recommendations": [
            {"activity_id": a["id"], "reason": a["title"], "category": "推荐活动"}
            for a in acts_data[:data.top_k]
        ]}


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
    design = content.pop("design", None)
    poster_path = generate_poster(content, filename, design)
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
    design = content.pop("design", None)
    poster_path = generate_poster(content, filename, design)
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


# ── AI Content Generation ──

@router.post("/suggest-tags")
async def ai_suggest_tags(data: dict):
    """Suggest tags based on description text."""
    from ..services.ai_content import suggest_tags
    tags = await suggest_tags(data.get("description", ""))
    return {"tags": tags}


@router.post("/generate-description")
async def ai_generate_description(data: dict):
    """Generate club description from keywords."""
    from ..services.ai_content import generate_description
    desc = await generate_description(data.get("keywords", ""))
    return {"description": desc}


@router.post("/generate-activity-summary")
async def ai_generate_activity_summary(data: dict, db: Session = Depends(get_db)):
    """Generate a post-event activity summary."""
    activity = db.query(Activity).get(data.get("activity_id"))
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    from ..models.activity import Checkin
    from ..services.ai_content import generate_activity_summary
    checkins = db.query(Checkin).filter_by(activity_id=activity.id).count()
    summary = await generate_activity_summary(
        activity_title=activity.title,
        activity_desc=activity.description or "",
        checkin_count=checkins,
        registration_count=activity.current_participants or 0,
        location=activity.location or "",
    )
    return {"summary": summary}


# ── Semantic Search ──

@router.get("/search")
def search(q: str, type: str | None = None, top_k: int = 10):
    """Semantic search across clubs and activities."""
    from ..services.semantic_search import search_semantic
    results = search_semantic(q, top_k=top_k, filter_type=type)
    return {"query": q, "results": results}


@router.post("/search/reindex")
def search_reindex(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-index all clubs and activities for semantic search."""
    if user.role.value not in ("admin",):
        raise HTTPException(status_code=403, detail="仅管理员可重建索引")
    from ..services.semantic_search import reindex_all
    result = reindex_all(db)
    return {"message": f"已索引 {result['clubs']} 个社团, {result['activities']} 个活动", **result}


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

