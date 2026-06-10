from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from . import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"          # 校社联管理员
    PRESIDENT = "president"  # 社团负责人
    MEMBER = "member"        # 普通成员


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.MEMBER)
    real_name = Column(String(50), nullable=False)
    student_id = Column(String(20), unique=True, nullable=True)  # 学号/工号
    phone = Column(String(20), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    interests = Column(Text, nullable=True)  # 兴趣标签，逗号分隔
    avatar_url = Column(String(255), nullable=True)
    face_encoding = Column(Text, nullable=True)  # 人脸特征编码（JSON）
    created_at = Column(DateTime, default=datetime.utcnow)

    club_id = Column(Integer, nullable=True)  # 所属社团ID（成员时使用）
