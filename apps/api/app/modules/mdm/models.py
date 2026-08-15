"""Departments + Employees (schema 07§7.2) — tiền NUMERIC/Decimal.

V2 (HIEN_PHAP 21§21.2 — hạng mục 1.1): thêm Team/Position/Job cho cây tổ chức 2 cấp
Bộ phận › Tổ. Department.is_active chuyển thành cột SUY RA từ effective_to (không lưu),
theo đúng chỉ định "hai cấp hiệu lực" — is_active không trả lời được "tháng 3 tổ này có
tồn tại không", chỉ effective_from/effective_to trả lời được.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class Department(Base):
    """Bộ phận — cấp cao nhất của cây tổ chức (10 bộ phận thật, nguồn TCO_EODEPT)."""

    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_local: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="direct", nullable=False)
    dept_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # office | factory | support
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # alias Mitapro — JSON list cho Postgres + SQLite
    mitapro_names: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teams: Mapped[list["Team"]] = relationship(back_populates="department")

    @hybrid_property
    def is_active(self) -> bool:
        """Suy ra từ effective_to — KHÔNG lưu cột riêng (HIEN_PHAP 21§21.2)."""
        return self.effective_to is None or self.effective_to >= date.today()


class Team(Base):
    """Tổ — cấp mà công nhân thực sự thuộc về (73 tổ thật, nguồn THR_ABWORKGRP).

    default_shift_id đã thêm ở hạng mục 2.4 (bảng work_shifts tạo cùng đợt) — trước đó
    (1.1) chưa có vì work_shifts chưa tồn tại. FK trỏ theo CODE (PK của work_shifts, giống
    leave_types), không phải uuid.
    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("departments.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_local: Mapped[str | None] = mapped_column(String(200), nullable=True)
    default_shift_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("work_shifts.code"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    department: Mapped[Department] = relationship(back_populates="teams")
    employees: Mapped[list[Employee]] = relationship(back_populates="team")
    # Không dựng relationship() Python sang WorkShift (module attendance) ở đây — tránh phụ
    # thuộc vòng giữa mdm <-> attendance. Cần đọc ca mặc định thì query WorkShift theo
    # default_shift_id (FK, xem docstring class) ở tầng service khi cần.

    @hybrid_property
    def is_active(self) -> bool:
        return self.effective_to is None or self.effective_to >= date.today()


class Position(Base):
    """Chức vụ — 52 mã thật, nguồn HRAB0060. Tách rời mã công việc (Job)."""

    __tablename__ = "positions"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_local: Mapped[str | None] = mapped_column(String(200), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_management: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Job(Base):
    """Mã công việc (nghề) — 82 mã thật, nguồn HRAB0100. Dùng cho HĐ và bảo hộ lao động."""

    __tablename__ = "jobs"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_local: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_hazardous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_place_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ethnicity_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    religion_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    children_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    education_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    id_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    id_issue_place_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    permanent_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    temporary_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgent_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    si_book_no: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pay_channel: Mapped[str] = mapped_column(String(10), default="ATM", nullable=False)  # ATM | CASH
    # V2 (hạng mục 1.1/1.5) — cấp Tổ thật là nơi NV thuộc về. Bộ phận SUY RA qua
    # team.department_id, KHÔNG lưu department_id riêng ở employees (21§21.3 — "không lưu
    # hai chỗ"; cột department_id đã xóa ở migration dọn dẹp đợt 1, xem báo cáo phiên).
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True
    )
    position_code: Mapped[str | None] = mapped_column(String(20), ForeignKey("positions.code"), nullable=True)
    job_code: Mapped[str | None] = mapped_column(String(20), ForeignKey("jobs.code"), nullable=True)
    position_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_signed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    probation_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    contract_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    si_base_override: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    si_enrolled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pit_enrolled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tax_dependent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    union_fee_override: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    resign_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team: Mapped["Team | None"] = relationship(back_populates="employees")
    position: Mapped["Position | None"] = relationship()
    job: Mapped["Job | None"] = relationship()
    violations: Mapped[list["EmployeeViolation"]] = relationship(back_populates="employee")
    documents: Mapped[list["EmployeeDocument"]] = relationship(back_populates="employee")
    assignments: Mapped[list["EmployeeAssignment"]] = relationship(
        back_populates="employee",
        order_by="EmployeeAssignment.effective_from.desc()",
    )
    salary_history: Mapped[list["EmployeeSalaryHistory"]] = relationship(
        back_populates="employee",
        order_by="EmployeeSalaryHistory.effective_from.desc()",
    )
    labour_contracts: Mapped[list["LabourContract"]] = relationship(
        back_populates="employee",
        order_by="LabourContract.start_date.desc()",
    )
    family_members: Mapped[list["EmployeeFamilyMember"]] = relationship(
        back_populates="employee",
        order_by="EmployeeFamilyMember.full_name.asc()",
    )
    resignations: Mapped[list["EmployeeResignation"]] = relationship(
        back_populates="employee",
        order_by="EmployeeResignation.seq_no.asc()",
    )
    educations: Mapped[list["EmployeeEducation"]] = relationship(
        back_populates="employee",
        order_by="EmployeeEducation.from_date.desc()",
    )
    experiences: Mapped[list["EmployeeExperience"]] = relationship(
        back_populates="employee",
        order_by="EmployeeExperience.from_date.desc()",
    )
    health_checks: Mapped[list["EmployeeHealthCheck"]] = relationship(
        back_populates="employee",
        order_by="EmployeeHealthCheck.check_date.desc()",
    )

    @hybrid_property
    def department(self) -> Department | None:
        """Bộ phận suy ra qua Tổ — không lưu department_id riêng (21§21.3)."""
        return self.team.department if self.team else None

    @hybrid_property
    def department_id(self) -> uuid.UUID | None:
        return self.team.department_id if self.team else None

    @department_id.expression
    def department_id(cls):  # noqa: N805 — quy ước hybrid_property của SQLAlchemy
        return (
            select(Team.department_id)
            .where(Team.id == cls.team_id)
            .correlate(cls)
            .scalar_subquery()
        )


class EmployeeViolation(Base):
    """Biên bản / vi phạm kỷ luật — file scan lưu ngoài DB."""

    __tablename__ = "employee_violations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    penalty: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="violations")


class EmployeeDocument(Base):
    """Hồ sơ giấy đã scan (HĐ, CCCD, lý lịch…) — file ngoài DB."""

    __tablename__ = "employee_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(40), default="other", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="documents")


class EmployeeAssignment(Base):
    """Lịch sử đổi tổ / chức vụ (21§21.3, hạng mục 1.5).

    Không có bảng này thì in lại bảng lương cũ sẽ ra sai tổ — mỗi lần chuyển tổ (đơn lẻ hay
    hàng loạt) phải ghi một dòng ở đây trước khi cập nhật employees.team_id. Bản ghi đang có
    hiệu lực (hiện tại) có effective_to = NULL; khi chuyển tiếp, bản ghi cũ được đóng lại
    (effective_to = effective_from mới - 1 ngày) — không chồng lấn ngày.
    """

    __tablename__ = "employee_assignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    position_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("positions.code"), nullable=True
    )
    job_code: Mapped[str | None] = mapped_column(String(20), ForeignKey("jobs.code"), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    decision_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="assignments")
    team: Mapped["Team"] = relationship()


class EmployeeSalaryHistory(Base):
    """Lịch sử thay đổi lương HĐ / thử việc (21§21.3)."""

    __tablename__ = "employee_salary_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    field_code: Mapped[str] = mapped_column(String(30), default="contract_salary", nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    old_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    new_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    decision_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="salary_history")


class LabourContract(Base):
    """Hợp đồng lao động — lịch sử HĐ, cảnh báo hết hạn (21§21.3, hạng mục 5.2)."""

    __tablename__ = "labour_contracts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    contract_type_code: Mapped[str] = mapped_column(String(20), nullable=False)
    seq_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sign_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    position_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("positions.code"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped[Employee] = relationship(back_populates="labour_contracts")
    team: Mapped["Team | None"] = relationship()
    position: Mapped["Position | None"] = relationship()


class EmployeeFamilyMember(Base):
    """Thân nhân / người phụ thuộc — giảm trừ gia cảnh tính ra (21§21.3, hạng mục 5.3)."""

    __tablename__ = "employee_family_members"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    relationship_code: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_tax_dependent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dependent_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    dependent_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped[Employee] = relationship(back_populates="family_members")


class EmployeeResignation(Base):
    """Lịch sử nghỉ việc — cho phép nhiều lần (21§21.3, hạng mục 5.4).

    UNIQUE (employee_id, seq_no) — KHÔNG unique theo employee_id đơn lẻ.
    """

    __tablename__ = "employee_resignations"
    __table_args__ = (
        UniqueConstraint("employee_id", "seq_no", name="uq_employee_resignations_emp_seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    resign_type_code: Mapped[str] = mapped_column(String(20), nullable=False)
    applied_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_working_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    severance_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severance_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    handover_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rehired_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rehire_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rehire_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped[Employee] = relationship(back_populates="resignations")


class EmployeeEducation(Base):
    __tablename__ = "employee_educations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)
    major: Mapped[str | None] = mapped_column(String(120), nullable=True)
    degree_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="educations")


class EmployeeExperience(Base):
    __tablename__ = "employee_experiences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="experiences")


class EmployeeWtRegime(Base):
    """Chế độ về sớm (22§22.14) — Thai sản / Nuôi con: giảm giờ cuối ca theo kỳ.

    Không dùng status=maternity cho Nuôi con — chỉ bảng này. Engine (Bước E) đọc
    regime hiệu lực (date_from ≤ ngày ≤ date_to) để bù giờ / miễn về sớm.
    """

    __tablename__ = "employee_wt_regimes"
    __table_args__ = (
        CheckConstraint("hours_early IN (1, 2, 3)", name="ck_wt_regime_hours_early"),
        CheckConstraint("date_to >= date_from", name="ck_wt_regime_dates"),
        Index("ix_wt_regimes_employee_dates", "employee_id", "date_from", "date_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    regime_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PREGNANT | CHILD
    hours_early: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 | 2 | 3
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmployeeHealthCheck(Base):
    __tablename__ = "employee_health_checks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    check_date: Mapped[date] = mapped_column(Date, nullable=False)
    facility_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="health_checks")


class LookupValue(Base):
    """Danh mục phẳng, KHÔNG mang quy tắc (21§21.4, hạng mục 2.1) — dân tộc, tôn giáo,
    quốc tịch, nơi sinh, nơi cấp CCCD, trình độ.

    Danh mục CÓ quy tắc (vd loại nghỉ có % lương, chức vụ có level) phải có bảng riêng —
    không lặp lại sai lầm `TCO_ABCODE` của GenusSuite (2.609 mã trộn 427 nhóm trong 1 bảng).
    """

    __tablename__ = "lookup_values"
    __table_args__ = (UniqueConstraint("group_code", "code", name="uq_lookup_values_group_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_local: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
