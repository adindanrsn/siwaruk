"""Refactor Business: rename user_id to owner_id, drop unique constraint (one-to-many)

Revision ID: a3f2b1c9d4e5
Revises: 277136aeaa65
Create Date: 2026-07-26

Migrates the businesses table from a one-to-one User relationship (via unique user_id)
to a one-to-many relationship (via owner_id without unique constraint).
All existing data is preserved; existing business records keep their owner association.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f2b1c9d4e5'
down_revision = '277136aeaa65'
branch_labels = None
depends_on = None


def upgrade():
    # Use batch mode for compatibility with databases that don't support ALTER COLUMN directly
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        # Step 1: Drop the unique constraint on user_id
        # Actual constraint name confirmed from pg_constraint: businesses_user_id_key
        batch_op.drop_constraint('businesses_user_id_key', type_='unique')

        # Step 2: Rename the column user_id -> owner_id
        batch_op.alter_column(
            'user_id',
            new_column_name='owner_id',
            existing_type=sa.Integer(),
            existing_nullable=False
        )


def downgrade():
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        # Restore column name
        batch_op.alter_column(
            'owner_id',
            new_column_name='user_id',
            existing_type=sa.Integer(),
            existing_nullable=False
        )
        # Re-add unique constraint with original name
        batch_op.create_unique_constraint('businesses_user_id_key', ['user_id'])
