from pydantic_settings import BaseSettings
import sys
import os


class Settings(BaseSettings):
    APP_NAME: str = "社团管理与活动报名系统"
    DEBUG: bool = True

    # Database type: "auto" (detect from credentials), "sqlite" or "mysql"
    DB_TYPE: str = "auto"

    # SQLite
    SQLITE_PATH: str = "club_system.db"

    # MySQL (only used when DB_TYPE=mysql, or auto-detected when credentials present)
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "club_system"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # DeepSeek API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # File paths
    UPLOAD_DIR: str = "uploads"
    POSTER_DIR: str = "static/posters"

    @property
    def DATABASE_URL(self) -> str:
        db_type = self.DB_TYPE
        # Auto-detect: if MySQL credentials are provided, use MySQL; otherwise SQLite
        if db_type == "auto":
            db_type = "mysql" if (self.DB_PASSWORD and self.DB_HOST) else "sqlite"
        if db_type == "mysql":
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        # SQLite: resolve path next to exe when frozen
        db_path = self.SQLITE_PATH
        if getattr(sys, 'frozen', False) and not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(sys.executable), db_path)
        return f"sqlite:///{db_path}"

    @property
    def BASE_DIR(self) -> str:
        """应用根目录（开发模式为backend/，exe模式为_MEIPASS临时目录）"""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        # 开发模式：config.py 在 app/core/ 下，上两级即 backend/
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    @property
    def DATA_DIR(self) -> str:
        """持久数据目录（exe模式下为exe同级目录，开发模式下同BASE_DIR）。
        上传文件、人脸图片、生成的海报等运行时数据存放于此，exe重启后不丢失。"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return self.BASE_DIR

    @property
    def UPLOAD_DIR_ABS(self) -> str:
        """上传目录的绝对路径（与main.py中StaticFiles挂载的目录一致）"""
        return os.path.join(self.DATA_DIR, self.UPLOAD_DIR)

    @property
    def FACES_DIR_ABS(self) -> str:
        """人脸图片存储的绝对路径"""
        return os.path.join(self.UPLOAD_DIR_ABS, "faces")

    @property
    def STATIC_DIR_ABS(self) -> str:
        """静态文件目录的绝对路径（face_model、posters等运行时生成的文件）"""
        return os.path.join(self.DATA_DIR, "static")

    class Config:
        # 优先使用环境变量指定的绝对路径 (exe模式下由main.py设置)
        # 回退到当前目录下的 .env (开发模式)
        env_file = os.environ.get("PYDANTIC_SETTINGS_ENV_FILE", ".env")
        extra = "ignore"  # ignore deprecated fields in old .env files (e.g. REDIS_URL)


settings = Settings()
