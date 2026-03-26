from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────
    APP_NAME: str = "GymBrain"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # production | staging

    # ── Security ─────────────────────────────────────────────────
    SECRET_KEY: str                          # flyctl secrets set SECRET_KEY=...
    ALGORITHM: str = "HS256"

    # ── CORS (your Flutter app domains) ──────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "https://gymbrain.app",
        "https://www.gymbrain.app",
        "capacitor://localhost",             # Flutter mobile WebView
        "ionic://localhost",
    ]

    # ── PostgreSQL (Supabase) ─────────────────────────────────────
    # Get from: Supabase → Settings → Database → Connection string (URI mode)
    DATABASE_URL: str                        # postgresql+asyncpg://...

    # ── Redis (Upstash) ──────────────────────────────────────────
    # Get from: Upstash console → Redis → Details → REST URL
    REDIS_URL: str                           # rediss://...  (TLS URL from Upstash)

    # ── Firebase ─────────────────────────────────────────────────
    FIREBASE_PROJECT_ID: str
    # Paste the full JSON content of your service account key as a single string
    FIREBASE_CREDENTIALS_JSON: str           # flyctl secrets set FIREBASE_CREDENTIALS_JSON="$(cat firebase.json)"

    # ── Gemini AI ────────────────────────────────────────────────
    GEMINI_API_KEY: str                      # flyctl secrets set GEMINI_API_KEY=...
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ── Firebase Cloud Messaging (Push Notifications) ─────────────
    FCM_SERVER_KEY: str = ""                 # From Firebase Console → Project Settings → Cloud Messaging

    # ── Email (Resend — production email service) ─────────────────
    RESEND_API_KEY: str = ""                 # https://resend.com — free 3000 emails/month
    EMAIL_FROM: str = "noreply@gymbrain.app"

    # ── Celery (uses Upstash Redis) ───────────────────────────────
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL

    # ── Storage (Cloudflare R2 / S3-compatible) ───────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "gymbrain-media"
    R2_PUBLIC_URL: str = ""                  # https://media.gymbrain.app

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
