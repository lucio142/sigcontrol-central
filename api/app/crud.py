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


def get_display_uid_for_user(db: Session, user: models.NfcUser) -> str | None:
    if user.uid_hex:
        return normalize_uid(user.uid_hex)

    cred = (
        db.query(models.NfcCredential)
        .filter(
            models.NfcCredential.nfc_user_id == user.id,
            models.NfcCredential.is_active == True,
        )
        .order_by(models.NfcCredential.id.asc())
        .first()
    )

    if cred:
        return cred.uid_hex

    return None


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
        password_hash=hash_password(password),
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
# NFC USERS
# =========================

def get_nfc_user_by_id(db: Session, user_id: int) -> models.NfcUser | None:
    return db.query(models.NfcUser).filter(models.NfcUser.id == user_id).first()


def get_nfc_user_by_uid(db: Session, uid: str) -> models.NfcUser | None:
    uid = normalize_uid(uid)
    if not uid:
        return None

    # 1) legado: uid directo en nfc_users
    user = db.query(models.NfcUser).filter(models.NfcUser.uid_hex == uid).first()
    if user:
        return user

    # 2) nuevo modelo: uid vive en nfc_credentials
    cred = db.query(models.NfcCredential).filter(
        models.NfcCredential.uid_hex == uid,
        models.NfcCredential.is_active == True,
    ).first()

    if cred:
        return cred.nfc_user

    return None


def list_nfc_users(db: Session) -> list[models.NfcUser]:
    return db.query(models.NfcUser).order_by(models.NfcUser.id.asc()).all()


