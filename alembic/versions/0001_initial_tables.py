"""initial tables

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source",
            sa.Enum("scanner", "partner", "manual", name="leadsource"),
            nullable=False,
        ),
        sa.Column(
            "stage",
            sa.Enum("new", "contacted", "qualified", "transferred", "lost", name="coldstage"),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "business_domain",
            sa.Enum("first", "second", "third", name="businessdomain"),
            nullable=True,
        ),
        sa.Column("messages_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_recommendation", sa.String(64), nullable=True),
        sa.Column("ai_reason", sa.Text(), nullable=True),
        sa.Column("ai_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "stage",
            sa.Enum("new", "kyc", "agreement", "paid", "lost", name="salestage"),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("sales")
    op.drop_table("leads")
    op.execute("DROP TYPE IF EXISTS salestage")
    op.execute("DROP TYPE IF EXISTS coldstage")
    op.execute("DROP TYPE IF EXISTS businessdomain")
    op.execute("DROP TYPE IF EXISTS leadsource")
