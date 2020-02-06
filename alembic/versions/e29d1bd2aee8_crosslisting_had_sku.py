"""Crosslisting had sku

Revision ID: e29d1bd2aee8
Revises: b44d800dd308
Create Date: 2020-02-03 13:26:15.134225

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e29d1bd2aee8'
down_revision = 'b44d800dd308'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cross_listings', sa.Column('sku', sa.String(), nullable=True))


def downgrade():
    op.drop_column('cross_listings', 'sku')
