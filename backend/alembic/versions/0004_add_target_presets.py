"""add target_presets

Revision ID: 8f2c4a91e03d
Revises: 7aa25fec512c
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import fastapi_users_db_sqlalchemy


revision: str = '8f2c4a91e03d'
down_revision: Union[str, Sequence[str], None] = '7aa25fec512c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'target_presets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', fastapi_users_db_sqlalchemy.generics.GUID(), nullable=False),
        sa.Column('name', sa.String(length=48), nullable=False),
        sa.Column('values_json', sa.JSON(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_preset_user_name'),
    )
    op.create_index(
        op.f('ix_target_presets_user_id'), 'target_presets', ['user_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_target_presets_user_id'), table_name='target_presets')
    op.drop_table('target_presets')
