"""Firebase Admin initialization and verified bearer identity dependencies."""
import os
from functools import lru_cache

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from database import get_db
from models import AdminPermission, User

PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "errno-pvt-ltd")
_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def firebase_app():
    """Initialize once per process, using ADC or GOOGLE_APPLICATION_CREDENTIALS."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass
    credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    credential = credentials.Certificate(credential_path) if credential_path else credentials.ApplicationDefault()
    return firebase_admin.initialize_app(credential, {"projectId": PROJECT_ID})


def verify_firebase_token(token: str) -> dict:
    """Verify signature, expiry, issuer, audience and project using Firebase Admin."""
    try:
        claims = auth.verify_id_token(token, app=firebase_app(), check_revoked=True)
        if claims.get("aud") != PROJECT_ID or claims.get("iss") != f"https://securetoken.google.com/{PROJECT_ID}":
            raise ValueError("Wrong Firebase project")
        if not isinstance(claims.get("uid"), str) or not claims["uid"]:
            raise ValueError("Missing Firebase UID")
        return claims
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from None
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service unavailable") from None


def verified_claims(credentials_: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if credentials_ is None or credentials_.scheme.lower() != "bearer" or not credentials_.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")
    return verify_firebase_token(credentials_.credentials)


def authenticated_user(
    claims: dict = Depends(verified_claims),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.firebase_uid == claims["uid"]).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


def require_role(user: User, *roles: str) -> None:
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This action is not available for your role")


def require_admin(permission: str | None = None):
    """Return a dependency enforcing persisted, operator-controlled admin access."""
    def dependency(
        claims: dict = Depends(verified_claims),
        db: Session = Depends(get_db),
    ) -> AdminPermission:
        admin = db.query(AdminPermission).filter(
            AdminPermission.firebase_uid == claims["uid"],
        ).first()
        if admin is None or not admin.active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
        account = db.query(User).filter(User.firebase_uid == claims["uid"]).first()
        if account is not None and not account.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator account is disabled")
        if permission is not None and permission not in (admin.permissions or []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permission required")
        return admin
    return dependency
