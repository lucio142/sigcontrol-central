"""make nfc_users.uid_hex nullable

Revision ID: 9f2c1f6b7a10
Revises: 6cf3866caeb2
Create Date: 2026-04-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2c1f6b7a10"
down_revision: Union[str, None] = "6cf3866caeb2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "nfc_users",
        "uid_hex",
        existing_type=sa.String(length=32),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    # Antes de volver a NOT NULL, aseguramos que no existan filas con uid_hex NULL
    op.execute("UPDATE nfc_users SET uid_hex = '' WHERE uid_hex IS NULL")

    op.alter_column(
        "nfc_users",
        "uid_hex",
        existing_type=sa.String(length=32),
        nullable=False,
        existing_nullable=True,
    )