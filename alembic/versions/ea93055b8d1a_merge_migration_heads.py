"""Merge migration heads

Revision ID: ea93055b8d1a
Revises: 001_add_content_types_data, 002_add_voice_cols
Create Date: 2025-12-15 16:53:52.842205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea93055b8d1a'
down_revision: Union[str, None] = ('001_add_content_types_data', '002_add_voice_cols')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
