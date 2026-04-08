from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db import Base
from datetime import datetime


class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Door(Base):
    __tablename__ = "doors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    door_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    site: Mapped[str] = mapped_column(String(64), default="planta")
    x: Mapped[float] = mapped_column(Float, default=0.5)
    y: Mapped[float] = mapped_column(Float, default=0.5)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NfcUser(Base):
    __tablename__ = "nfc_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # LEGACY: antes el usuario se identificaba por UID directo.
    # Ahora el UID puede vivir en nfc_credentials.
    uid_hex: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)

    full_name: Mapped[str] = mapped_column(String(120))
    employee_number: Mapped[str] = mapped_column(String(40), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    credentials = relationship("NfcCredential", back_populates="nfc_user", cascade="all, delete-orphan")


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
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    door: Mapped[str] = mapped_column(String(32), index=True)
    uid: Mapped[str] = mapped_column(String(32), default="", index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    result: Mapped[str] = mapped_column(String(40), default="")
    details: Mapped[str] = mapped_column(Text, default="")


class DeviceKey(Base):
    __tablename__ = "device_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    door_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("doors.door_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    key_hash: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    door = relationship("Door")


class NfcCredential(Base):
    __tablename__ = "nfc_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nfc_user_id: Mapped[int] = mapped_column(
        ForeignKey("nfc_users.id", ondelete="CASCADE"),
        index=True,
    )
    uid_hex: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    tag_type: Mapped[str] = mapped_column(String(20), default="tag")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    nfc_user = relationship("NfcUser", back_populates="credentials")


class EnrollmentStationKey(Base):
    __tablename__ = "enrollment_station_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnrollmentSession(Base):
    __tablename__ = "enrollment_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    station_name: Mapped[str] = mapped_column(String(80), default="main")
    requested_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(String(20), default="pending")
    tag_type: Mapped[str] = mapped_column(String(20), default="tag")
    uid_hex: Mapped[str] = mapped_column(String(32), default="", index=True)
    error_message: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requested_by = relationship("StaffUser")