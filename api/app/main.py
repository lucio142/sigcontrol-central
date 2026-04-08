from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db import init_db, get_db
from app import crud, schemas, models
from app.security import create_access_token
from app.deps import get_current_user, require_roles, require_edit_access, require_device
from app.config import get_edit_roles

app = FastAPI(
    title="SigControl Central API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def require_enrollment_station(
    station_name: str,
    x_station_key: str | None,
    db: Session,
):
    if not x_station_key:
        raise HTTPException(status_code=401, detail="Missing X-Station-Key")

    ok = crud.verify_enrollment_station_key(db, station_name, x_station_key)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid station credentials")


def nfc_user_to_out(db: Session, u: models.NfcUser) -> schemas.NfcUserOut:
    return schemas.NfcUserOut(
        id=u.id,
        uid_hex=crud.get_display_uid_for_user(db, u),
        full_name=u.full_name,
        employee_number=u.employee_number,
        is_active=u.is_active,
    )


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- UI ----------
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/login", response_class=HTMLResponse)
def ui_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def ui_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
def ui_root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def ui_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/map", response_class=HTMLResponse)
def ui_map(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})


# ---------- Auth ----------
@app.post("/api/auth/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = crud.authenticate_staff_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Bad credentials")
    token = create_access_token(subject=user.email, role=user.role)
    return schemas.TokenOut(access_token=token)


@app.get("/api/auth/me", response_model=schemas.MeOut)
def me(u: models.StaffUser = Depends(get_current_user)):
    can_edit = u.role in get_edit_roles()
    return schemas.MeOut(
        id=u.id,
        email=u.email,
        role=u.role,
        is_active=u.is_active,
        can_edit=can_edit,
    )


