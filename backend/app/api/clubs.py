from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..models import get_db
from ..models.user import User
from ..models.club import Club, ClubStatus, JoinRequest
from ..schemas import ClubCreate, ClubInfo, TransferRequest, JoinRequestAction
from ..models.notification import Notification
from ..core.security import decode_access_token
from ..services.star_rating import calculate_star_rating

router = APIRouter(tags=["社团管理"])


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = db.query(User).get(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_current_user_or_none(authorization: str = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_access_token(authorization[7:])
    if not payload:
        return None
    return db.query(User).get(int(payload["sub"]))


@router.post("/", response_model=ClubInfo)
def create_club(data: ClubCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.club_id:
        raise HTTPException(status_code=400, detail="您已加入社团，无法创建新社团")
    if db.query(Club).filter(Club.name == data.name).first():
        raise HTTPException(status_code=400, detail="社团名称已存在")

    club = Club(name=data.name, description=data.description, president_id=user.id, tags=data.tags)
    db.add(club)
    user.club_id = club.id
    db.commit()
    db.refresh(club)
    calculate_star_rating(db, club.id)
    return club


@router.get("/", response_model=List[ClubInfo])
def list_clubs(status: str = None, search: str = None, user: Optional[User] = Depends(get_current_user_or_none), db: Session = Depends(get_db)):
    q = db.query(Club)

    # Role-based visibility
    if not user:
        q = q.filter(Club.status == ClubStatus.APPROVED)
    elif user.role.value == "admin":
        pass
    elif user.role.value == "president":
        q = q.filter(
            (Club.status == ClubStatus.APPROVED) |
            ((Club.status == ClubStatus.PENDING) & (Club.president_id == user.id))
        )
    else:
        q = q.filter(Club.status == ClubStatus.APPROVED)

    if status:
        q = q.filter(Club.status == status)
    if search:
        q = q.filter(Club.name.contains(search) | Club.tags.contains(search) | Club.description.contains(search))
    return q.all()


@router.get("/my-pending-requests")
def my_pending_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reqs = db.query(JoinRequest).filter_by(user_id=user.id, status="pending").all()
    return [r.club_id for r in reqs]


@router.get("/{club_id}", response_model=ClubInfo)
def get_club(club_id: int, db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    return club


@router.put("/{club_id}/approve")
def approve_club(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可审批")
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    club.status = ClubStatus.APPROVED
    # Promote the club president
    president = db.query(User).get(club.president_id)
    if president and president.role.value == "member":
        president.role = "president"
    db.commit()
    return {"message": "审批通过"}


@router.put("/{club_id}")
def update_club(club_id: int, data: ClubCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    if club.president_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="无权限修改该社团信息")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(club, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.post("/{club_id}/leave")
def leave_club(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    if user.club_id != club_id:
        raise HTTPException(status_code=400, detail="您不在该社团中")
    if club.president_id == user.id:
        raise HTTPException(status_code=400, detail="负责人不能直接退出，请先转让负责人身份")

    user.club_id = None
    user.role = "member"
    club.member_count = max(0, club.member_count - 1)
    # Notify all members
    for member in db.query(User).filter(User.club_id == club_id).all():
        db.add(Notification(sender_id=user.id, receiver_id=member.id, club_id=club_id,
                            title="成员退出", content=f"{user.real_name} 已退出 {club.name}",
                            source_label=f"{club.name}-系统", category="club"))
    db.add(Notification(sender_id=user.id, receiver_id=club.president_id, club_id=club_id,
                        title="成员退出", content=f"{user.real_name} 已退出 {club.name}",
                        source_label=f"{club.name}-系统", category="club"))
    db.commit()
    return {"message": f"已退出 {club.name}"}


@router.post("/{club_id}/transfer")
def transfer_presidency(club_id: int, data: TransferRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    if club.president_id != user.id:
        raise HTTPException(status_code=403, detail="只有当前负责人才能转让")

    new_president = db.query(User).get(data.new_president_id)
    if not new_president or new_president.club_id != club_id:
        raise HTTPException(status_code=400, detail="目标用户不在该社团中")

    old_name = user.real_name
    # Transfer
    club.president_id = new_president.id
    # Demote old president to member
    user.role = "member"
    # Promote new president
    new_president.role = "president"
    db.commit()

    # Notify all members
    for member in db.query(User).filter(User.club_id == club_id).all():
        db.add(Notification(sender_id=user.id, receiver_id=member.id, club_id=club_id,
                            title="负责人变更", content=f"社团负责人已由 {old_name} 变更为 {new_president.real_name}",
                            source_label=f"{club.name}-系统", category="club"))
    db.commit()
    return {"message": f"负责人已转让给 {new_president.real_name}"}


@router.post("/{club_id}/join")
def join_club(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value != "member":
        raise HTTPException(status_code=403, detail="只有普通成员可以申请加入社团")
    if user.club_id:
        raise HTTPException(status_code=400, detail="您已在其他社团中，请先退出")
    club = db.query(Club).get(club_id)
    if not club or club.status != ClubStatus.APPROVED:
        raise HTTPException(status_code=400, detail="社团不存在或未通过审批")

    existing = db.query(JoinRequest).filter_by(club_id=club_id, user_id=user.id, status="pending").first()
    if existing:
        raise HTTPException(status_code=400, detail="已申请，等待审批中")

    req = JoinRequest(club_id=club_id, user_id=user.id)
    db.add(req)

    # Notify the club president
    db.add(Notification(
        sender_id=user.id, receiver_id=club.president_id, club_id=club_id,
        title="新的入社申请", content=f"{user.real_name} 申请加入 {club.name}",
        source_label=f"{club.name}-系统", category="club"
    ))
    db.commit()
    return {"message": "入社申请已提交，等待负责人审批"}


@router.get("/{club_id}/members")
def list_club_members(club_id: int, db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    members = db.query(User).filter(User.club_id == club_id).all()
    return [{"id": m.id, "username": m.username, "real_name": m.real_name, "role": m.role.value} for m in members]


@router.put("/{club_id}/approve-dissolve")
def approve_dissolve(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可审批")
    club = db.query(Club).get(club_id)
    if not club or club.status != ClubStatus.DISSOLVE_PENDING:
        raise HTTPException(status_code=400, detail="社团不存在或不在注销待审批状态")
    # Clear all members
    for member in db.query(User).filter(User.club_id == club_id).all():
        member.club_id = None
        member.role = "member"
    db.flush()
    # Delete related data
    db.query(JoinRequest).filter(JoinRequest.club_id == club_id).delete()
    db.query(Notification).filter(Notification.club_id == club_id).delete()
    from ..models.activity import Activity, ActivityRegistration, Checkin
    for act in db.query(Activity).filter(Activity.club_id == club_id).all():
        db.query(Checkin).filter(Checkin.activity_id == act.id).delete()
        db.query(ActivityRegistration).filter(ActivityRegistration.activity_id == act.id).delete()
    db.query(Activity).filter(Activity.club_id == club_id).delete()
    db.delete(club)
    db.commit()
    return {"message": "已批准注销，社团已删除"}


@router.put("/{club_id}/reject-dissolve")
def reject_dissolve(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可审批")
    club = db.query(Club).get(club_id)
    if not club or club.status != ClubStatus.DISSOLVE_PENDING:
        raise HTTPException(status_code=400, detail="社团不存在或不在注销待审批状态")
    club.status = ClubStatus.APPROVED
    db.commit()
    return {"message": "已拒绝注销"}


@router.post("/{club_id}/dissolve")
def dissolve_club(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    if club.president_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="只有社团负责人可以申请注销")

    club.status = ClubStatus.DISSOLVE_PENDING
    db.commit()
    return {"message": "注销申请已提交，等待管理员审批"}


@router.get("/{club_id}/join-requests")
def list_join_requests(club_id: int, status: str = "pending", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    if club.president_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅负责人可查看入社申请")

    q = db.query(JoinRequest).filter(JoinRequest.club_id == club_id)
    if status:
        q = q.filter(JoinRequest.status == status)

    result = []
    for r in q.all():
        req_user = db.query(User).get(r.user_id)
        result.append({
            "id": r.id, "club_id": r.club_id, "user_id": r.user_id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "user_name": req_user.real_name or req_user.username if req_user else "Unknown",
        })
    return result


@router.put("/{club_id}/join-requests/{request_id}")
def handle_join_request(club_id: int, request_id: int, data: JoinRequestAction, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    if club.president_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅负责人可处理入社申请")

    req = db.query(JoinRequest).filter_by(id=request_id, club_id=club_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已被处理")

    applicant = db.query(User).get(req.user_id)

    if data.action == "approve":
        req.status = "approved"
        req.reviewed_at = datetime.utcnow()
        applicant.club_id = club_id
        club.member_count += 1
        msg = f"您的入社申请已通过，欢迎加入 {club.name}！"
    elif data.action == "reject":
        req.status = "rejected"
        req.reviewed_at = datetime.utcnow()
        msg = f"您的入社申请({club.name})已被拒绝"
    else:
        raise HTTPException(status_code=400, detail="无效操作")

    db.add(Notification(
        sender_id=user.id, receiver_id=applicant.id, club_id=club_id,
        title="入社申请结果", content=msg,
        source_label=f"{club.name}-系统", category="club"
    ))
    db.commit()
    if data.action == "approve":
        calculate_star_rating(db, club_id)
    return {"message": "处理成功"}


@router.post("/{club_id}/kick/{user_id}")
def kick_member(club_id: int, user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = db.query(Club).get(club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    if club.president_id != user.id and user.role.value != "admin":
        raise HTTPException(status_code=403, detail="仅负责人或管理员可踢出成员")

    target = db.query(User).get(user_id)
    if not target or target.club_id != club_id:
        raise HTTPException(status_code=400, detail="该用户不在本社团中")
    if target.id == club.president_id:
        raise HTTPException(status_code=400, detail="不能踢出社团负责人")

    target.club_id = None
    target.role = "member"
    club.member_count = max(0, club.member_count - 1)

    db.add(Notification(
        sender_id=user.id, receiver_id=target.id, club_id=club_id,
        title="您已被移出社团", content=f"您已被移出 {club.name}",
        source_label=f"{club.name}-系统", category="club"
    ))
    db.commit()
    return {"message": f"已将 {target.real_name} 踢出社团"}
