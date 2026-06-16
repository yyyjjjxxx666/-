import json as _json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..models import get_db
from ..models.user import User
from ..models.club import Club, ClubStatus
from ..models.activity import Activity, ActivityStatus, ActivityRegistration, Checkin
from ..schemas import ClubInfo, ActivityInfo
from ..core.security import decode_access_token

router = APIRouter(tags=["管理员审批"])


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = db.query(User).get(int(payload["sub"]))
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    return user


@router.get("/pending-items")
def pending_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出所有待审批项"""
    pending_clubs = db.query(Club).filter(Club.status == ClubStatus.PENDING).all()
    pending_activities = db.query(Activity).filter(Activity.status == ActivityStatus.PENDING).all()
    pending_dissolve = db.query(Club).filter(Club.status == "dissolve_pending").all()

    return {
        "clubs": [ClubInfo.model_validate(c).model_dump() for c in pending_clubs],
        "activities": [ActivityInfo.model_validate(a).model_dump() for a in pending_activities],
        "dissolutions": [{"id": c.id, "name": c.name, "president_id": c.president_id, "created_at": str(c.created_at)} for c in pending_dissolve],
    }


@router.put("/activities/{activity_id}/approve")
def approve_activity(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    activity = db.query(Activity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    activity.status = ActivityStatus.APPROVED
    db.commit()
    return {"message": "活动已通过审批"}


@router.put("/activities/{activity_id}/reject")
def reject_activity(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    activity = db.query(Activity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    activity.status = ActivityStatus.REJECTED
    db.commit()
    return {"message": "活动已拒绝"}


@router.put("/clubs/{club_id}/reject")
def reject_club(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    club.status = ClubStatus.REJECTED
    db.commit()
    return {"message": "社团已拒绝"}


@router.get("/pending-count")
def pending_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    clubs = db.query(Club).filter(Club.status == ClubStatus.PENDING).count()
    activities = db.query(Activity).filter(Activity.status == ActivityStatus.PENDING).count()
    dissolutions = db.query(Club).filter(Club.status == "dissolve_pending").count()
    return {"clubs": clubs, "activities": activities, "dissolutions": dissolutions, "total": clubs + activities + dissolutions}


@router.get("/stats")
def admin_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    total_clubs = db.query(Club).count()
    approved_clubs = db.query(Club).filter(Club.status == ClubStatus.APPROVED).count()
    pending_clubs = db.query(Club).filter(Club.status == ClubStatus.PENDING).count()
    total_activities = db.query(Activity).count()
    ongoing = db.query(Activity).filter(Activity.status.in_([ActivityStatus.REGISTRATION, ActivityStatus.ONGOING])).count()
    total_members = db.query(User).filter(User.role == "member").count()
    presidents = db.query(User).filter(User.role == "president").count()
    return {
        "clubs": total_clubs,
        "approved_clubs": approved_clubs,
        "pending_clubs": pending_clubs,
        "activities": total_activities,
        "ongoing_activities": ongoing,
        "members": total_members,
        "presidents": presidents,
    }


@router.get("/all-approvals")
def all_approvals(status: str = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return all approval records (all statuses) across clubs, activities, dissolutions, join requests."""
    from ..models.club import JoinRequest
    items = []

    # Clubs
    club_q = db.query(Club)
    if status:
        club_q = club_q.filter(Club.status == status)
    for c in club_q.order_by(Club.created_at.desc()).all():
        applicant = db.query(User).get(c.president_id)
        items.append({
            "type": "club",
            "type_label": "社团审批",
            "id": c.id,
            "name": c.name,
            "status": c.status.value if hasattr(c.status, 'value') else c.status,
            "applicant": applicant.real_name or applicant.username if applicant else "未知",
            "applicant_id": c.president_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "reviewed_at": None,
        })

    # Activities
    act_q = db.query(Activity)
    if status:
        act_q = act_q.filter(Activity.status == status)
    for a in act_q.order_by(Activity.created_at.desc()).all():
        applicant = db.query(User).get(a.creator_id) if hasattr(a, 'creator_id') else None
        items.append({
            "type": "activity",
            "type_label": "活动审批",
            "id": a.id,
            "name": a.title,
            "status": a.status.value if hasattr(a.status, 'value') else a.status,
            "applicant": applicant.real_name or applicant.username if applicant else "未知",
            "applicant_id": a.creator_id if hasattr(a, 'creator_id') else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "reviewed_at": None,
        })

    # Dissolutions (clubs with dissolve_pending or already processed)
    diss_status = status if status else None
    diss_q = db.query(Club).filter(Club.status.in_(["dissolve_pending"]))
    # Include all clubs for dissolution history - but only those that ever had dissolve status
    # For simplicity, we only show dissolve_pending ones (already-disolved are deleted)
    for c in diss_q.order_by(Club.created_at.desc()).all():
        applicant = db.query(User).get(c.president_id)
        items.append({
            "type": "dissolution",
            "type_label": "注销审批",
            "id": c.id,
            "name": c.name,
            "status": "dissolve_pending",
            "applicant": applicant.real_name or applicant.username if applicant else "未知",
            "applicant_id": c.president_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "reviewed_at": None,
        })

    # Join Requests
    jr_q = db.query(JoinRequest)
    if status:
        jr_q = jr_q.filter(JoinRequest.status == status)
    for jr in jr_q.order_by(JoinRequest.created_at.desc()).all():
        req_user = db.query(User).get(jr.user_id)
        club = db.query(Club).get(jr.club_id)
        items.append({
            "type": "join_request",
            "type_label": "入社申请",
            "id": jr.id,
            "name": f"{req_user.real_name or req_user.username if req_user else '未知'} → {club.name if club else '未知社团'}",
            "status": jr.status,
            "applicant": req_user.real_name or req_user.username if req_user else "未知",
            "applicant_id": jr.user_id,
            "created_at": jr.created_at.isoformat() if jr.created_at else None,
            "reviewed_at": jr.reviewed_at.isoformat() if jr.reviewed_at else None,
        })

    # Sort by created_at desc
    items.sort(key=lambda x: x["created_at"] or "", reverse=True)

    return {"items": items, "total": len(items)}


