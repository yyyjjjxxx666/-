from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from . import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = broadcast
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)      # scope filter
    target_type = Column(String(20), default="all")  # all / club / unaffiliated
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    source_label = Column(String(100), nullable=False)  # e.g. "校联社" or "AI创新社-张三"
    category = Column(String(20), default="system")  # system / club / activity
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
