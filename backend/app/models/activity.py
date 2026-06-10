from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SAEnum, Float, Boolean
from datetime import datetime
import enum

from . import Base


class ActivityStatus(str, enum.Enum):
    PENDING = "pending"        # 待审批
    APPROVED = "approved"      # 已通过
    REJECTED = "rejected"      # 已拒绝
    REGISTRATION = "registration"  # 报名中
    ONGOING = "ongoing"        # 进行中
    FINISHED = "finished"      # 已结束


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    club_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    registration_deadline = Column(DateTime, nullable=True)
    max_participants = Column(Integer, nullable=True)
    status = Column(SAEnum(ActivityStatus), nullable=False, default=ActivityStatus.PENDING)
    poster_url = Column(String(255), nullable=True)  # AI生成的海报
    checkin_qr = Column(String(255), nullable=True)  # 签到二维码
    current_participants = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityRegistration(Base):
    __tablename__ = "activity_registrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    checkin_time = Column(DateTime, default=datetime.utcnow)
    method = Column(String(20), default="qr")  # qr / face
    status = Column(String(20), default="on_time")  # on_time / late / early
