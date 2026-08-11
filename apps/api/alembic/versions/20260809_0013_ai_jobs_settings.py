"""ai_jobs + ai_runtime_settings (P4.5 Gemini)



Revision ID: 20260809_0013

Revises: 20260809_0012

Create Date: 2026-08-09



"""



from typing import Sequence, Union



import sqlalchemy as sa

from alembic import op



revision: str = "20260809_0013"

down_revision: Union[str, None] = "20260809_0012"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None





def upgrade() -> None:

    op.create_table(

        "ai_runtime_settings",

        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),

        sa.Column("model_name", sa.String(length=80), nullable=False, server_default="gemini-2.0-flash"),

        sa.Column("max_queries_per_day", sa.Integer(), nullable=False, server_default="20"),

        sa.Column("max_output_tokens", sa.Integer(), nullable=False, server_default="1024"),

        sa.Column("api_key_encrypted", sa.Text(), nullable=True),

        sa.Column(

            "updated_at",

            sa.DateTime(timezone=True),

            server_default=sa.text("now()"),

            nullable=True,

        ),

        sa.PrimaryKeyConstraint("id"),

    )

    op.create_table(

        "ai_jobs",

        sa.Column("id", sa.Uuid(), nullable=False),

        sa.Column("user_id", sa.Uuid(), nullable=False),

        sa.Column("kind", sa.String(length=40), nullable=False),

        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),

        sa.Column("response", sa.Text(), nullable=False, server_default=""),

        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("dispute_id", sa.Uuid(), nullable=True),

        sa.Column("model_name", sa.String(length=80), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),

        sa.ForeignKeyConstraint(["dispute_id"], ["disputes.id"]),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),

        sa.PrimaryKeyConstraint("id"),

    )

    op.create_index("ix_ai_jobs_user_id", "ai_jobs", ["user_id"])

    op.create_index("ix_ai_jobs_kind", "ai_jobs", ["kind"])

    op.create_index("ix_ai_jobs_created_at", "ai_jobs", ["created_at"])





def downgrade() -> None:

    op.drop_index("ix_ai_jobs_created_at", table_name="ai_jobs")

    op.drop_index("ix_ai_jobs_kind", table_name="ai_jobs")

    op.drop_index("ix_ai_jobs_user_id", table_name="ai_jobs")

    op.drop_table("ai_jobs")

    op.drop_table("ai_runtime_settings")


