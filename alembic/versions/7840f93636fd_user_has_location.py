"""User has location

Revision ID: 7840f93636fd
Revises: a436af697294
Create Date: 2020-02-04 13:15:32.062138

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7840f93636fd'
down_revision = 'a436af697294'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('ebay_location_key', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'ebay_location_key')
