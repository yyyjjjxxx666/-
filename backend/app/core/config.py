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

    class Config:
        # 优先使用环境变量指定的绝对路径 (exe模式下由main.py设置)
        # 回退到当前目录下的 .env (开发模式)
        env_file = os.environ.get("PYDANTIC_SETTINGS_ENV_FILE", ".env")
        extra = "ignore"  # ignore deprecated fields in old .env files (e.g. REDIS_URL)


settings = Settings()
