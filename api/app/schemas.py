from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_active: bool
    can_edit: bool = False


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
    site: str = ""
    x: float = 0.0
    y: float = 0.0


class DoorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    door_id: str
    name: str
    location: str
    is_enabled: bool
    site: str = ""
    x: float = 0.0
    y: float = 0.0


class DoorCoordsIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


# ---------------------------
# NFC Users
# ---------------------------
class NfcUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    employee_number: str = ""
    is_active: bool = True

    # opcional solo por compatibilidad/legado
    uid_hex: Optional[str] = Field(default=None, min_length=4, max_length=32)


class NfcUserUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    employee_number: str = ""
    is_active: bool = True


class NfcUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uid_hex: Optional[str] = None
    full_name: str
    employee_number: str = ""
    is_active: bool


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


# ---------------------------
# Door Status
# ---------------------------
class DoorStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    door_id: str
    name: str
    location: str
    is_enabled: bool
    x: float
    y: float
    alert: Literal["ok", "warn", "disabled", "stale"]
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    type: str
    door: str
    uid: str
    name: str
    result: str
    details: str


# ---------------------------
# Device Keys
# ---------------------------
class DeviceKeyCreate(BaseModel):
    door_id: str = Field(min_length=3, max_length=32)
    raw_key: str = Field(min_length=16, max_length=128)
    description: str = ""


class DeviceKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    door_id: str
    description: str
    is_active: bool
    last_seen: Optional[datetime] = None


# ---------------------------
# NFC Credentials
# ---------------------------
class NfcCredentialCreate(BaseModel):
    nfc_user_id: int
    uid_hex: str
    tag_type: str = "tag"
    is_active: bool = True


class NfcCredentialUpdate(BaseModel):
    tag_type: str = "tag"
    is_active: bool = True


class NfcCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nfc_user_id: int
    uid_hex: str
    tag_type: str
    is_active: bool
    created_at: datetime


# ---------------------------
# Enrollment Sessions
# ---------------------------
class EnrollmentStartIn(BaseModel):
    station_name: str = "main"
    tag_type: str = "tag"


class EnrollmentReportIn(BaseModel):
    session_id: int
    uid_hex: str


class EnrollmentSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_name: str
    requested_by_id: Optional[int] = None
    status: str
    tag_type: str
    uid_hex: str
    error_message: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


# ---------------------------
# Enrollment Station Keys
# ---------------------------
class EnrollmentStationKeyCreate(BaseModel):
    station_name: str
    raw_key: str
    description: str = ""


class EnrollmentStationKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_name: str
    description: str
    is_active: bool
    created_at: datetime