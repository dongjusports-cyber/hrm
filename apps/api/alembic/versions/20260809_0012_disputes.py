"""disputes table — Worker khiếu nại (P4.3)



Revision ID: 20260809_0012

Revises: 20260809_0011

Create Date: 2026-08-09



"""



from typing import Sequence, Union



import sqlalchemy as sa

from alembic import op



revision: str = "20260809_0012"

down_revision: Union[str, None] = "20260809_0011"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None





def upgrade() -> None:

    op.create_table(

        "disputes",

        sa.Column("id", sa.Uuid(), nullable=False),

        sa.Column("code", sa.String(length=20), nullable=False),

        sa.Column("payslip_id", sa.Uuid(), nullable=False),

        sa.Column("employee_id", sa.Uuid(), nullable=False),

        sa.Column("reason_code", sa.String(length=40), nullable=False),

        sa.Column("description", sa.Text(), nullable=False, server_default=""),

        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),

        sa.Column("ai_summary", sa.Text(), nullable=True),

        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),

        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),

        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"]),

        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),

        sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"]),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint("code"),

    )

    op.create_index("ix_disputes_code", "disputes", ["code"])

    op.create_index("ix_disputes_payslip_id", "disputes", ["payslip_id"])

    op.create_index("ix_disputes_employee_id", "disputes", ["employee_id"])

    op.create_index("ix_disputes_status", "disputes", ["status"])





def downgrade() -> None:

    op.drop_index("ix_disputes_status", table_name="disputes")

    op.drop_index("ix_disputes_employee_id", table_name="disputes")

    op.drop_index("ix_disputes_payslip_id", table_name="disputes")

    op.drop_index("ix_disputes_code", table_name="disputes")

    op.drop_table("disputes")


