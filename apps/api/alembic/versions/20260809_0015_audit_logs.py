"""audit_logs — hộp đen (07§7.1 / P5.3)



Revision ID: 20260809_0015

Revises: 20260809_0014

Create Date: 2026-08-09



"""



from typing import Sequence, Union



import sqlalchemy as sa

from alembic import op



revision: str = "20260809_0015"

down_revision: Union[str, None] = "20260809_0014"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None





def upgrade() -> None:

    # UUID PK (thay BIGSERIAL) — tương thích SQLite test + Postgres

    op.create_table(

        "audit_logs",

        sa.Column("id", sa.Uuid(), nullable=False),

        sa.Column("actor_user_id", sa.Uuid(), nullable=True),

        sa.Column("actor_username", sa.String(length=64), nullable=True),

        sa.Column("action", sa.String(length=80), nullable=False),

        sa.Column("entity_type", sa.String(length=80), nullable=False, server_default=""),

        sa.Column("entity_id", sa.String(length=120), nullable=True),

        sa.Column("summary", sa.Text(), nullable=False, server_default=""),

        sa.Column("meta_json", sa.JSON(), nullable=True),

        sa.Column("ip", sa.String(length=64), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),

        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),

        sa.PrimaryKeyConstraint("id"),

    )

    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])





def downgrade() -> None:

    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")

    op.drop_index("ix_audit_logs_action", table_name="audit_logs")

    op.drop_table("audit_logs")


