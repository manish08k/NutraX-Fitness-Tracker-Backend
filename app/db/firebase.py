import json
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings
from app.core.logger import logger

_app: firebase_admin.App | None = None


def init_firebase() -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK.
    Credentials are loaded from FIREBASE_CREDENTIALS_JSON env var
    (a JSON string of the service account key file).
    This avoids needing a credentials file on the server.
    """
    global _app
    if _app is not None:
        return _app

    try:
        cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(cred_dict)
        _app = firebase_admin.initialize_app(cred, {
            "projectId": settings.FIREBASE_PROJECT_ID,
        })
        logger.info(f"✅ Firebase initialized (project: {settings.FIREBASE_PROJECT_ID})")
    except json.JSONDecodeError:
        logger.error("❌ FIREBASE_CREDENTIALS_JSON is not valid JSON")
        raise
    except Exception as e:
        logger.error(f"❌ Firebase init failed: {e}")
        raise
    return _app


def get_firebase_auth():
    return auth
