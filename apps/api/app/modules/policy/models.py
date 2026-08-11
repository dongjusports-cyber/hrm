"""Models policy_packages + confirm log (schema 07§7.3) + bảng chính sách có ngày hiệu lực (21§21.4, hạng mục 2.5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base

# JSONB trên Postgres; JSON trên SQLite (tests)
PayloadType = JSON().with_variant(JSONB(), "postgresql")


class PolicyPackage(Base):
    __tablename__ = "policy_packages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    payload: Mapped[dict] = mapped_column(PayloadType, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PolicyConfirmLog(Base):
    __tablename__ = "policy_confirm_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("policy_packages.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    confirm_step: Mapped[int] = mapped_column(Integer, nullable=False)  # luôn 3 khi ghi
    before_payload: Mapped[dict] = mapped_column(PayloadType, nullable=False)
    after_payload: Mapped[dict] = mapped_column(PayloadType, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InsuranceRate(Base):
    """Tỷ lệ BHXH/BHYT/BHTN + công đoàn + trần nền (21§21.4, 22§22.9).

    `union_pct` giữ đúng tên cột trong 21 — thực tế GenusSuite lưu **số tiền cố định** 44.100đ
    (không phải %), xem báo cáo phiên 2.5 mục Lệch.
    """

    __tablename__ = "insurance_rates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    si_employee_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)  # 8 = 8%
    hi_employee_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)  # 1.5
    ui_employee_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)  # 1
    union_pct: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)  # 44100đ (lệch tên)
    si_base_cap: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    region_min_wage: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PitBracket(Base):
    """Biểu thuế TNCN lũy tiến — 7 bậc, có ngày hiệu lực (21§21.4)."""

    __tablename__ = "pit_brackets"
    __table_args__ = (UniqueConstraint("effective_from", "seq", name="uq_pit_brackets_from_seq"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    from_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)  # 5 = 5%
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PitDeduction(Base):
    """Giảm trừ gia cảnh TNCN — bản thân + người phụ thuộc (21§21.4, 22§22.10)."""

    __tablename__ = "pit_deductions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    self_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    dependent_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SeniorityAllowanceTier(Base):
    """Bậc phụ cấp thâm niên theo số tháng làm việc (21§21.4, 22§22.5 / F_CAL_SERVERANCE).

    Công thức GenusSuite `FLOOR(tháng/6)×25.000` ở khoảng 6–119 được **bung thành từng bậc
    6 tháng** lúc seed — mọi số nằm trong bảng, không viết cứng công thức trong engine (N4).
    """

    __tablename__ = "seniority_allowance_tiers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    months_from: Mapped[int] = mapped_column(Integer, nullable=False)
    months_to: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = không giới hạn trên
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttendanceBonusRule(Base):
    """Ngưỡng phạt chuyên cần + số tiền đủ điều kiện (21§21.4, 22§22.12 / F_CAL_INDUS_AMT).

    late≥half → 50%; late≥zero hoặc early≥zero hoặc có vắng → 0%. Số tiền chuẩn 600.000 (20§20.7).
    """

    __tablename__ = "attendance_bonus_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    late_count_half: Mapped[int] = mapped_column(Integer, nullable=False)
    early_count_half: Mapped[int] = mapped_column(Integer, nullable=False)
    late_count_zero: Mapped[int] = mapped_column(Integer, nullable=False)
    early_count_zero: Mapped[int] = mapped_column(Integer, nullable=False)
    exempt_leave_codes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    full_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
