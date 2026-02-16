from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from typing import Optional, Literal

# ---------------------------
# Auth
# ---------------------------
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MeOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    can_edit: bool = False  # ✅ agregado


class StaffUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    role: str = Field(min_length=3, max_length=32)
    is_active: bool = True


# ---------------------------
# Doors
# ---------------------------
class DoorIn(BaseModel):
    door_id: str = Field(min_length=3, max_length=32)
    name: str = ""
    location: str = ""
    is_enabled: bool = True

    # ✅ para mapeo (opcional al crear/actualizar)
    site: str = ""  # ejemplo: "planta"
    x: float = 0.0  # normalizado 0..1
    y: float = 0.0  # normalizado 0..1


class DoorOut(BaseModel):
    id: int
    door_id: str
    name: str
    location: str
    is_enabled: bool

    # ✅ para mapeo
    site: str = ""
    x: float = 0.0
    y: float = 0.0


class DoorCoordsIn(BaseModel):
    # ✅ coords normalizadas dentro del mapa (0..1)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


# ---------------------------
# NFC Users (globales)
# ---------------------------
class NfcUserIn(BaseModel):
    uid_hex: str = Field(min_length=4, max_length=32)
    full_name: str = Field(min_length=2, max_length=120)
    employee_number: str = ""
    is_active: bool = True


class NfcUserOut(NfcUserIn):
    id: int


# ---------------------------
# Door Access
# ---------------------------
class DoorAccessSetIn(BaseModel):
    door_id: str = Field(min_length=3, max_length=32)
    uid_hex: str = Field(min_length=4, max_length=32)
    is_allowed: bool = True


class DoorAccessRowOut(BaseModel):
    door_id: str
    uid_hex: str
    full_name: str
    is_allowed: bool


# ---- Doors Status (para mapa/alertas)
class DoorStatusOut(DoorOut):
    alert: str = "ok"        # ok | warn | disabled | stale
    last_ts: Optional[datetime] = None
    last_result: str = ""
    last_details: str = ""



# ---------------------------
# ESP32 Access Check
# ---------------------------
class AccessCheckIn(BaseModel):
    door_id: str = Field(min_length=3, max_length=32)
    uid: str = Field(min_length=4, max_length=64)


class AccessCheckOut(BaseModel):
    allowed: bool
    reason: str
    door_id: str
    uid: str
    user_name: Optional[str] = None


# ---------------------------
# Logs
# ---------------------------
class EventOut(BaseModel):
    id: int
    ts: datetime
    type: str
    door: str
    uid: str
    name: str
    result: str
    details: str




class DoorStatusOut(BaseModel):
    id: int
    door_id: str
    name: str
    location: str
    is_enabled: bool
    x: float
    y: float

    alert: Literal["ok","warn","disabled","stale"]
    last_ts: Optional[datetime] = None
    last_result: str = ""
    last_details: str = ""