@router.get("/ai-insights")
async def ai_insights(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI-generated narrative insights for admin dashboard."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可访问")

    now = datetime.utcnow()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(seconds=1)

    # Basic stats
    total_clubs = db.query(Club).count()
    approved_clubs = db.query(Club).filter(Club.status == ClubStatus.APPROVED).count()
    total_activities = db.query(Activity).count()
    ongoing_acts = db.query(Activity).filter(Activity.status.in_([ActivityStatus.REGISTRATION, ActivityStatus.ONGOING])).count()

    # This month clubs
    new_clubs_month = db.query(Club).filter(Club.created_at >= this_month_start).count()
    # Last month clubs
    new_clubs_last = db.query(Club).filter(Club.created_at >= last_month_start, Club.created_at <= last_month_end).count()

    # This month activities
    new_acts_month = db.query(Activity).filter(Activity.created_at >= this_month_start).count()
    new_acts_last = db.query(Activity).filter(Activity.created_at >= last_month_start, Activity.created_at <= last_month_end).count()

    # Top clubs by activity count
    top_active = (
        db.query(Club.name, func.count(Activity.id).label("cnt"))
        .join(Activity, Activity.club_id == Club.id)
        .filter(Activity.created_at >= this_month_start)
        .group_by(Club.id)
        .order_by(func.count(Activity.id).desc())
        .limit(5)
        .all()
    )

    # Average checkin rate
    registrations = db.query(ActivityRegistration).count()
    checkins = db.query(Checkin).count()
    checkin_rate = round(checkins / max(registrations, 1) * 100, 1)

    # Build stats text for AI
    stats_text = f"""系统当前数据概览：
- 社团总数: {total_clubs} 个（已通过: {approved_clubs}）
- 活动总数: {total_activities} 个（进行中/报名中: {ongoing_acts}）
- 本月新增社团: {new_clubs_month} 个（上月: {new_clubs_last}）
- 本月新增活动: {new_acts_month} 个（上月: {new_acts_last}）
- 总签到率: {checkin_rate}%
- 本月最活跃社团: {", ".join(f"{name}({cnt}活动)" for name, cnt in top_active) if top_active else "暂无数据"}"""

    from ..services.deepseek import chat_completion

    prompt = f"""作为高校社团管理系统智能分析师，基于以下数据生成洞察报告：

{stats_text}

请返回JSON格式（只返回JSON，不要其他文字）：
{{
    "summary": "一段80字以内的系统运营总体评价",
    "highlights": ["亮点1（10字内）", "亮点2"],
    "concerns": ["需关注的问题1"],
    "suggestions": ["可操作的建议1", "建议2"],
    "trend_note": "简短的趋势判断（30字内）"
}}"""

    try:
        result = await chat_completion([{"role": "user", "content": prompt}], max_tokens=500, temperature=0.5)
        text = result.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        insights = _json.loads(text)
    except Exception:
        insights = {
            "summary": f"系统共有 {total_clubs} 个社团、{total_activities} 个活动，本月签到率 {checkin_rate}%。",
            "highlights": ["系统运行正常"],
            "concerns": [],
            "suggestions": ["持续关注社团活跃度"],
            "trend_note": "数据稳定",
        }

    return {"insights": insights, "generated_at": now.isoformat()}
