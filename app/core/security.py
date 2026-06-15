from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.core.config import get_settings

security = HTTPBearer()


def create_access_token(subject: str, scopes: Optional[list] = None, expires_minutes: int = 60) -> str:
    settings = get_settings()
    to_encode: Dict[str, Any] = {"sub": subject, "scopes": scopes or []}
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt


def get_current_admin(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    token = credentials.credentials
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    scopes = payload.get("scopes", [])
    if "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return payload
