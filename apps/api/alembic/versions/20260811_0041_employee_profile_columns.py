"""5.1 — mở rộng employees: 15 cột hồ sơ (21§21.3)."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0041"
down_revision = "20260811_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("employees", sa.Column("birth_place_code", sa.String(20), nullable=True))
    op.add_column("employees", sa.Column("nationality_code", sa.String(20), nullable=True))
    op.add_column("employees", sa.Column("ethnicity_code", sa.String(20), nullable=True))
    op.add_column("employees", sa.Column("religion_code", sa.String(20), nullable=True))
    op.add_column("employees", sa.Column("marital_status", sa.String(20), nullable=True))
    op.add_column(
        "employees",
        sa.Column("children_count", sa.SmallInteger(), server_default="0", nullable=False),
    )
    op.add_column("employees", sa.Column("education_code", sa.String(20), nullable=True))
    op.add_column("employees", sa.Column("id_issue_date", sa.Date(), nullable=True))
    op.add_column("employees", sa.Column("id_issue_place_code", sa.String(20), nullable=True))
    op.add_column("employees", sa.Column("permanent_address", sa.Text(), nullable=True))
    op.add_column("employees", sa.Column("temporary_address", sa.Text(), nullable=True))
    op.add_column("employees", sa.Column("urgent_contact", sa.String(200), nullable=True))
    op.add_column("employees", sa.Column("timekeeping_card_no", sa.String(40), nullable=True))
    op.add_column("employees", sa.Column("si_book_no", sa.String(40), nullable=True))
    op.create_index("ix_employees_timekeeping_card_no", "employees", ["timekeeping_card_no"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_employees_timekeeping_card_no", table_name="employees")
    op.drop_column("employees", "si_book_no")
    op.drop_column("employees", "timekeeping_card_no")
    op.drop_column("employees", "urgent_contact")
    op.drop_column("employees", "temporary_address")
    op.drop_column("employees", "permanent_address")
    op.drop_column("employees", "id_issue_place_code")
    op.drop_column("employees", "id_issue_date")
    op.drop_column("employees", "education_code")
    op.drop_column("employees", "children_count")
    op.drop_column("employees", "marital_status")
    op.drop_column("employees", "religion_code")
    op.drop_column("employees", "ethnicity_code")
    op.drop_column("employees", "nationality_code")
    op.drop_column("employees", "birth_place_code")
    op.drop_column("employees", "birth_date")
