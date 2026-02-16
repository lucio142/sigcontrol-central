# api/app/crud.py
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app import models
from app.security import hash_password, verify_password

from datetime import datetime, timezone, timedelta


# =========================
# HELPERS
# =========================

def clamp01(v: float) -> float:
    try:
        v = float(v)
    except Exception:
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v

def normalize_uid(uid: str) -> str:
    return (uid or "").strip().upper().replace(" ", "")


# =========================
# STAFF USERS
# =========================

def get_staff_user_by_email(db: Session, email: str) -> models.StaffUser | None:
    email = (email or "").strip().lower()
    return db.query(models.StaffUser).filter(models.StaffUser.email == email).first()

def create_staff_user(
    db: Session,
    email: str,
    password: str,
    role: str,
    is_active: bool = True,
) -> models.StaffUser:
    email = (email or "").strip().lower()
    existing = get_staff_user_by_email(db, email)
    if existing:
        return existing

    u = models.StaffUser(
        email=email,
        password_hash=hash_password(password),  # bcrypt-safe (72 bytes)
        role=(role or "").strip(),
        is_active=bool(is_active),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def authenticate_staff_user(db: Session, email: str, password: str) -> models.StaffUser | None:
    u = get_staff_user_by_email(db, email)
    if not u or not u.is_active:
        return None
    if not verify_password(password, u.password_hash):
        return None
    return u


# =========================
# DOORS
# =========================

def get_door_by_code(db: Session, door_id: str) -> models.Door | None:
    door_id = (door_id or "").strip()
    return db.query(models.Door).filter(models.Door.door_id == door_id).first()

def list_doors(db: Session) -> list[models.Door]:
    return db.query(models.Door).order_by(models.Door.id.asc()).all()

def list_doors_by_site(db: Session, site: str) -> list[models.Door]:
    site = (site or "main").strip() or "main"
    return (
        db.query(models.Door)
        .filter(models.Door.site == site)
        .order_by(models.Door.id.asc())
        .all()
    )

def create_door(
    db: Session,
    door_id: str,
    name: str = "",
    location: str = "",
    is_enabled: bool = True,
    site: str = "main",
    x: float = 0.5,
    y: float = 0.5,
) -> models.Door:
    existing = get_door_by_code(db, door_id)
    if existing:
        return existing

    d = models.Door(
        door_id=(door_id or "").strip(),
        name=name or "",
        location=location or "",
        is_enabled=bool(is_enabled),
        site=(site or "main").strip() or "main",
        x=clamp01(x),
        y=clamp01(y),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d

def update_door(
    db: Session,
    door: models.Door,
    name: str,
    location: str,
    is_enabled: bool,
    site: str | None = None,
    x: float | None = None,
    y: float | None = None,
) -> models.Door:
    door.name = name or ""
    door.location = location or ""
    door.is_enabled = bool(is_enabled)

    if site is not None:
        door.site = (site or "main").strip() or "main"
    if x is not None:
        door.x = clamp01(x)
    if y is not None:
        door.y = clamp01(y)

    db.commit()
    db.refresh(door)
    return door

def update_door_coords(db: Session, door: models.Door, x: float, y: float) -> models.Door:
    door.x = clamp01(x)
    door.y = clamp01(y)
    db.commit()
    db.refresh(door)
    return door

def delete_door(db: Session, door: models.Door) -> None:
    db.delete(door)
    db.commit()


# =========================
# NFC USERS (globales)
# =========================

def get_nfc_user_by_uid(db: Session, uid: str) -> models.NfcUser | None:
    uid = normalize_uid(uid)
    return db.query(models.NfcUser).filter(models.NfcUser.uid_hex == uid).first()

def list_nfc_users(db: Session) -> list[models.NfcUser]:
    return db.query(models.NfcUser).order_by(models.NfcUser.id.asc()).all()

def create_nfc_user(
    db: Session,
    uid_hex: str,
    full_name: str,
    employee_number: str = "",
    is_active: bool = True,
) -> models.NfcUser:
    uid_hex = normalize_uid(uid_hex)
    existing = get_nfc_user_by_uid(db, uid_hex)
    if existing:
        return existing

    u = models.NfcUser(
        uid_hex=uid_hex,
        full_name=(full_name or "").strip(),
        employee_number=employee_number or "",
        is_active=bool(is_active),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def update_nfc_user(
    db: Session,
    u: models.NfcUser,
    full_name: str,
    employee_number: str,
    is_active: bool,
) -> models.NfcUser:
    u.full_name = (full_name or "").strip()
    u.employee_number = employee_number or ""
    u.is_active = bool(is_active)
    db.commit()
    db.refresh(u)
    return u

def delete_nfc_user(db: Session, u: models.NfcUser) -> None:
    db.delete(u)
    db.commit()


# =========================
# DOOR ACCESS (permisos por puerta)
# =========================

def is_nfc_allowed_for_door(db: Session, door_pk: int, nfc_pk: int) -> bool:
    row = db.query(models.DoorAccess).filter(
        and_(
            models.DoorAccess.door_id == door_pk,
            models.DoorAccess.nfc_user_id == nfc_pk,
            models.DoorAccess.is_allowed == True,
        )
    ).first()
    return row is not None

def allow_nfc_for_door(db: Session, door_pk: int, nfc_pk: int, allowed: bool = True) -> models.DoorAccess:
    row = db.query(models.DoorAccess).filter(
        and_(models.DoorAccess.door_id == door_pk, models.DoorAccess.nfc_user_id == nfc_pk)
    ).first()

    if row:
        row.is_allowed = bool(allowed)
    else:
        row = models.DoorAccess(door_id=door_pk, nfc_user_id=nfc_pk, is_allowed=bool(allowed))
        db.add(row)

    db.commit()
    db.refresh(row)
    return row

def list_door_access(db: Session) -> list[tuple[str, str, str, bool]]:
    """
    Devuelve filas listas para el dashboard:
    (door_id, uid_hex, full_name, is_allowed)
    """
    rows = (
        db.query(
            models.Door.door_id,
            models.NfcUser.uid_hex,
            models.NfcUser.full_name,
            models.DoorAccess.is_allowed,
        )
        .join(models.DoorAccess, models.DoorAccess.door_id == models.Door.id)
        .join(models.NfcUser, models.DoorAccess.nfc_user_id == models.NfcUser.id)
        .order_by(models.Door.door_id.asc(), models.NfcUser.full_name.asc())
        .all()
    )
    return rows


# =========================
# LOGS
# =========================

def log_event(
    db: Session,
    type: str,
    door: str = "",
    uid: str = "",
    name: str = "",
    result: str = "",
    details: str = "",
):
    ev = models.EventLog(
        type=(type or "")[:40],
        door=(door or "")[:32],
        uid=normalize_uid(uid)[:32],
        name=(name or "")[:120],
        result=(result or "")[:40],
        details=details or "",
    )
    db.add(ev)
    db.commit()

def list_events(db: Session, limit: int = 200) -> list[models.EventLog]:
    limit = max(1, min(int(limit), 1000))
    return db.query(models.EventLog).order_by(models.EventLog.ts.desc()).limit(limit).all()



def list_events_by_door(db: Session, door_id: str, limit: int = 50) -> list[models.EventLog]:
    limit = max(1, min(int(limit), 200))
    door_id = (door_id or "").strip()
    return (
        db.query(models.EventLog)
        .filter(models.EventLog.door == door_id)
        .order_by(models.EventLog.ts.desc())
        .limit(limit)
        .all()
    )

def get_last_event_by_door(db: Session, door_id: str) -> models.EventLog | None:
    door_id = (door_id or "").strip()
    return (
        db.query(models.EventLog)
        .filter(models.EventLog.door == door_id)
        .order_by(models.EventLog.ts.desc())
        .first()
    )

def compute_door_alert(door: models.Door, last: models.EventLog | None) -> tuple[str, datetime | None, str, str]:
    """
    alert: ok | warn | disabled | stale
    """
    if not door.is_enabled:
        return ("disabled", None, "", "door_disabled")

    if not last:
        # sin eventos: lo marcamos como "stale" (no hay telemetría)
        return ("stale", None, "", "no_events")

    # last.ts puede venir naive/aware. Normalizamos.
    ts = last.ts
    try:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        ts = None

    # si hace mucho no reporta
    if ts:
        if datetime.now(timezone.utc) - ts > timedelta(hours=12):
            return ("stale", ts, (last.result or ""), (last.details or ""))

    # regla simple de alerta: denied / no_permission / door_not_found / etc
    r = (last.result or "").lower()
    d = (last.details or "").lower()
    if "deny" in r or "denied" in r or "no_permission" in d or "inactive" in d:
        return ("warn", ts, (last.result or ""), (last.details or ""))

    return ("ok", ts, (last.result or ""), (last.details or ""))

