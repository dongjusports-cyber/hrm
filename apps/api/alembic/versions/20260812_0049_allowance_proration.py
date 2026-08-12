"""PCCC/TOXIC/POSITION/TECH/OTHER — prorate theo ngày hưởng (mức tháng ÷ mẫu số × tử số)."""

from alembic import op

revision = "20260812_0049"
down_revision = "20260812_0048"
branch_labels = None
depends_on = None

_CODES = ("TOXIC", "POSITION", "PCCC", "TECH", "OTHER")


def upgrade() -> None:
    codes = ", ".join(f"'{c}'" for c in _CODES)
    op.execute(
        f"""
        UPDATE pay_components
        SET proration = 'by_worked_days',
            proration_rule = 'by_worked_days'
        WHERE code IN ({codes})
        """
    )


def downgrade() -> None:
    codes = ", ".join(f"'{c}'" for c in _CODES)
    op.execute(
        f"""
        UPDATE pay_components
        SET proration = 'fixed',
            proration_rule = 'none'
        WHERE code IN ({codes})
        """
    )
