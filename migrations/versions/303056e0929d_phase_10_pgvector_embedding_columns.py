"""Phase 10 pgvector embedding columns

Revision ID: 303056e0929d
Revises: 9c7b536d076c
Create Date: 2026-09-13 19:55:56.082680

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '303056e0929d'
down_revision = '9c7b536d076c'
branch_labels = None
depends_on = None


def upgrade():
    # Use raw SQL to add VECTOR column — pgvector must be enabled on the DB.
    # Run once: CREATE EXTENSION IF NOT EXISTS vector;
    conn = op.get_bind()
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.execute(sa.text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS embedding vector(768)"))
    conn.execute(sa.text("ALTER TABLE notes   ADD COLUMN IF NOT EXISTS embedding vector(768)"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE clients DROP COLUMN IF EXISTS embedding"))
    conn.execute(sa.text("ALTER TABLE notes   DROP COLUMN IF EXISTS embedding"))