def create_nfc_user(
    db: Session,
    full_name: str,
    employee_number: str = "",
    is_active: bool = True,
    uid_hex: str | None = None,
) -> models.NfcUser:
    uid_norm = normalize_uid(uid_hex) if uid_hex else None

    if uid_norm:
        existing = get_nfc_user_by_uid(db, uid_norm)
        if existing:
            return existing

    u = models.NfcUser(
        uid_hex=uid_norm or None,
        full_name=(full_name or "").strip(),
        employee_number=(employee_number or "").strip(),
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
    u.employee_number = (employee_number or "").strip()
    u.is_active = bool(is_active)
    db.commit()
    db.refresh(u)
    return u


def delete_nfc_user(db: Session, u: models.NfcUser) -> None:
    db.delete(u)
    db.commit()


# =========================
# NFC CREDENTIALS
# =========================

def get_nfc_credential_by_uid(db: Session, uid: str) -> models.NfcCredential | None:
    uid = normalize_uid(uid)
    return db.query(models.NfcCredential).filter(
        models.NfcCredential.uid_hex == uid
    ).first()


def list_nfc_credentials_by_user(db: Session, nfc_user_id: int) -> list[models.NfcCredential]:
    return db.query(models.NfcCredential).filter(
        models.NfcCredential.nfc_user_id == nfc_user_id
    ).order_by(models.NfcCredential.id.asc()).all()


def create_nfc_credential(
    db: Session,
    nfc_user_id: int,
    uid_hex: str,
    tag_type: str = "tag",
    is_active: bool = True,
) -> models.NfcCredential:
    uid_hex = normalize_uid(uid_hex)

    existing = get_nfc_credential_by_uid(db, uid_hex)
    if existing:
        return existing

    cred = models.NfcCredential(
        nfc_user_id=nfc_user_id,
        uid_hex=uid_hex,
        tag_type=(tag_type or "tag").strip(),
        is_active=bool(is_active),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


def update_nfc_credential(
    db: Session,
    credential: models.NfcCredential,
    tag_type: str,
    is_active: bool,
) -> models.NfcCredential:
    credential.tag_type = (tag_type or "tag").strip()
    credential.is_active = bool(is_active)
    db.commit()
    db.refresh(credential)
    return credential


def delete_nfc_credential(db: Session, credential: models.NfcCredential) -> None:
    db.delete(credential)
    db.commit()


# =========================
# DOOR ACCESS
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
    rows = (
        db.query(
            models.Door.door_id,
            models.NfcUser.id,
            models.NfcUser.full_name,
            models.DoorAccess.is_allowed,
        )
        .join(models.DoorAccess, models.DoorAccess.door_id == models.Door.id)
        .join(models.NfcUser, models.DoorAccess.nfc_user_id == models.NfcUser.id)
        .order_by(models.Door.door_id.asc(), models.NfcUser.full_name.asc())
        .all()
    )

    out: list[tuple[str, str, str, bool]] = []
    for door_code, user_id, full_name, is_allowed in rows:
        user = get_nfc_user_by_id(db, user_id)
        display_uid = get_display_uid_for_user(db, user) if user else None
        out.append((door_code, display_uid or "", full_name, is_allowed))

    return out


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


# =========================
# DEVICE KEYS
# =========================

def create_device_key(
    db: Session,
    door_id: str,
    raw_key: str,
    description: str = "",
) -> models.DeviceKey:
    existing = db.query(models.DeviceKey).filter(
        models.DeviceKey.door_id == door_id
    ).first()

    if existing:
        existing.key_hash = hash_password(raw_key)
        existing.description = description
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    dk = models.DeviceKey(
        door_id=door_id,
        key_hash=hash_password(raw_key),
        description=description,
        is_active=True,
    )
    db.add(dk)
    db.commit()
    db.refresh(dk)
    return dk


def get_device_key_by_door(db: Session, door_id: str) -> models.DeviceKey | None:
    return db.query(models.DeviceKey).filter(
        models.DeviceKey.door_id == door_id,
        models.DeviceKey.is_active == True,
    ).first()


def get_device_key_any_status(db: Session, door_id: str) -> models.DeviceKey | None:
    return db.query(models.DeviceKey).filter(
        models.DeviceKey.door_id == door_id
    ).first()


def touch_device_last_seen(db: Session, door_id: str) -> models.DeviceKey | None:
    dk = get_device_key_any_status(db, door_id)
    if not dk:
        return None
    dk.last_seen = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dk)
    return dk


def verify_device_key(db: Session, door_id: str, raw_key: str) -> bool:
    dk = get_device_key_by_door(db, door_id)
    if not dk:
        return False

    ok = verify_password(raw_key, dk.key_hash)
    if ok:
        dk.last_seen = datetime.now(timezone.utc)
        db.commit()

    return ok


def list_device_keys(db: Session) -> list[models.DeviceKey]:
    return db.query(models.DeviceKey).order_by(models.DeviceKey.id.asc()).all()


def delete_device_key(db: Session, door_id: str) -> bool:
    dk = db.query(models.DeviceKey).filter(
        models.DeviceKey.door_id == door_id
    ).first()
    if not dk:
        return False
    db.delete(dk)
    db.commit()
    return True


def toggle_device_key(db: Session, door_id: str) -> models.DeviceKey | None:
    dk = db.query(models.DeviceKey).filter(
        models.DeviceKey.door_id == door_id
    ).first()
    if not dk:
        return None
    dk.is_active = not dk.is_active
    db.commit()
    db.refresh(dk)
    return dk


# =========================
# ALERTAS / STATUS DE PUERTA
# =========================

def compute_door_alert(
    door: models.Door,
    last: models.EventLog | None,
    device_last_seen: datetime | None = None,
) -> tuple[str, datetime | None, str, str]:
    if not door.is_enabled:
        return ("disabled", device_last_seen or (last.ts if last else None), "", "door_disabled")

    ts_event = last.ts if last else None

    try:
        if ts_event and ts_event.tzinfo is None:
            ts_event = ts_event.replace(tzinfo=timezone.utc)
    except Exception:
        ts_event = None

    try:
        if device_last_seen and device_last_seen.tzinfo is None:
            device_last_seen = device_last_seen.replace(tzinfo=timezone.utc)
    except Exception:
        device_last_seen = None

    now = datetime.now(timezone.utc)

    if not device_last_seen:
        return ("stale", ts_event, (last.result if last else ""), "device_offline")

    if now - device_last_seen > timedelta(minutes=5):
        return ("stale", ts_event, (last.result if last else ""), "device_timeout")

    if last:
        r = (last.result or "").lower()
        d = (last.details or "").lower()
        if "deny" in r or "denied" in r or "no_permission" in d or "inactive" in d:
            return ("warn", ts_event, (last.result or ""), (last.details or ""))

    return ("ok", ts_event, (last.result if last else ""), (last.details if last else "online"))


# =========================
# ENROLLMENT STATION KEYS
# =========================

def create_enrollment_station_key(
    db: Session,
    station_name: str,
    raw_key: str,
    description: str = "",
) -> models.EnrollmentStationKey:
    station_name = (station_name or "").strip()

    existing = db.query(models.EnrollmentStationKey).filter(
        models.EnrollmentStationKey.station_name == station_name
    ).first()

    if existing:
        existing.key_hash = hash_password(raw_key)
        existing.description = description or ""
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    obj = models.EnrollmentStationKey(
        station_name=station_name,
        key_hash=hash_password(raw_key),
        description=description or "",
        is_active=True,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def list_enrollment_station_keys(db: Session) -> list[models.EnrollmentStationKey]:
    return (
        db.query(models.EnrollmentStationKey)
        .order_by(models.EnrollmentStationKey.station_name.asc())
        .all()
    )

def get_enrollment_station_key(
    db: Session,
    station_name: str,
) -> models.EnrollmentStationKey | None:
    station_name = (station_name or "").strip()
    return db.query(models.EnrollmentStationKey).filter(
        models.EnrollmentStationKey.station_name == station_name,
        models.EnrollmentStationKey.is_active == True,
    ).first()


def verify_enrollment_station_key(
    db: Session,
    station_name: str,
    raw_key: str,
) -> bool:
    obj = get_enrollment_station_key(db, station_name)
    if not obj:
        return False
    return verify_password(raw_key, obj.key_hash)


# =========================
# ENROLLMENT SESSIONS
# =========================

def create_enrollment_session(
    db: Session,
    station_name: str,
    requested_by_id: int | None,
    tag_type: str = "tag",
) -> models.EnrollmentSession:
    now = datetime.now(timezone.utc)

    session = models.EnrollmentSession(
        station_name=(station_name or "main").strip() or "main",
        requested_by_id=requested_by_id,
        status="pending",
        tag_type=(tag_type or "tag").strip() or "tag",
        uid_hex="",
        error_message="",
        expires_at=now + timedelta(seconds=60),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_enrollment_session(db: Session, session_id: int) -> models.EnrollmentSession | None:
    return db.query(models.EnrollmentSession).filter(
        models.EnrollmentSession.id == session_id
    ).first()


def get_pending_enrollment_session(
    db: Session,
    station_name: str = "main",
) -> models.EnrollmentSession | None:
    now = datetime.now(timezone.utc)

    rows = db.query(models.EnrollmentSession).filter(
        models.EnrollmentSession.station_name == ((station_name or "main").strip() or "main"),
        models.EnrollmentSession.status == "pending",
    ).order_by(models.EnrollmentSession.id.asc()).all()

    for row in rows:
        exp = row.expires_at
        try:
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
        except Exception:
            exp = None

        if exp and exp < now:
            row.status = "expired"
            row.error_message = "session_expired"
            db.commit()
            db.refresh(row)
            continue

        return row

    return None


def report_enrollment_uid(
    db: Session,
    session_obj: models.EnrollmentSession,
    uid_hex: str,
) -> models.EnrollmentSession:
    session_obj.uid_hex = normalize_uid(uid_hex)
    session_obj.status = "read"
    session_obj.read_at = datetime.now(timezone.utc)
    session_obj.error_message = ""
    db.commit()
    db.refresh(session_obj)
    return session_obj


def consume_enrollment_session(
    db: Session,
    session_obj: models.EnrollmentSession,
) -> models.EnrollmentSession:
    session_obj.status = "consumed"
    db.commit()
    db.refresh(session_obj)
    return session_obj


def cancel_enrollment_session(
    db: Session,
    session_obj: models.EnrollmentSession,
    error_message: str = "",
) -> models.EnrollmentSession:
    session_obj.status = "cancelled"
    session_obj.error_message = (error_message or "")[:255]
    db.commit()
    db.refresh(session_obj)
    return session_obj