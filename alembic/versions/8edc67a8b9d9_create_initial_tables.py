"""Create initial tables

Revision ID: 8edc67a8b9d9
Revises:
Create Date: 2020-01-28 09:25:59.509184

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8edc67a8b9d9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('cross_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=True),
        sa.Column('marketplace', sa.String(length=50), nullable=True),
        sa.Column('price_cents', sa.Integer(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('secondary_external_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('operational_status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('ebay_token', sa.String(), nullable=True),
        sa.Column('ebay_refresh_token', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('cross_listings')
    op.drop_table('users')
