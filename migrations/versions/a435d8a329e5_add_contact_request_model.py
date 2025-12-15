"""Add contact_request model

Revision ID: a435d8a329e5
Revises: f4c2fd5f47f1
Create Date: 2025-12-15 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a435d8a329e5'
down_revision = 'f4c2fd5f47f1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('contact_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contact_info', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('contact_request')
