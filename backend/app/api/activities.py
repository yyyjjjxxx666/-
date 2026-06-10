from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional

from ..models import get_db
from ..models.user import User
from ..models.activity import Activity, ActivityStatus, ActivityRegistration, Checkin
from ..schemas import ActivityCreate, ActivityInfo
from ..core.security import decode_access_token

router = APIRouter(tags=["活动管理"])


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return db.query(User).get(int(payload["sub"]))


def get_current_user_or_none(authorization: str = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_access_token(authorization[7:])
    if not payload:
        return None
    return db.query(User).get(int(payload["sub"]))


@router.post("/", response_model=ActivityInfo)
def create_activity(data: ActivityCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value not in ("president", "admin"):
        raise HTTPException(status_code=403, detail="只有社团负责人或管理员可以创建活动")
    activity = Activity(**data.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.get("/", response_model=List[dict])
def list_activities(status: str = None, club_id: int = None, search: str = None, user: Optional[User] = Depends(get_current_user_or_none), db: Session = Depends(get_db)):
    q = db.query(Activity)

    # Role-based visibility
    if not user:
        q = q.filter(Activity.status.notin_([ActivityStatus.PENDING, ActivityStatus.REJECTED]))
    elif user.role.value == "admin":
        pass
    elif user.role.value == "president":
        q = q.filter(
            (Activity.club_id == user.club_id) |
            Activity.status.notin_([ActivityStatus.PENDING, ActivityStatus.REJECTED])
        )
    else:
        q = q.filter(Activity.status.notin_([ActivityStatus.PENDING, ActivityStatus.REJECTED]))

    if status:
        q = q.filter(Activity.status == status)
    if club_id:
        q = q.filter(Activity.club_id == club_id)
    if search:
        q = q.filter(Activity.title.contains(search) | Activity.description.contains(search))

    activities = q.all()

    if user:
        reg_ids = {r.activity_id for r in db.query(ActivityRegistration).filter(
            ActivityRegistration.user_id == user.id,
            ActivityRegistration.activity_id.in_([a.id for a in activities])
        ).all()}
        return [dict(ActivityInfo.model_validate(a).model_dump(), is_registered=a.id in reg_ids) for a in activities]
    return [dict(ActivityInfo.model_validate(a).model_dump(), is_registered=False) for a in activities]


@router.get("/{activity_id}", response_model=ActivityInfo)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.query(Activity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    return activity


@router.post("/{activity_id}/register")
def register_activity(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    activity = db.query(Activity).get(activity_id)
    if not activity or activity.status != ActivityStatus.REGISTRATION:
        raise HTTPException(status_code=400, detail="活动未开放报名")
    if activity.max_participants and activity.current_participants >= activity.max_participants:
        raise HTTPException(status_code=400, detail="报名人数已满")

    existing = db.query(ActivityRegistration).filter_by(activity_id=activity_id, user_id=user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="已报名该活动")

    reg = ActivityRegistration(activity_id=activity_id, user_id=user.id)
    activity.current_participants += 1
    db.add(reg)
    db.commit()
    return {"message": "报名成功"}


@router.put("/{activity_id}/status")
def update_activity_status(activity_id: int, status: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新活动状态: approve/open/start/end"""
    activity = db.query(Activity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    status_labels = {"approve": "通过", "open": "开放报名", "start": "开始", "end": "结束"}
    valid_statuses = {
        "approve": ActivityStatus.APPROVED,
        "open": ActivityStatus.REGISTRATION,
        "start": ActivityStatus.ONGOING,
        "end": ActivityStatus.FINISHED,
    }
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态。可选: {', '.join(status_labels.values())}")

    activity.status = valid_statuses[status]

    # 开放报名时自动生成签到二维码
    if status == "open" and not activity.checkin_qr:
        from ..services.qrcode_service import generate_checkin_qr
        activity.checkin_qr = generate_checkin_qr(activity_id, activity.title)

    db.commit()
    return {"message": "状态已更新", "status": activity.status.value, "checkin_qr": activity.checkin_qr}


@router.post("/{activity_id}/checkin")
def checkin_activity(activity_id: int, method: str = "qr", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    activity = db.query(Activity).get(activity_id)
    if not activity or activity.status not in (ActivityStatus.ONGOING, ActivityStatus.REGISTRATION):
        raise HTTPException(status_code=400, detail="活动未在进行中")

    existing = db.query(Checkin).filter_by(activity_id=activity_id, user_id=user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="已签到")

    checkin = Checkin(activity_id=activity_id, user_id=user.id, method=method)
    db.add(checkin)
    db.commit()
    return {"message": "签到成功", "time": checkin.checkin_time.isoformat()}


@router.post("/{activity_id}/checkin/manual")
def manual_checkin(activity_id: int, target_user_id: int, method: str = "qr", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """管理员/负责人手动为用户签到"""
    if user.role.value not in ("admin", "president"):
        raise HTTPException(status_code=403, detail="只有管理员或社团负责人可以手动签到")

    activity = db.query(Activity).get(activity_id)
    if not activity or activity.status not in (ActivityStatus.ONGOING, ActivityStatus.REGISTRATION):
        raise HTTPException(status_code=400, detail="活动未在进行中")

    target = db.query(User).get(target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="目标用户不存在")

    existing = db.query(Checkin).filter_by(activity_id=activity_id, user_id=target_user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户已签到")

    checkin = Checkin(activity_id=activity_id, user_id=target_user_id, method=method)
    db.add(checkin)
    db.commit()
    return {"message": f"签到成功: {target.real_name or target.username}", "time": checkin.checkin_time.isoformat()}


@router.get("/{activity_id}/attendance")
def get_attendance(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    activity = db.query(Activity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    checkin_count = db.query(Checkin).filter(Checkin.activity_id == activity_id).count()
    reg_count = activity.current_participants or 0
    rate = round(checkin_count / reg_count * 100, 1) if reg_count > 0 else 0
    return {"activity_id": activity_id, "checkins": checkin_count, "registrations": reg_count, "rate": rate}


@router.post("/{activity_id}/generate-qr")
def regenerate_qr(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value not in ("admin", "president"):
        raise HTTPException(status_code=403, detail="仅管理员或负责人可生成二维码")
    activity = db.query(Activity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    from ..services.qrcode_service import generate_checkin_qr
    activity.checkin_qr = generate_checkin_qr(activity_id, activity.title)
    db.commit()
    return {"message": "二维码已生成", "checkin_qr": activity.checkin_qr}


@router.get("/{activity_id}/checkins")
def list_checkins(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value not in ("admin", "president"):
        raise HTTPException(status_code=403, detail="仅管理员或负责人可查看")
    checkins_data = db.query(Checkin).filter(Checkin.activity_id == activity_id).all()
    return [{"user_id": c.user_id, "method": c.method, "time": c.checkin_time.isoformat(), "status": c.status} for c in checkins_data]


