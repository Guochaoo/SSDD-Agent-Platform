"""persist non-image chat attachments"""

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7c8"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("attachments", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "attachments")
