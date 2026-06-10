from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SAEnum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from . import Base


class ClubStatus(str, enum.Enum):
    PENDING = "pending"          # 待审批
    APPROVED = "approved"        # 已通过
    REJECTED = "rejected"        # 已拒绝
    DISSOLVE_PENDING = "dissolve_pending"  # 注销待审批


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    logo_url = Column(String(255), nullable=True)
    president_id = Column(Integer, nullable=False)  # 社团负责人 user id
    status = Column(SAEnum(ClubStatus), nullable=False, default=ClubStatus.PENDING)
    member_count = Column(Integer, default=0)
    activity_count = Column(Integer, default=0)
    tags = Column(String(255), nullable=True)  # 标签，逗号分隔
    star_rating = Column(Float, nullable=True)  # AI评选星级
    created_at = Column(DateTime, default=datetime.utcnow)


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    club_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
