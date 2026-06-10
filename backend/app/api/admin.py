from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List

from ..models import get_db
from ..models.user import User
from ..models.club import Club, ClubStatus
from ..models.activity import Activity, ActivityStatus
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