# ---------- Staff ----------
@app.post("/api/staff", response_model=schemas.MeOut)
def staff_create(
    payload: schemas.StaffUserCreate,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    exists = crud.get_staff_user_by_email(db, payload.email)
    if exists:
        raise HTTPException(status_code=409, detail="Email already exists")
    u = crud.create_staff_user(db, payload.email, payload.password, payload.role, payload.is_active)
    return schemas.MeOut(
        id=u.id,
        email=u.email,
        role=u.role,
        is_active=u.is_active,
        can_edit=(u.role in get_edit_roles()),
    )


# ---------- Doors ----------
@app.get("/api/doors", response_model=list[schemas.DoorOut])
def doors_list(
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    return crud.list_doors(db)


@app.get("/api/doors/status", response_model=list[schemas.DoorStatusOut])
def doors_status(
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    doors = crud.list_doors(db)
    out: list[schemas.DoorStatusOut] = []

    for d in doors:
        last = crud.get_last_event_by_door(db, d.door_id)
        dk = crud.get_device_key_any_status(db, d.door_id)
        device_last_seen = dk.last_seen if dk else None

        alert, last_ts, last_result, last_details = crud.compute_door_alert(
            d,
            last,
            device_last_seen=device_last_seen,
        )

        out.append(
            schemas.DoorStatusOut(
                id=d.id,
                door_id=d.door_id,
                name=d.name or "",
                location=d.location or "",
                is_enabled=bool(d.is_enabled),
                x=float(getattr(d, "x", 0.5) or 0.5),
                y=float(getattr(d, "y", 0.5) or 0.5),
                alert=alert,
                last_ts=last_ts,
                last_result=last_result or "",
                last_details=last_details or "",
            )
        )

    return out


@app.post("/api/doors", response_model=schemas.DoorOut)
def doors_create(
    payload: schemas.DoorIn,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    if crud.get_door_by_code(db, payload.door_id):
        raise HTTPException(status_code=409, detail="door_id already exists")

    return crud.create_door(
        db,
        payload.door_id,
        payload.name,
        payload.location,
        payload.is_enabled,
        payload.site,
        payload.x,
        payload.y,
    )


@app.put("/api/doors/{door_id}", response_model=schemas.DoorOut)
def doors_update(
    door_id: str,
    payload: schemas.DoorIn,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    door = crud.get_door_by_code(db, door_id)
    if not door:
        raise HTTPException(status_code=404, detail="Door not found")

    return crud.update_door(
        db,
        door,
        payload.name,
        payload.location,
        payload.is_enabled,
        payload.site,
        payload.x,
        payload.y,
    )


@app.delete("/api/doors/{door_id}")
def doors_delete(
    door_id: str,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    door = crud.get_door_by_code(db, door_id)
    if not door:
        raise HTTPException(status_code=404, detail="Door not found")
    crud.delete_door(db, door)
    return {"ok": True}


@app.post("/api/doors/{door_id}/coords", response_model=schemas.DoorOut)
def door_update_coords(
    door_id: str,
    payload: schemas.DoorCoordsIn,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_edit_access()),
):
    door = crud.get_door_by_code(db, door_id)
    if not door:
        raise HTTPException(status_code=404, detail="Door not found")
    return crud.update_door_coords(db, door, payload.x, payload.y)


# ---------- NFC Users ----------
@app.get("/api/nfc-users", response_model=list[schemas.NfcUserOut])
def nfc_users_list(
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    users = crud.list_nfc_users(db)
    return [nfc_user_to_out(db, u) for u in users]


@app.post("/api/nfc-users", response_model=schemas.NfcUserOut)
def nfc_users_create(
    payload: schemas.NfcUserCreate,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    if payload.uid_hex:
        if crud.get_nfc_user_by_uid(db, payload.uid_hex):
            raise HTTPException(status_code=409, detail="uid already exists")

    u = crud.create_nfc_user(
        db,
        full_name=payload.full_name,
        employee_number=payload.employee_number,
        is_active=payload.is_active,
        uid_hex=payload.uid_hex,
    )
    return nfc_user_to_out(db, u)


@app.put("/api/nfc-users/{user_id}", response_model=schemas.NfcUserOut)
def nfc_users_update(
    user_id: int,
    payload: schemas.NfcUserUpdate,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    u = crud.get_nfc_user_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="NFC user not found")

    u = crud.update_nfc_user(db, u, payload.full_name, payload.employee_number, payload.is_active)
    return nfc_user_to_out(db, u)


@app.delete("/api/nfc-users/{user_id}")
def nfc_users_delete(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    u = crud.get_nfc_user_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="NFC user not found")
    crud.delete_nfc_user(db, u)
    return {"ok": True}


# ---------- NFC Credentials ----------
@app.get("/api/nfc-credentials/by-user/{nfc_user_id}", response_model=list[schemas.NfcCredentialOut])
def nfc_credentials_by_user(
    nfc_user_id: int,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    user = db.query(models.NfcUser).filter(models.NfcUser.id == nfc_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="NFC user not found")

    return crud.list_nfc_credentials_by_user(db, nfc_user_id)


@app.post("/api/nfc-credentials", response_model=schemas.NfcCredentialOut)
def nfc_credential_create(
    payload: schemas.NfcCredentialCreate,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas")),
):
    user = db.query(models.NfcUser).filter(models.NfcUser.id == payload.nfc_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="NFC user not found")

    uid = crud.normalize_uid(payload.uid_hex)

    existing_cred = crud.get_nfc_credential_by_uid(db, uid)
    if existing_cred:
        raise HTTPException(status_code=409, detail="UID already exists in credentials")

    existing_user = db.query(models.NfcUser).filter(models.NfcUser.uid_hex == uid).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="UID already exists in legacy nfc_users")

    cred = crud.create_nfc_credential(
        db,
        nfc_user_id=payload.nfc_user_id,
        uid_hex=uid,
        tag_type=payload.tag_type,
        is_active=payload.is_active,
    )

    crud.log_event(
        db,
        type="enroll",
        door="",
        uid=cred.uid_hex,
        name=user.full_name,
        result="ok",
        details=f"credential_created:{cred.tag_type}",
    )

    return cred


@app.put("/api/nfc-credentials/{credential_id}", response_model=schemas.NfcCredentialOut)
def nfc_credential_update(
    credential_id: int,
    payload: schemas.NfcCredentialUpdate,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas")),
):
    cred = db.query(models.NfcCredential).filter(models.NfcCredential.id == credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    cred = crud.update_nfc_credential(
        db,
        cred,
        tag_type=payload.tag_type,
        is_active=payload.is_active,
    )

    return cred


@app.delete("/api/nfc-credentials/{credential_id}")
def nfc_credential_delete(
    credential_id: int,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas")),
):
    cred = db.query(models.NfcCredential).filter(models.NfcCredential.id == credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    crud.delete_nfc_credential(db, cred)
    return {"ok": True}


# ---------- Enrollment Station Keys ----------
@app.post("/api/enrollment-station-keys", response_model=schemas.EnrollmentStationKeyOut)
def enrollment_station_key_create(
    payload: schemas.EnrollmentStationKeyCreate,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "sistemas")),
):
    obj = crud.create_enrollment_station_key(
        db,
        station_name=payload.station_name,
        raw_key=payload.raw_key,
        description=payload.description,
    )
    return obj


# ---------- Enrollment ----------
@app.post("/api/enrollment/start", response_model=schemas.EnrollmentSessionOut)
def enrollment_start(
    payload: schemas.EnrollmentStartIn,
    db: Session = Depends(get_db),
    u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas")),
):
    session_obj = crud.create_enrollment_session(
        db,
        station_name=payload.station_name,
        requested_by_id=u.id,
        tag_type=payload.tag_type,
    )

    crud.log_event(
        db,
        type="enroll_start",
        door="",
        uid="",
        name=u.email,
        result="pending",
        details=f"station={session_obj.station_name};tag_type={session_obj.tag_type};session_id={session_obj.id}",
    )

    return session_obj


@app.get("/api/enrollment/pending", response_model=schemas.EnrollmentSessionOut | None)
def enrollment_pending(
    station_name: str = "main",
    x_station_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_enrollment_station(station_name, x_station_key, db)
    return crud.get_pending_enrollment_session(db, station_name=station_name)


@app.post("/api/enrollment/report", response_model=schemas.EnrollmentSessionOut)
def enrollment_report(
    payload: schemas.EnrollmentReportIn,
    station_name: str,
    x_station_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_enrollment_station(station_name, x_station_key, db)

    session_obj = crud.get_enrollment_session(db, payload.session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Enrollment session not found")

    if session_obj.station_name != station_name:
        raise HTTPException(status_code=403, detail="Station mismatch")

    if session_obj.status != "pending":
        raise HTTPException(status_code=409, detail="Enrollment session is not pending")

    uid = crud.normalize_uid(payload.uid_hex)

    existing_cred = crud.get_nfc_credential_by_uid(db, uid)
    if existing_cred:
        raise HTTPException(status_code=409, detail="UID already exists in credentials")

    existing_user = db.query(models.NfcUser).filter(models.NfcUser.uid_hex == uid).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="UID already exists in legacy nfc_users")

    session_obj = crud.report_enrollment_uid(db, session_obj, uid)

    crud.log_event(
        db,
        type="enroll_read",
        door="",
        uid=session_obj.uid_hex,
        name="",
        result="ok",
        details=f"station={session_obj.station_name};tag_type={session_obj.tag_type};session_id={session_obj.id}",
    )

    return session_obj


@app.get("/api/enrollment/{session_id}", response_model=schemas.EnrollmentSessionOut)
def enrollment_get(
    session_id: int,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    session_obj = crud.get_enrollment_session(db, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Enrollment session not found")
    return session_obj


@app.post("/api/enrollment/{session_id}/consume", response_model=schemas.EnrollmentSessionOut)
def enrollment_consume(
    session_id: int,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas")),
):
    session_obj = crud.get_enrollment_session(db, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Enrollment session not found")

    session_obj = crud.consume_enrollment_session(db, session_obj)
    return session_obj


# ---------- Door Access Matrix ----------
@app.get("/api/door-access", response_model=list[schemas.DoorAccessRowOut])
def door_access_list(
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "hsc", "sistemas")),
):
    rows = crud.list_door_access(db)
    return [
        schemas.DoorAccessRowOut(door_id=d, uid_hex=uid, full_name=name, is_allowed=allowed)
        for (d, uid, name, allowed) in rows
    ]


@app.post("/api/door-access/set")
def door_access_set(
    payload: schemas.DoorAccessSetIn,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_edit_access()),
):
    door = crud.get_door_by_code(db, payload.door_id)
    if not door:
        raise HTTPException(status_code=404, detail="Door not found")

    user = crud.get_nfc_user_by_uid(db, payload.uid_hex)
    if not user:
        raise HTTPException(status_code=404, detail="NFC user not found")

    crud.allow_nfc_for_door(db, door.id, user.id, payload.is_allowed)
    return {"ok": True, "is_allowed": bool(payload.is_allowed)}


@app.post("/api/door-access/toggle")
def door_access_toggle(
    payload: schemas.DoorAccessSetIn,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_edit_access()),
):
    door = crud.get_door_by_code(db, payload.door_id)
    if not door:
        raise HTTPException(status_code=404, detail="Door not found")

    user = crud.get_nfc_user_by_uid(db, payload.uid_hex)
    if not user:
        raise HTTPException(status_code=404, detail="NFC user not found")

    current = crud.is_nfc_allowed_for_door(db, door.id, user.id)
    crud.allow_nfc_for_door(db, door.id, user.id, not current)
    return {"ok": True, "is_allowed": (not current)}


# ---------- ESP32: heartbeat ----------
@app.post("/api/devices/heartbeat")
def device_heartbeat(
    door: models.Door = Depends(require_device),
    db: Session = Depends(get_db),
):
    crud.touch_device_last_seen(db, door.door_id)
    return {"ok": True, "door_id": door.door_id}


# ---------- ESP32: access check ----------
@app.post("/api/access/check", response_model=schemas.AccessCheckOut)
def access_check(
    payload: schemas.AccessCheckIn,
    door: models.Door = Depends(require_device),
    db: Session = Depends(get_db),
):
    uid = crud.normalize_uid(payload.uid)
    door_code = payload.door_id.strip()

    if door_code != door.door_id:
        raise HTTPException(status_code=403, detail="Door mismatch")

    if not door.is_enabled:
        crud.log_event(db, "access", door_code, uid, "", "denied", "door_disabled")
        return schemas.AccessCheckOut(
            allowed=False,
            reason="door_disabled",
            door_id=door_code,
            uid=uid,
            user_name=None,
        )

    user = crud.get_nfc_user_by_uid(db, uid)
    if not user:
        crud.log_event(db, "access", door_code, uid, "", "denied", "uid_not_registered")
        return schemas.AccessCheckOut(
            allowed=False,
            reason="uid_not_registered",
            door_id=door_code,
            uid=uid,
            user_name=None,
        )

    if not user.is_active:
        crud.log_event(db, "access", door_code, uid, user.full_name, "denied", "user_inactive")
        return schemas.AccessCheckOut(
            allowed=False,
            reason="user_inactive",
            door_id=door_code,
            uid=uid,
            user_name=user.full_name,
        )

    allowed = crud.is_nfc_allowed_for_door(db, door.id, user.id)
    if allowed:
        crud.log_event(db, "access", door_code, uid, user.full_name, "granted", "ok")
        return schemas.AccessCheckOut(
            allowed=True,
            reason="granted",
            door_id=door_code,
            uid=uid,
            user_name=user.full_name,
        )

    crud.log_event(db, "access", door_code, uid, user.full_name, "denied", "no_permission")
    return schemas.AccessCheckOut(
        allowed=False,
        reason="no_permission",
        door_id=door_code,
        uid=uid,
        user_name=user.full_name,
    )


# ---------- Logs ----------
@app.get("/api/events", response_model=list[schemas.EventOut])
def events_list(
    limit: int = 200,
    door_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    if door_id:
        return crud.list_events_by_door(db, door_id=door_id, limit=limit)
    return crud.list_events(db, limit=limit)


# ---------- Device Keys ----------
@app.get("/api/device-keys", response_model=list[schemas.DeviceKeyOut])
def device_keys_list(
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin", "sistemas")),
):
    return crud.list_device_keys(db)


@app.post("/api/device-keys")
def device_keys_create(
    payload: schemas.DeviceKeyCreate,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin", "sistemas")),
):
    door = crud.get_door_by_code(db, payload.door_id)
    if not door:
        raise HTTPException(status_code=404, detail="Door not found")

    crud.create_device_key(
        db,
        payload.door_id,
        payload.raw_key,
        payload.description,
    )

    return {"ok": True}


@app.delete("/api/device-keys/{door_id}")
def device_keys_delete(
    door_id: str,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin", "sistemas")),
):
    ok = crud.delete_device_key(db, door_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device key not found")

    return {"ok": True}


@app.post("/api/device-keys/{door_id}/toggle")
def device_keys_toggle(
    door_id: str,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin", "sistemas")),
):
    dk = crud.toggle_device_key(db, door_id)
    if not dk:
        raise HTTPException(status_code=404, detail="Device key not found")

    return {"ok": True, "is_active": dk.is_active}