"""payroll_runs, payslips, policy_snapshots, allowance catalog (schema 07)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

PayloadType = JSON().with_variant(JSONB(), "postgresql")


class PayComponent(Base):
    """Danh mục khoản lương — đổi tên từ `allowance_types` (21§21.4, hạng mục 2.3), giữ dữ
    liệu + 4 cột cũ (`proration`, `include_in_si_base`, `include_in_ot_base` — payroll engine
    thật đang đọc, không đập). 5 cột mới `kind`/`affects_*`/`proration_rule` để phân loại
    earning/deduction và chuẩn bị nối PIT (4.x) — HR sửa nghĩa qua Admin (2.8) nếu cần.

    20 mã hiện có (seed_allowances.py) suy ra từ bảng `THR_SALARY_EMP`/`THR_ABEMPMAS`
    (GenuSuite HRM/GenuiSuite_Code.sql — ~148 cột, đúng nguồn 21§21.4 nói tới), mỗi mã có
    comment tiếng Việt gốc làm chứng — KHÔNG suy đoán. Vẫn chưa đủ ~30 vì phần cột còn lại
    là ngày công/OT/nghỉ (đã có bảng riêng: attendance_days, leave_types, engine OT) hoặc cột
    kỹ thuật (PK, CRT_DT…), không phải khoản lương riêng — xem chi tiết ở đầu CATALOG trong
    seed_allowances.py. HR bổ sung tiếp qua Admin (2.8) nếu phát sinh khoản thật chưa có ở đây.
    """

    __tablename__ = "pay_components"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    proration: Mapped[str] = mapped_column(String(40), default="fixed", nullable=False)
    # by_worked_days | full_if_eligible | fixed | seniority_tiers | attend_penalty
    include_in_si_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    include_in_ot_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    rules: Mapped[dict | None] = mapped_column(PayloadType, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # V2 (hạng mục 2.3, 21§21.4) — 5 cột mới:
    kind: Mapped[str] = mapped_column(String(20), default="earning", nullable=False)  # earning|deduction|info
    affects_si_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    affects_ot_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    affects_pit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    proration_rule: Mapped[str] = mapped_column(String(30), default="none", nullable=False)
    # none | by_worked_days | by_calendar_days


# Alias tương thích — mã cũ trong scripts/deprecated còn import tên này (N1: mở rộng không đập).
AllowanceType = PayComponent


class EmployeeAllowanceAssignment(Base):
    __tablename__ = "employee_allowance_assignments"
    __table_args__ = (
        UniqueConstraint("employee_id", "allowance_type_id", name="uq_emp_allowance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    allowance_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_components.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    meta: Mapped[dict | None] = mapped_column(PayloadType, nullable=True)


class PolicySnapshot(Base):
    __tablename__ = "policy_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_periods.id"), nullable=False, index=True
    )
    package_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    payload: Mapped[dict] = mapped_column(PayloadType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (
        Index(
            "uq_payroll_runs_one_running",
            "pay_period_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
            sqlite_where=text("status = 'running'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_periods.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="running", nullable=False)
    # running | success | error
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    policy_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("policy_snapshots.id"), nullable=True
    )


class PayslipAdjustment(Base):
    """Khoản cộng/trừ bất thường — Re-Pay, truy lĩnh, tạm ứng… (07 / 10.3#15)."""

    __tablename__ = "payslip_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_periods.id"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # addon | deduction
    reason: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmployeeBonus(Base):
    """Thưởng Tết / thưởng đợt — nguồn THR_BONUS (4.8, 21§21.6)."""

    __tablename__ = "employee_bonuses"
    __table_args__ = (
        UniqueConstraint("employee_id", "bonus_year", "seq_times", name="uq_employee_bonus_year_seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bonus_year: Mapped[int] = mapped_column(Integer, nullable=False)
    seq_times: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    bonus_code: Mapped[str] = mapped_column(String(40), default="TET", nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    bonus_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_periods.id"), nullable=False, index=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("pay_period_id", "employee_id", name="uq_payslip_period_emp"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_periods.id"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    policy_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("policy_snapshots.id"), nullable=True
    )
    wd_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    allowance_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    ot_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    other_adjustments: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    gross: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    taxable_income: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    bhxh: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    bhyt: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    bhtn: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    union_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    pit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    net: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    # draft | published | confirmed | disputed | resolved | expired
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirm_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    lines: Mapped[dict | None] = mapped_column(PayloadType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    components: Mapped[list["PayslipComponent"]] = relationship(
        back_populates="payslip", cascade="all, delete-orphan"
    )


class PayslipComponent(Base):
    """Một dòng khoản trên phiếu lương — có segment + seq_no (21§21.6, hạng mục 4.1)."""

    __tablename__ = "payslip_components"
    __table_args__ = (
        UniqueConstraint(
            "payslip_id",
            "component_code",
            "segment",
            "seq_no",
            name="uq_payslip_component_line",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payslip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payslips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(
        String(40), ForeignKey("pay_components.code"), nullable=False, index=True
    )
    segment: Mapped[str] = mapped_column(String(10), default="official", nullable=False)
    seq_no: Mapped[int] = mapped_column(SmallInteger(), default=1, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(10), nullable=True)
    unit_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer(), default=0, nullable=False)

    payslip: Mapped[Payslip] = relationship(back_populates="components")
