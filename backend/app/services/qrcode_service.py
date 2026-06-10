"""活动签到二维码生成服务。"""
import os
import qrcode
from ..core.config import settings


def generate_checkin_qr(activity_id: int, activity_title: str) -> str:
    """为活动生成签到二维码，返回文件路径。"""
    os.makedirs(settings.POSTER_DIR, exist_ok=True)

    # QR content: activity check-in URL
    qr_data = f"checkin://activity/{activity_id}"

    img = qrcode.make(qr_data)
    filename = f"qr_{activity_id}.png"
    path = os.path.join(settings.POSTER_DIR, filename)
    img.save(path)

    return f"/static/posters/{filename}"
