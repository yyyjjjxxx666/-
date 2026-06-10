from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from ..models.user import UserRole


# ── Auth ──
class UserRegister(BaseModel):
    username: str
    password: str
    real_name: str
    role: UserRole = UserRole.MEMBER
    student_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    interests: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    real_name: str
    club_id: Optional[int] = None


class UserInfo(BaseModel):
    id: int
    username: str
    role: UserRole
    real_name: str
    student_id: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    interests: Optional[str]
    avatar_url: Optional[str]
    club_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Club ──
class ClubCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tags: Optional[str] = None
    logo_url: Optional[str] = None


class ClubInfo(BaseModel):
    id: int
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    president_id: int
    status: str
    member_count: int
    activity_count: int
    tags: Optional[str]
    star_rating: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Activity ──
class ActivityCreate(BaseModel):
    club_id: int
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    registration_deadline: Optional[datetime] = None
    max_participants: Optional[int] = None
    poster_url: Optional[str] = None


class ActivityInfo(BaseModel):
    id: int
    club_id: int
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: datetime
    registration_deadline: Optional[datetime]
    max_participants: Optional[int]
    status: str
    poster_url: Optional[str]
    current_participants: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── AI ──
class RecommendRequest(BaseModel):
    user_id: int
    top_k: int = 5


class GenerateTextRequest(BaseModel):
    prompt: str
    max_tokens: int = 500


class GeneratePosterRequest(BaseModel):
    activity_id: int
    template_style: str = "default"


class StarRatingRequest(BaseModel):
    club_id: int


# ── Face ──
class FaceRegisterRequest(BaseModel):
    user_id: Optional[int] = None
    image_data: Optional[str] = None  # base64


# ── Notification ──
class NotificationCreate(BaseModel):
    title: str
    content: str
    target: str = "all"  # all / club / unaffiliated
    club_id: Optional[int] = None    # required when target=club


class NotificationInfo(BaseModel):
    id: int
    sender_id: int
    title: str
    content: str
    source_label: str
    category: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── User Profile ──
class UpdateInterestsRequest(BaseModel):
    interests: str


class UserMeInfo(BaseModel):
    id: int
    username: str
    role: str
    real_name: str
    interests: Optional[str] = None
    club_id: Optional[int] = None
    face_registered: bool = False
    student_id: Optional[str] = None

    class Config:
        from_attributes = True


# ── Reset Password ──
class ResetPasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ── Transfer ──
class TransferRequest(BaseModel):
    new_president_id: int


# ── Join Request ──
class JoinRequestAction(BaseModel):
    action: str  # "approve" or "reject"
