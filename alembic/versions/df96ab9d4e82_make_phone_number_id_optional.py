"""Make phone_number_id optional

Revision ID: df96ab9d4e82
Revises: 2ff347aa9abb
Create Date: 2025-05-06 15:42:47.558883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df96ab9d4e82'
down_revision: Union[str, None] = '2ff347aa9abb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('companies', 'phone_number_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('companies', 'phone_number_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
