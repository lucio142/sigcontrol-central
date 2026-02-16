# api/app/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SigControl Central"
    ENV: str = "dev"
    CORS_ORIGINS: str = "*"

    DATABASE_URL: str

    JWT_SECRET: str
    JWT_EXPIRE_MIN: int = 480

    ADMIN_EMAIL: str = "admin@empresa.com"
    ADMIN_PASSWORD: str = "Admin123!"

    # Roles con permiso de edición en UI (mover puertas, permisos, etc.)
    EDIT_ROLES: str = "admin,hsc,sistemas"

settings = Settings()

def get_edit_roles() -> set[str]:
    raw = (os.getenv("EDIT_ROLES") or settings.EDIT_ROLES or "").strip()
    if not raw:
        return {"admin"}
    return {r.strip() for r in raw.split(",") if r.strip()}
