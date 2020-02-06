"""Create operations table

Revision ID: b44d800dd308
Revises: 8edc67a8b9d9
Create Date: 2020-01-28 11:58:50.536930

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b44d800dd308'
down_revision = '8edc67a8b9d9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('operations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cross_listing_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('workflow_specs', sa.JSON(), nullable=True),
        sa.Column('workflow_instance', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_operations_cross_listing_id'), 'operations', ['cross_listing_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_operations_cross_listing_id'), table_name='operations')
