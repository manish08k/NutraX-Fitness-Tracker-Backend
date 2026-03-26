from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth
from app.core.logger import logger


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token.
    Returns decoded claims: uid, email, name, picture, email_verified, etc.
    Raises 401 if invalid/expired.
    """
    try:
        decoded = firebase_auth.verify_id_token(id_token, check_revoked=True)
        return decoded
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please sign in again.",
        )
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
        )
    except firebase_auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    except Exception as e:
        logger.error(f"Firebase token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        )
