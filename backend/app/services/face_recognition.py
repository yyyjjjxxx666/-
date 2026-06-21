"""人脸识别签到服务。使用 OpenCV 内置 Haar Cascade + LBPH 识别器。
Windows 上无需安装 dlib/face_recognition，开箱即用。
"""
import os
import json
import pickle
import logging
import numpy as np
import cv2

from sqlalchemy.orm import Session
from ..models.user import User
from ..core.config import settings

logger = logging.getLogger(__name__)

# LBPH 模型存储路径（使用 settings 统一路径）
MODEL_PATH = os.path.join(settings.STATIC_DIR_ABS, "face_model.yml")
LABELS_PATH = os.path.join(settings.STATIC_DIR_ABS, "face_labels.pkl")

# 人脸图片存储目录
FACES_DIR = settings.FACES_DIR_ABS

# Haar Cascade 分类器（使用项目捆绑的本地副本，exe模式下也能正常加载）
_CASCADE_FILENAME = "haarcascade_frontalface_default.xml"
_CASCADE_PATH_LOCAL = os.path.join(settings.BASE_DIR, "static", _CASCADE_FILENAME)
# 回退：如果本地副本不存在（比如开发环境未复制），则使用 OpenCV 自带的
if os.path.exists(_CASCADE_PATH_LOCAL):
    CASCADE_PATH = _CASCADE_PATH_LOCAL
else:
    CASCADE_PATH = cv2.data.haarcascades + _CASCADE_FILENAME


def _detect_face(image_path: str):
    """检测图像中的最大人脸，返回裁剪后的人脸灰度图。"""
    try:
        cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if cascade.empty():
            logger.warning("Haar Cascade 分类器加载失败: %s", CASCADE_PATH)
            return None
        img = cv2.imread(image_path)
        if img is None:
            logger.warning("无法读取图片: %s", image_path)
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return None
        # 取最大的人脸
        (x, y, w, h) = max(faces, key=lambda r: r[2] * r[3])
        return gray[y:y+h, x:x+w]
    except Exception as e:
        logger.exception("人脸检测异常: %s", e)
        return None


def register_face(db: Session, user_id: int, image_path: str) -> dict:
    """为用户注册人脸。"""
    try:
        face = _detect_face(image_path)
        if face is None:
            return {"success": False, "message": "未检测到人脸，请确保光线充足、正对摄像头"}

        # Resize to consistent size for LBPH
        face_resized = cv2.resize(face, (200, 200))

        user = db.query(User).get(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 存储人脸图片到统一的人脸目录
        user_dir = os.path.join(FACES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        img_path = os.path.join(user_dir, "face.jpg")
        # 灰度转 BGR 以便浏览器兼容显示
        face_bgr = cv2.cvtColor(face_resized, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(img_path, face_bgr)
        user.face_encoding = img_path  # 存储文件路径
        db.commit()

        # 重新训练模型
        train_result = _train_model()
        if not train_result["success"]:
            logger.warning("模型训练警告: %s", train_result.get("message"))
        return {"success": True, "message": "人脸注册成功"}
    except Exception as e:
        logger.exception("人脸注册异常: %s", e)
        db.rollback()
        return {"success": False, "message": f"人脸注册失败: {str(e)}"}


def _train_model() -> dict:
    """使用所有已注册用户的人脸训练 LBPH 识别器。"""
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        faces_data = []
        labels = []
        label_map = {}  # label -> user_id

        if not os.path.exists(FACES_DIR):
            return {"success": True, "message": "人脸目录为空，跳过训练"}

        current_label = 0
        for user_dir_name in os.listdir(FACES_DIR):
            user_path = os.path.join(FACES_DIR, user_dir_name)
            if not os.path.isdir(user_path):
                continue

            # 验证目录名为数字（user_id）
            try:
                user_id = int(user_dir_name)
            except (ValueError, TypeError):
                logger.warning("跳过非用户目录: %s", user_dir_name)
                continue

            # 收集该用户的所有人脸图片
            user_faces = []
            for img_file in os.listdir(user_path):
                if img_file.endswith((".jpg", ".png", ".jpeg")):
                    img = cv2.imread(os.path.join(user_path, img_file), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        img = cv2.resize(img, (200, 200))
                        user_faces.append(img)

            # 只有该用户至少有一张有效人脸图片时，才分配标签
            if user_faces:
                faces_data.extend(user_faces)
                labels.extend([current_label] * len(user_faces))
                label_map[current_label] = user_id
                current_label += 1
            else:
                logger.warning("用户 %d 无有效人脸图片，跳过", user_id)

        if faces_data:
            recognizer.train(faces_data, np.array(labels))
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            recognizer.save(MODEL_PATH)
            os.makedirs(os.path.dirname(LABELS_PATH), exist_ok=True)
            with open(LABELS_PATH, "wb") as f:
                pickle.dump(label_map, f)
            logger.info("人脸模型已训练: %d 个用户, %d 张图片", len(label_map), len(faces_data))
        else:
            logger.info("无有效人脸数据，跳过模型训练")

        return {"success": True, "message": "模型训练完成"}
    except Exception as e:
        logger.exception("模型训练异常: %s", e)
        return {"success": False, "message": f"模型训练失败: {str(e)}"}


def recognize_face(image_path: str, known_users: list[dict] = None) -> dict:
    """识别图像中的人脸。"""
    try:
        face = _detect_face(image_path)
        if face is None:
            return {"success": False, "message": "未检测到人脸"}

        face_resized = cv2.resize(face, (200, 200))

        if not os.path.exists(MODEL_PATH):
            return {"success": False, "message": "人脸模型未训练，请先注册人脸"}
        if not os.path.exists(LABELS_PATH):
            return {"success": False, "message": "人脸标签数据缺失，请重新训练模型"}

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_PATH)

        with open(LABELS_PATH, "rb") as f:
            label_map = pickle.load(f)

        label, confidence = recognizer.predict(face_resized)
        # LBPH confidence: lower is better, 0 = perfect match
        threshold = 70
        if confidence < threshold:
            user_id = label_map.get(label)
            # 将 LBPH 置信度转换为百分比（值越低 → 百分比越高）
            conf_pct = round(max(0, (threshold - confidence) / threshold) * 100, 1)
            return {"success": True, "user_id": user_id, "confidence": conf_pct}
        return {"success": False, "message": "人脸不匹配（置信度不足）"}
    except Exception as e:
        logger.exception("人脸识别异常: %s", e)
        return {"success": False, "message": f"人脸识别失败: {str(e)}"}
