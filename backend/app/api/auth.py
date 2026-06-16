from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models import get_db
from ..models.user import User, UserRole
from ..models.club import Club
from ..schemas import UserRegister, UserLogin, Token, UserInfo, UpdateInterestsRequest, UserMeInfo, ResetPasswordRequest
from ..core.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(tags=["认证"])


def get_current_user(authorization: str = __import__("fastapi").Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return db.query(User).get(int(payload["sub"]))


@router.get("/search-users")
def search_users(
    q: str = Query(..., min_length=1, description="搜索关键词（姓名/用户名/学号）"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search users by real_name, username, or student_id. Admin/president only."""
    if user.role.value not in ("admin", "president"):
        raise HTTPException(status_code=403, detail="仅管理员或社团负责人可搜索用户")

    pattern = f"%{q}%"
    users = (
        db.query(User)
        .filter(
            or_(
                User.real_name.ilike(pattern),
                User.username.ilike(pattern),
                User.student_id.ilike(pattern),
            )
        )
        .limit(20)
        .all()
    )

    results = []
    for u in users:
        club_name = None
        if u.club_id:
            club = db.query(Club).get(u.club_id)
            club_name = club.name if club else None
        results.append({
            "id": u.id,
            "username": u.username,
            "real_name": u.real_name,
            "student_id": u.student_id,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "club_name": club_name,
        })
    return results


@router.post("/register", response_model=UserInfo)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if data.student_id and db.query(User).filter(User.student_id == data.student_id).first():
        raise HTTPException(status_code=400, detail="学号已注册")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role="member",  # All self-registered users are members; president is granted on club approval
        real_name=data.real_name,
        student_id=data.student_id or None,
        phone=data.phone or None,
        email=data.email or None,
        interests=data.interests or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return Token(
        access_token=token,
        user_id=user.id,
        role=user.role.value,
        real_name=user.real_name,
        club_id=user.club_id,
    )


@router.get("/me", response_model=dict)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import os
    face_registered = bool(user.face_encoding) if user.face_encoding else False
    return {
        "id": user.id, "username": user.username, "role": user.role.value,
        "real_name": user.real_name, "interests": user.interests,
        "club_id": user.club_id, "student_id": user.student_id,
        "face_registered": face_registered,
    }


@router.put("/interests")
def update_interests(data: UpdateInterestsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.interests = data.interests
    db.commit()
    return {"message": "兴趣已更新", "interests": data.interests}


@router.get("/check-face/{user_id}")
def check_face(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"user_id": user_id, "face_registered": bool(u.face_encoding)}


def get_current_user_dep(authorization: str = __import__("fastapi").Header(...), db: Session = Depends(get_db)) -> User:
    return get_current_user(authorization, db)


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, user: User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "密码已重置"}
