"""Chế độ đặc biệt — cho phép hours_early = 0 (Nghỉ thai sản).

Revision ID: 20260818_0054
Revises: 20260817_0053
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260818_0054"
down_revision: Union[str, None] = "20260817_0053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_wt_regime_hours_early", "employee_wt_regimes", type_="check")
    op.create_check_constraint(
        "ck_wt_regime_hours_early",
        "employee_wt_regimes",
        "hours_early IN (0, 1, 2, 3)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_wt_regime_hours_early", "employee_wt_regimes", type_="check")
    op.create_check_constraint(
        "ck_wt_regime_hours_early",
        "employee_wt_regimes",
        "hours_early IN (1, 2, 3)",
    )
