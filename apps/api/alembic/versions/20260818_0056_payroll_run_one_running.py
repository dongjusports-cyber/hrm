"""Một lần «Tính lương» running / kỳ — khóa race đúp chuột.

Revision ID: 20260818_0056
Revises: 20260818_0055
"""

from alembic import op
import sqlalchemy as sa

revision = "20260818_0056"
down_revision = "20260818_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Giữ 1 dòng running mới nhất / kỳ, còn lại đánh error trước khi tạo unique index.
    op.execute(
        sa.text(
            """
            UPDATE payroll_runs
            SET status = 'error',
                finished_at = CURRENT_TIMESTAMP,
                message = 'Timeout — trùng lần tính (khóa kỳ).'
            WHERE status = 'running'
              AND started_at < (
                SELECT MAX(pr2.started_at)
                FROM payroll_runs AS pr2
                WHERE pr2.pay_period_id = payroll_runs.pay_period_id
                  AND pr2.status = 'running'
              )
            """
        )
    )
    op.create_index(
        "uq_payroll_runs_one_running",
        "payroll_runs",
        ["pay_period_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("uq_payroll_runs_one_running", table_name="payroll_runs")
