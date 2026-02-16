from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app import crud, schemas, models
from app.security import create_access_token
from app.deps import get_current_user, require_roles, require_edit_access
from app.config import get_edit_roles

app = FastAPI(title="SigControl Central API")

# ---------- UI (Templates + Static) ----------
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


# (Solo admin) crear usuarios staff
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


@app.post("/api/doors", response_model=schemas.DoorOut)
def doors_create(
    payload: schemas.DoorIn,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    if crud.get_door_by_code(db, payload.door_id):
        raise HTTPException(status_code=409, detail="door_id already exists")
    return crud.create_door(db, payload.door_id, payload.name, payload.location, payload.is_enabled)


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
    return crud.update_door(db, door, payload.name, payload.location, payload.is_enabled)


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


# Guardar coordenadas en mapa (escala 0..1)
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


# ✅ Status/alertas para mapa 3D
@app.get("/api/doors/status", response_model=list[schemas.DoorStatusOut])
def doors_status(
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    doors = crud.list_doors(db)
    out: list[schemas.DoorStatusOut] = []

    for d in doors:
        last = crud.get_last_event_by_door(db, d.door_id)
        alert, last_ts, last_result, last_details = crud.compute_door_alert(d, last)

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


# ---------- NFC Users (globales) ----------
@app.get("/api/nfc-users", response_model=list[schemas.NfcUserOut])
def nfc_users_list(
    db: Session = Depends(get_db),
    _u: models.StaffUser = Depends(require_roles("admin", "seguridad", "sistemas", "hsc")),
):
    return crud.list_nfc_users(db)


@app.post("/api/nfc-users", response_model=schemas.NfcUserOut)
def nfc_users_create(
    payload: schemas.NfcUserIn,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    if crud.get_nfc_user_by_uid(db, payload.uid_hex):
        raise HTTPException(status_code=409, detail="uid already exists")
    u = crud.create_nfc_user(db, payload.uid_hex, payload.full_name, payload.employee_number, payload.is_active)
    return schemas.NfcUserOut(
        id=u.id,
        uid_hex=u.uid_hex,
        full_name=u.full_name,
        employee_number=u.employee_number,
        is_active=u.is_active,
    )


@app.put("/api/nfc-users/{uid_hex}", response_model=schemas.NfcUserOut)
def nfc_users_update(
    uid_hex: str,
    payload: schemas.NfcUserIn,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    u = crud.get_nfc_user_by_uid(db, uid_hex)
    if not u:
        raise HTTPException(status_code=404, detail="NFC user not found")
    u = crud.update_nfc_user(db, u, payload.full_name, payload.employee_number, payload.is_active)
    return schemas.NfcUserOut(
        id=u.id,
        uid_hex=u.uid_hex,
        full_name=u.full_name,
        employee_number=u.employee_number,
        is_active=u.is_active,
    )


@app.delete("/api/nfc-users/{uid_hex}")
def nfc_users_delete(
    uid_hex: str,
    db: Session = Depends(get_db),
    _admin: models.StaffUser = Depends(require_roles("admin")),
):
    u = crud.get_nfc_user_by_uid(db, uid_hex)
    if not u:
        raise HTTPException(status_code=404, detail="NFC user not found")
    crud.delete_nfc_user(db, u)
    return {"ok": True}


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



# ---------- ESP32 endpoint: access check ----------
@app.post("/api/access/check", response_model=schemas.AccessCheckOut)
def access_check(payload: schemas.AccessCheckIn, db: Session = Depends(get_db)):
    uid = crud.normalize_uid(payload.uid)
    door_code = payload.door_id.strip()

    door = crud.get_door_by_code(db, door_code)
    if not door:
        crud.log_event(db, "access", door_code, uid, "", "denied", "door_not_found")
        return schemas.AccessCheckOut(allowed=False, reason="door_not_found", door_id=door_code, uid=uid, user_name=None)

    if not door.is_enabled:
        crud.log_event(db, "access", door_code, uid, "", "denied", "door_disabled")
        return schemas.AccessCheckOut(allowed=False, reason="door_disabled", door_id=door_code, uid=uid, user_name=None)

    user = crud.get_nfc_user_by_uid(db, uid)
    if not user:
        crud.log_event(db, "access", door_code, uid, "", "denied", "uid_not_registered")
        return schemas.AccessCheckOut(allowed=False, reason="uid_not_registered", door_id=door_code, uid=uid, user_name=None)

    if not user.is_active:
        crud.log_event(db, "access", door_code, uid, user.full_name, "denied", "user_inactive")
        return schemas.AccessCheckOut(allowed=False, reason="user_inactive", door_id=door_code, uid=uid, user_name=user.full_name)

    allowed = crud.is_nfc_allowed_for_door(db, door.id, user.id)
    if allowed:
        crud.log_event(db, "access", door_code, uid, user.full_name, "granted", "ok")
        return schemas.AccessCheckOut(allowed=True, reason="granted", door_id=door_code, uid=uid, user_name=user.full_name)

    crud.log_event(db, "access", door_code, uid, user.full_name, "denied", "no_permission")
    return schemas.AccessCheckOut(allowed=False, reason="no_permission", door_id=door_code, uid=uid, user_name=user.full_name)


# ---------- Logs ----------
# ✅ permite filtrar por puerta con ?door_id=D-001
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
