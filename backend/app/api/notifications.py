from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import List

from ..models import get_db
from ..models.user import User
from ..models.club import Club
from ..models.notification import Notification
from ..schemas import NotificationCreate, NotificationInfo
from ..core.security import decode_access_token
from ..core.config import settings

router = APIRouter(tags=["通知"])


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return db.query(User).get(int(payload["sub"]))


@router.post("/", response_model=NotificationInfo)
def send_notification(data: NotificationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发送通知"""
    if user.role.value == "member":
        raise HTTPException(status_code=403, detail="普通成员无权发送通知")

    # Build source label
    if user.role.value == "admin":
        source_label = "校联社"
        # Admin can send to all / club / unaffiliated
        if data.target == "club" and data.club_id:
            source_label = "校联社"
    elif user.role.value == "president":
        if not user.club_id:
            raise HTTPException(status_code=400, detail="您未加入任何社团")
        club = db.query(Club).get(user.club_id)
        if not club or club.president_id != user.id:
            raise HTTPException(status_code=403, detail="只有本社团负责人才能发送通知")
        source_label = f"{club.name}-{user.real_name}"
        if data.target not in ("club", "unaffiliated"):
            raise HTTPException(status_code=400, detail="负责人只能发送给社团成员或未加入社团的学生")
    else:
        raise HTTPException(status_code=403, detail="无权发送通知")

    # Create notification records
    if data.target == "all" and user.role.value == "admin":
        # Broadcast to all users - single record with receiver_id=NULL
        notif = Notification(
            sender_id=user.id, receiver_id=None, target_type="all",
            title=data.title, content=data.content,
            source_label=source_label, category="system",
        )
        db.add(notif)
    elif data.target == "club":
        if not data.club_id:
            raise HTTPException(status_code=400, detail="请指定目标社团")
        club_members = db.query(User).filter(User.club_id == data.club_id).all()
        for member in club_members:
            notif = Notification(
                sender_id=user.id, receiver_id=member.id, club_id=data.club_id,
                target_type="club", title=data.title, content=data.content,
                source_label=source_label, category="club",
            )
            db.add(notif)
    elif data.target == "unaffiliated":
        unaffiliated = db.query(User).filter(User.club_id.is_(None), User.role != "admin").all()
        for u in unaffiliated:
            notif = Notification(
                sender_id=user.id, receiver_id=u.id, target_type="unaffiliated",
                title=data.title, content=data.content,
                source_label=source_label, category="system",
            )
            db.add(notif)

    db.commit()
    return NotificationInfo(id=0, sender_id=user.id, title=data.title, content=data.content,
                            source_label=source_label, category="system", is_read=False,
                            created_at=__import__("datetime").datetime.utcnow())


@router.get("/", response_model=List[NotificationInfo])
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db),
                       unread_only: bool = False):
    """获取当前用户的通知列表"""
    q = db.query(Notification).filter(
        (Notification.receiver_id == user.id) | (Notification.receiver_id.is_(None))
    )
    if unread_only:
        q = q.filter(Notification.is_read == False)
    return q.order_by(Notification.created_at.desc()).limit(50).all()


@router.put("/{notif_id}/read")
def mark_read(notif_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).get(notif_id)
    if not notif:
        raise HTTPException(status_code=404, detail="通知不存在")
    notif.is_read = True
    db.commit()
    return {"message": "已读"}


@router.put("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        (Notification.receiver_id == user.id) | (Notification.receiver_id.is_(None))
    ).update({"is_read": True})
    db.commit()
    return {"message": "全部已读"}


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(Notification).filter(
        ((Notification.receiver_id == user.id) | (Notification.receiver_id.is_(None))),
        Notification.is_read == False,
    ).count()
    return {"count": count}


@router.delete("/read")
def delete_read_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.receiver_id == user.id,
        Notification.is_read == True,
    ).delete()
    db.commit()
    return {"message": "已删除所有已读通知"}


@router.post("/ai-generate")
async def ai_generate(data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI 生成通知内容（支持语气切换）"""
    if user.role.value not in ("admin", "president"):
        raise HTTPException(status_code=403, detail="无权使用")
    from ..services.deepseek import chat_completion

    target = data.get("target", "all")
    tone = data.get("tone", "正式")  # 正式/轻松/紧急
    club_name = data.get("club_name", "")
    context = data.get("extra", "")
    title_hint = data.get("title_hint", "")

    target_desc = {"all": "全体用户", "club": "社团成员", "unaffiliated": "未加入社团的学生"}.get(target, "全体用户")
    tone_desc = {"正式": "语言正式规范", "轻松": "语气轻松活泼", "紧急": "语气郑重且引人注意"}.get(tone, "语言正式")

    prompt = f"""生成一条社团系统通知：
- 目标受众：{target_desc}
- 语气风格：{tone_desc}
- 相关社团：{club_name or '校社联'}
- 主题提示：{title_hint}
- 额外要求：{context}

请返回JSON（只返回JSON，不要其他文字）：
{{"title": "通知标题（10字以内）", "content": "通知正文（80-150字）"}}"""

    result = await chat_completion([{"role": "user", "content": prompt}], max_tokens=350)
    try:
        import json as _json
        text = result.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = _json.loads(text)
        return {"title": parsed.get("title", ""), "content": parsed.get("content", result)}
    except Exception:
        return {"title": "", "content": result}


@router.get("/ai-digest")
async def ai_digest(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI 生成未读通知摘要"""
    unread = (
        db.query(Notification)
        .filter(
            (Notification.receiver_id == user.id) | (Notification.receiver_id.is_(None)),
            Notification.is_read == False,
        )
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    if not unread:
        return {"digest": "您没有未读通知。", "count": 0}

    notif_lines = "\n".join(
        f"- [{n.source_label or '系统'}] {n.title}: {n.content[:80]}"
        for n in unread[:10]
    )
    from ..services.deepseek import chat_completion

    prompt = f"""用户"{user.real_name}"有{len(unread)}条未读通知。请生成一段50字以内的摘要，概括最重要通知：
{notif_lines}
请直接返回摘要文本。"""

    digest = await chat_completion([{"role": "user", "content": prompt}], max_tokens=150)
    return {"digest": digest.strip(), "count": len(unread)}
