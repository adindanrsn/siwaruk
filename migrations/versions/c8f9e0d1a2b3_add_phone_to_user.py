"""Add phone to user

Revision ID: c8f9e0d1a2b3
Revises: a3f2b1c9d4e5
Create Date: 2026-07-26

Add phone column to users table for owner WhatsApp number.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8f9e0d1a2b3'
down_revision = 'a3f2b1c9d4e5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('phone')
