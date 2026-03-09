"""Widen session mode column from 20 to 50 chars

Revision ID: 012
Revises: 011
"""

from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"


def upgrade() -> None:
    op.alter_column("sessions", "mode", type_=sa.String(50), existing_type=sa.String(20))


def downgrade() -> None:
    op.alter_column("sessions", "mode", type_=sa.String(20), existing_type=sa.String(50))
