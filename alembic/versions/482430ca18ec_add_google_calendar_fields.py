"""Add google calendar fields

Revision ID: 482430ca18ec
Revises: 589e7dfc9368
Create Date: 2025-05-08 13:49:04.629366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '482430ca18ec'
down_revision: Union[str, None] = '589e7dfc9368'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('companies', sa.Column('google_refresh_token', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('google_access_token', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('google_token_expiry', sa.DateTime(), nullable=True))
    op.add_column('companies', sa.Column('google_calendar_id', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('companies', 'google_calendar_id')
    op.drop_column('companies', 'google_token_expiry')
    op.drop_column('companies', 'google_access_token')
    op.drop_column('companies', 'google_refresh_token')
    # ### end Alembic commands ###
