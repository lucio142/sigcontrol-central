import os
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app import models
from app.security import hash_password


def env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def create_user_if_missing(
    db: Session,
    email: str,
    password: str,
    role: str,
    is_active: bool = True,
):
    email = email.strip().lower()

    if not password or "CAMBIAR" in password:
        raise ValueError(f"Password inválido para {email}. Cambia las contraseñas en .env")

    existing = db.query(models.StaffUser).filter(models.StaffUser.email == email).first()

    if existing:
        print(f"[OK] Ya existe: {existing.email} (role={existing.role})")
        return existing

    user = models.StaffUser(
        email=email,
        password_hash=hash_password(password),
        role=role.strip(),
        is_active=is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"[OK] Creado: {user.email} (role={user.role})")
    return user


def main():
    print("===== Creando usuarios base SigControl =====")

    db: Session = SessionLocal()

    try:
        users = [
            {
                "email": env("ADMIN_EMAIL", "admin@sigcontrol.com"),
                "password": env("ADMIN_PASSWORD", "CAMBIAR_ADMIN_PASSWORD"),
                "role": env("ADMIN_ROLE", "admin"),
            },
            {
                "email": env("SEGURIDAD_EMAIL", "seguridad@sigcontrol.com"),
                "password": env("SEGURIDAD_PASSWORD", "CAMBIAR_SEGURIDAD_PASSWORD"),
                "role": "seguridad",
            },
            {
                "email": env("SISTEMAS_EMAIL", "sistemas@sigcontrol.com"),
                "password": env("SISTEMAS_PASSWORD", "CAMBIAR_SISTEMAS_PASSWORD"),
                "role": "sistemas",
            },
            {
                "email": env("HSC_EMAIL", "hsc@sigcontrol.com"),
                "password": env("HSC_PASSWORD", "CAMBIAR_HSC_PASSWORD"),
                "role": "hsc",
            },
        ]

        for item in users:
            create_user_if_missing(
                db=db,
                email=item["email"],
                password=item["password"],
                role=item["role"],
                is_active=True,
            )

        print("===== Seed completado correctamente =====")

    finally:
        db.close()


if __name__ == "__main__":
    main()