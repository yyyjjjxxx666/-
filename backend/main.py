import os
# Prevent HuggingFace from trying to connect (blocked in China, model cached locally)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import sys
import shutil
import signal
import atexit
import time

# ============================================================
# First-run auto-config: copy bundled .env.template to .env
# when running as a frozen PyInstaller exe and no .env exists
# ============================================================
if getattr(sys, 'frozen', False):
    _exe_dir = os.path.dirname(sys.executable)
    _dest_env = os.path.join(_exe_dir, ".env")
    if not os.path.exists(_dest_env):
        _bundled_template = os.path.join(sys._MEIPASS, ".env.template")
        if os.path.exists(_bundled_template):
            shutil.copy(_bundled_template, _dest_env)
            print(f"[首次运行] 已生成配置文件: {_dest_env}")
            print("[首次运行] 请编辑该文件中的数据库配置和API密钥后重新启动程序")
            print("[首次运行] 程序将在 5 秒后退出...")
            time.sleep(5)
            sys.exit(0)
    # 关键：让 pydantic-settings 使用 .env 的绝对路径
    # 避免因工作目录不同而找不到 .env 文件
    os.environ["PYDANTIC_SETTINGS_ENV_FILE"] = _dest_env

import webbrowser
import threading
import mimetypes
from contextlib import asynccontextmanager

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from app.api import api_router
from app.models import Base, engine
from app.models.user import User
from app.models.club import Club, JoinRequest
from app.models.activity import Activity, ActivityRegistration, Checkin
from app.models.notification import Notification
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fix MIME types + trailing slash redirect for nested API routers
APP_LEVEL_ROUTES = {"/api/health"}  # Routes that must NOT receive trailing slash

API_COLLECTIONS = {"clubs", "activities", "auth", "ai", "notifications", "admin", "home"}  # Top-level API prefixes

@app.middleware("http")
async def fix_mime_types(request, call_next):
    path = request.url.path

    # Redirect /api/{collection} → /api/{collection}/ for nested router compatibility
    if path.startswith("/api/") and not path.endswith("/"):
        parts = path.split("/")
        # Only redirect top-level collection paths like /api/clubs, not /api/health or /api/clubs/1
        if len(parts) == 3 and parts[2] in API_COLLECTIONS:
            return RedirectResponse(url=f"{path}/", status_code=307)

    response = await call_next(request)
    if path.endswith(".js") or path.endswith(".mjs"):
        response.headers["Content-Type"] = "application/javascript; charset=utf-8"
    elif path.endswith(".css"):
        response.headers["Content-Type"] = "text/css; charset=utf-8"
    return response

app.include_router(api_router, prefix="/api")

# Base directory (works for both dev and PyInstaller)
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# Ensure directories exist
static_dir = os.path.join(BASE_DIR, "static")
posters_dir = os.path.join(static_dir, "posters")
uploads_dir = os.path.join(BASE_DIR, settings.UPLOAD_DIR)
os.makedirs(posters_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/api/home/recent-activities")
def recent_activities():
    from app.models import SessionLocal
    from app.models.activity import Activity, ActivityStatus
    from app.schemas import ActivityInfo
    db = SessionLocal()
    try:
        activities = db.query(Activity).filter(
            Activity.status.in_([ActivityStatus.APPROVED, ActivityStatus.REGISTRATION, ActivityStatus.ONGOING])
        ).order_by(Activity.created_at.desc()).limit(3).all()
        return [ActivityInfo.model_validate(a).model_dump() for a in activities]
    finally:
        db.close()


import uuid
from fastapi import UploadFile, File

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持JPG/PNG/GIF/WEBP格式")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过5MB")
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(uploads_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return {"url": f"/uploads/{filename}"}


@app.get("/api/health")
def health():
    return {"status": "ok", "name": settings.APP_NAME}


# Frontend SPA hosting
frontend_dir = os.path.join(BASE_DIR, "..", "frontend", "dist")
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ============================================================
# Graceful shutdown: release port immediately when console closed
# ============================================================
_uvicorn_server = None

def _cleanup():
    """释放资源，确保端口立即回收"""
    global _uvicorn_server
    if _uvicorn_server:
        _uvicorn_server.should_exit = True

def _signal_handler(signum, frame):
    _cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# Windows 控制台关闭事件 (CTRL_CLOSE_EVENT)
# 使用 ctypes 调用 kernel32.SetConsoleCtrlHandler（无需安装额外包）
if sys.platform == "win32":
    import ctypes
    _WIN_CTRL_CLOSE_EVENT = 2
    _HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)

    @_HandlerRoutine
    def _win_handler(ctrl_type):
        if ctrl_type == _WIN_CTRL_CLOSE_EVENT:
            _cleanup()
            return True
        return False

    if not ctypes.windll.kernel32.SetConsoleCtrlHandler(_win_handler, True):
        pass  # 注册失败时回退到 signal 处理器

atexit.register(_cleanup)


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    import uvicorn
    if getattr(sys, 'frozen', False):
        threading.Thread(target=open_browser, daemon=True).start()

    # 使用 uvicorn.Server 实例以便能调用 should_exit 优雅关闭
    _uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    _uvicorn_server = uvicorn.Server(_uvicorn_config)
    _uvicorn_server.run()
