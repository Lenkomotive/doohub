"""Add image_urls column to session_messages

Revision ID: 006
Revises: 005
Create Date: 2026-03-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_messages", sa.Column("image_urls", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("session_messages", "image_urls")
