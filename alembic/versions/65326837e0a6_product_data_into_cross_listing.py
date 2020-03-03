"""Product data into Cross Listing

Revision ID: 65326837e0a6
Revises: 7840f93636fd
Create Date: 2020-02-07 15:06:36.624168

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '65326837e0a6'
down_revision = '7840f93636fd'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cross_listings', sa.Column('product_id', sa.Integer(), nullable=True))
    op.add_column('cross_listings', sa.Column('product_upc', sa.String(), nullable=True))
    op.add_column('cross_listings', sa.Column('product_name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('cross_listings', 'product_id')
    op.drop_column('cross_listings', 'product_upc')
    op.drop_column('cross_listings', 'product_name')
