"""User has ebay policy ids

Revision ID: a436af697294
Revises: e29d1bd2aee8
Create Date: 2020-02-04 12:37:31.189328

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a436af697294'
down_revision = 'e29d1bd2aee8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('ebay_payment_policy_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('ebay_return_policy_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('ebay_fulfillment_policy_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'ebay_payment_policy_id')
    op.drop_column('users', 'ebay_return_policy_id')
    op.drop_column('users', 'ebay_fulfillment_policy_id')
    pass
