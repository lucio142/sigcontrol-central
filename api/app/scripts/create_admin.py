import os
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app import models
from app.security import hash_password


def main():
    email = os.getenv("ADMIN_EMAIL", "admin@sigcontrol.com").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "Admin1234!")
    role = os.getenv("ADMIN_ROLE", "admin")
    is_active = True

    db: Session = SessionLocal()
    try:
        existing = db.query(models.StaffUser).filter(models.StaffUser.email == email).first()
        if existing:
            print(f"[OK] Admin ya existe: {existing.email} (role={existing.role})")
            return

        u = models.StaffUser(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        print(f"[OK] Admin creado: {u.email} / role={u.role}")
        print("TIP: Puedes cambiar credenciales con variables de entorno:")
        print("     ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_ROLE")
    finally:
        db.close()


if __name__ == "__main__":
    main()