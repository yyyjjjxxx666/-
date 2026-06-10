"""AI星级社团评选：基于活动数量、成员活跃度、签到率等维度加权评分。"""
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.club import Club
from ..models.activity import Activity, Checkin


def calculate_star_rating(db: Session, club_id: int) -> float:
    """计算社团综合评分（满分5星）。"""
    club = db.query(Club).get(club_id)
    if not club:
        return 0.0

    # 活动数量得分
    total_activities = db.query(Activity).filter(Activity.club_id == club_id).count()
    activity_score = min(total_activities / 10, 1.0) * 20  # 0-20分

    # 成员规模得分
    member_score = min(club.member_count / 100, 1.0) * 20  # 0-20分

    # 签到率得分
    checkins = (
        db.query(func.count(Checkin.id))
        .join(Activity, Checkin.activity_id == Activity.id)
        .filter(Activity.club_id == club_id)
        .scalar()
    )
    # 假设每次活动平均10人签到
    expected_checkins = total_activities * 10
    attendance_rate = min(checkins / max(expected_checkins, 1), 1.0) if total_activities > 0 else 0
    attendance_score = attendance_rate * 30  # 0-30分

    # 活动多样性（通过活动描述长度简单评估）
    diverse_score = 15  # 基础分
    descriptions = (
        db.query(Activity.description)
        .filter(Activity.club_id == club_id, Activity.description.isnot(None))
        .all()
    )
    if descriptions:
        avg_len = sum(len(d[0]) for d in descriptions) / len(descriptions)
        diverse_score = min(avg_len / 100, 1.0) * 15 + 15

    total = activity_score + member_score + attendance_score + diverse_score
    stars = round(total / 20, 1)  # 转换为5分制
    stars = max(0.1, min(5.0, stars))

    # Update club
    club.star_rating = stars
    db.commit()

    return stars
