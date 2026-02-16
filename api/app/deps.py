from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import decode_token
from app import models
from app.config import get_edit_roles

bearer = HTTPBearer(auto_error=True)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.StaffUser:
    token = creds.credentials
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.StaffUser).filter(models.StaffUser.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    return user

def require_roles(*roles: str):
    def _guard(u: models.StaffUser = Depends(get_current_user)) -> models.StaffUser:
        if u.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return u
    return _guard

def require_edit_access():
    """
    Permite editar a roles definidos en .env:
    EDIT_ROLES=hsc,sistemas
    """
    roles = tuple(get_edit_roles())
    return require_roles(*roles)
