"""人脸识别签到服务。使用 OpenCV 内置 Haar Cascade + LBPH 识别器。
Windows 上无需安装 dlib/face_recognition，开箱即用。
"""
import os
import json
import pickle
import numpy as np
import cv2

from sqlalchemy.orm import Session
from ..models.user import User

# LBPH模型存储路径
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "static", "face_model.yml")
LABELS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "static", "face_labels.pkl")

# Haar Cascade 分类器
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def _detect_face(image_path: str):
    """检测图像中的最大人脸，返回裁剪后的人脸灰度图。"""
    cascade = cv2.CascadeClassifier(CASCADE_PATH)
    img = cv2.imread(image_path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    # 取最大的人脸
    (x, y, w, h) = max(faces, key=lambda r: r[2] * r[3])
    return gray[y:y+h, x:x+w]


def register_face(db: Session, user_id: int, image_path: str) -> dict:
    """为用户注册人脸。"""
    face = _detect_face(image_path)
    if face is None:
        return {"success": False, "message": "未检测到人脸，请确保光线充足、正对摄像头"}

    # Resize to consistent size for LBPH
    face_resized = cv2.resize(face, (200, 200))

    user = db.query(User).get(user_id)
    if not user:
        return {"success": False, "message": "用户不存在"}

    # Store the face image path for later training
    user_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "faces", str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    img_path = os.path.join(user_dir, "face.jpg")
    # Convert grayscale to BGR for browser-compatible JPEG
    face_bgr = cv2.cvtColor(face_resized, cv2.COLOR_GRAY2BGR)
    cv2.imwrite(img_path, face_bgr)
    user.face_encoding = img_path  # Store path instead of encoding
    db.commit()

    # Retrain the model
    _train_model(db)
    return {"success": True, "message": "人脸注册成功，请重新训练模型"}


def _train_model(db: Session):
    """使用所有已注册用户的人脸训练 LBPH 识别器。"""
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces_data = []
    labels = []
    label_map = {}  # label -> user_id

    # Walk through face directories
    faces_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "faces")
    if not os.path.exists(faces_dir):
        return

    current_label = 0
    for user_dir in os.listdir(faces_dir):
        user_path = os.path.join(faces_dir, user_dir)
        if not os.path.isdir(user_path):
            continue
        for img_file in os.listdir(user_path):
            if img_file.endswith((".jpg", ".png", ".jpeg")):
                img = cv2.imread(os.path.join(user_path, img_file), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, (200, 200))
                    faces_data.append(img)
                    labels.append(current_label)
        label_map[current_label] = int(user_dir)
        current_label += 1

    if faces_data:
        recognizer.train(faces_data, np.array(labels))
        recognizer.save(MODEL_PATH)
        with open(LABELS_PATH, "wb") as f:
            pickle.dump(label_map, f)


def recognize_face(image_path: str, known_users: list[dict] = None) -> dict:
    """识别图像中的人脸。"""
    face = _detect_face(image_path)
    if face is None:
        return {"success": False, "message": "未检测到人脸"}

    face_resized = cv2.resize(face, (200, 200))

    if not os.path.exists(MODEL_PATH):
        return {"success": False, "message": "人脸模型未训练，请先注册人脸"}

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)

    with open(LABELS_PATH, "rb") as f:
        label_map = pickle.load(f)

    label, confidence = recognizer.predict(face_resized)
    # LBPH confidence: lower is better, 0 = perfect match
    threshold = 70
    if confidence < threshold:
        user_id = label_map.get(label)
        # Convert confidence to percentage (lower LBPH confidence = higher our confidence)
        conf_pct = round(max(0, (threshold - confidence) / threshold) * 100, 1)
        return {"success": True, "user_id": user_id, "confidence": conf_pct}
    return {"success": False, "message": f"人脸不匹配（置信度不足）"}
