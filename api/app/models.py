from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db import Base


class StaffUser(Base):
    __tablename__ = "staff_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)  # admin/seguridad/sistemas/hsc...
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Door(Base):
    __tablename__ = "doors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    door_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # ✅ para mapeo / escalabilidad
    site: Mapped[str] = mapped_column(String(64), default="planta")  # puedes cambiar "planta" por "site1"
    x: Mapped[float] = mapped_column(Float, default=0.5)
    y: Mapped[float] = mapped_column(Float, default=0.5)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NfcUser(Base):
    __tablename__ = "nfc_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid_hex: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # UID HEX sin espacios
    full_name: Mapped[str] = mapped_column(String(120))
    employee_number: Mapped[str] = mapped_column(String(40), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DoorAccess(Base):
    __tablename__ = "door_access"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    door_id: Mapped[int] = mapped_column(ForeignKey("doors.id", ondelete="CASCADE"))
    nfc_user_id: Mapped[int] = mapped_column(ForeignKey("nfc_users.id", ondelete="CASCADE"))
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)

    door = relationship("Door")
    nfc_user = relationship("NfcUser")


class EventLog(Base):
    __tablename__ = "event_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    type: Mapped[str] = mapped_column(String(40), index=True)     # access/remote_unlock/enroll/denied/etc
    door: Mapped[str] = mapped_column(String(32), index=True)     # "D-001"
    uid: Mapped[str] = mapped_column(String(32), default="", index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    result: Mapped[str] = mapped_column(String(40), default="")   # ok/denied/etc
    details: Mapped[str] = mapped_column(Text, default="")
