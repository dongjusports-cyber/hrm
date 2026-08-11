"""attendance_days + timesheet tháng (schema 07§7.3–7.4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AttendanceDay(Base):
    __tablename__ = "attendance_days"
    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_attendance_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    first_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worked_hours: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    early_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ot_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ot_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # weekday | weekend | holiday | none
    punch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_workday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # V2 hạng mục 3.4 (21§21.5):
    work_shift_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("work_shifts.code", ondelete="SET NULL"), nullable=True
    )
    leave_code: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("leave_types.code", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(10), default="machine", nullable=False)
    night_hours: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=Decimal("0"), nullable=False)
    sunday_hours: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=Decimal("0"), nullable=False)
    holiday_hours: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=Decimal("0"), nullable=False)
    ot_night_hours: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=Decimal("0"), nullable=False)
    segment: Mapped[str] = mapped_column(String(10), default="official", nullable=False, index=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    edited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LeaveType(Base):
    """14 mã nghỉ thật, nguồn `Common_Codes.csv` nhóm `HRAB0110` (21§21.4, hạng mục 2.2,
    bảng đầy đủ ở 22§22.6). `pay_ratio_percent` NULL riêng cho `PER` — GenusSuite bỏ trống,
    buộc HR khai báo qua Admin (2.8), không được đoán (N4)."""

    __tablename__ = "leave_types"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    paid_by_company: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    counts_as_unauthorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # V2 (hạng mục 2.2, 21§21.4) — 6 cột mới:
    pay_ratio_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0 | 70 | 100 | NULL (PER)
    paid_by_si: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # BHXH chi trả
    affects_attendance_bonus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    counts_as_worked_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_days_per_year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PayPeriod(Base):
    __tablename__ = "pay_periods"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_pay_period_ym"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    official_work_days: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    salary_divisor: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False)
    # open | calculating | published | locked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TimesheetMonth(Base):
    __tablename__ = "timesheet_months"
    __table_args__ = (UniqueConstraint("pay_period_id", "employee_id", name="uq_timesheet_period_emp"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_periods.id"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    worked_days: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    al_days: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    rem_days: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    late_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    early_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ot_hours_weekday: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    ot_hours_weekend: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    ot_hours_holiday: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TimesheetMonthDetail(Base):
    """Chi tiết bảng công tháng theo category × segment (21§21.5, hạng mục 3.5)."""

    __tablename__ = "timesheet_month_details"
    __table_args__ = (
        UniqueConstraint(
            "timesheet_month_id",
            "category",
            "segment",
            name="uq_timesheet_month_detail_cat_seg",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timesheet_month_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("timesheet_months.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    segment: Mapped[str] = mapped_column(String(10), nullable=False)
    hours: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=Decimal("0"), nullable=False)
    days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)


class LeaveRequest(Base):
    """Đơn xin nghỉ — hàng đợi duyệt HR (21§21.5, hạng mục 3.6)."""

    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_code: Mapped[str] = mapped_column(
        String(40), ForeignKey("leave_types.code", ondelete="RESTRICT"), nullable=False
    )
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_half: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    to_half: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_days: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    document_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnnualLeaveLedger(Base):
    """Sổ phép năm theo NV × năm (4.7, 21§21.6)."""

    __tablename__ = "annual_leave_ledger"
    __table_args__ = (UniqueConstraint("employee_id", "year", name="uq_annual_leave_ledger_emp_year"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    accrued: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    used: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    adjusted: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"), nullable=False)
    last_accrued_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    entries: Mapped[list["AnnualLeaveEntry"]] = relationship(
        "AnnualLeaveEntry", back_populates="ledger", cascade="all, delete-orphan"
    )


class AnnualLeaveEntry(Base):
    """Bút toán phép năm — số dư = opening + tổng các dòng (22§22.7)."""

    __tablename__ = "annual_leave_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("annual_leave_ledger.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # accrual | use | adjust | payout
    days: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ledger: Mapped["AnnualLeaveLedger"] = relationship("AnnualLeaveLedger", back_populates="entries")


class TimesheetAdjustment(Base):
    """Nhập tay nghỉ / OT — MVP không workflow duyệt (04§4.3b)."""

    __tablename__ = "timesheet_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pay_periods.id"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # leave | ot
    leave_code: Mapped[str | None] = mapped_column(String(40), ForeignKey("leave_types.code"), nullable=True)
    days: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    ot_type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # weekday|weekend|holiday
    ot_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkShift(Base):
    """Ca làm việc (21§21.5, hạng mục 2.4) — thực tế công ty CHỈ dùng 1 ca hành chính
    08:00–17:00, nghỉ trưa 12:00–13:00 (trừ 1 giờ). Dựng đủ cột để sau này thêm ca
    (2/3 kíp) không phải chạy migration — không seed sẵn ca nào ngoài ca hành chính."""

    __tablename__ = "work_shifts"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    lunch_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    lunch_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    dinner_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    dinner_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    ot_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    night_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    lunch_deduct_hours: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=Decimal("0"), nullable=False)
    dinner_deduct_hours: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=Decimal("0"), nullable=False)
    standard_hours: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=Decimal("8"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TeamShiftSchedule(Base):
    """Xếp ca THEO TỔ, không theo từng người (21§21.5, hạng mục 2.4)."""

    __tablename__ = "team_shift_schedules"
    __table_args__ = (UniqueConstraint("team_id", "work_date", name="uq_team_shift_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    work_shift_id: Mapped[str] = mapped_column(String(20), ForeignKey("work_shifts.code"), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    work_shift: Mapped[WorkShift] = relationship()
