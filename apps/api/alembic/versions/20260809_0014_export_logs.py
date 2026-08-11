"""export_logs — audit xuất dữ liệu (12§12.3 / P5.2)



Revision ID: 20260809_0014

Revises: 20260809_0013

Create Date: 2026-08-09



"""



from typing import Sequence, Union



import sqlalchemy as sa

from alembic import op



revision: str = "20260809_0014"

down_revision: Union[str, None] = "20260809_0013"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None





def upgrade() -> None:

    op.create_table(

        "export_logs",

        sa.Column("id", sa.Uuid(), nullable=False),

        sa.Column("user_id", sa.Uuid(), nullable=False),

        sa.Column("kind", sa.String(length=40), nullable=False),

        sa.Column("period", sa.String(length=20), nullable=True),

        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("filename", sa.String(length=200), nullable=False, server_default=""),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),

        sa.PrimaryKeyConstraint("id"),

    )

    op.create_index("ix_export_logs_user_id", "export_logs", ["user_id"])

    op.create_index("ix_export_logs_kind", "export_logs", ["kind"])

    op.create_index("ix_export_logs_created_at", "export_logs", ["created_at"])





def downgrade() -> None:

    op.drop_index("ix_export_logs_created_at", table_name="export_logs")

    op.drop_index("ix_export_logs_kind", table_name="export_logs")

    op.drop_index("ix_export_logs_user_id", table_name="export_logs")

    op.drop_table("export_logs")


