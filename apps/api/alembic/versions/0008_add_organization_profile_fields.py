"""Add contact and location columns to organizations.

New nullable columns: contact_name, contact_email, country_name,
country_code, state_name, state_code, city.

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("contact_name", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("contact_email", sa.String(320), nullable=True))
    op.add_column("organizations", sa.Column("country_name", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("country_code", sa.String(10), nullable=True))
    op.add_column("organizations", sa.Column("state_name", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("state_code", sa.String(10), nullable=True))
    op.add_column("organizations", sa.Column("city", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "city")
    op.drop_column("organizations", "state_code")
    op.drop_column("organizations", "state_name")
    op.drop_column("organizations", "country_code")
    op.drop_column("organizations", "country_name")
    op.drop_column("organizations", "contact_email")
    op.drop_column("organizations", "contact_name")
