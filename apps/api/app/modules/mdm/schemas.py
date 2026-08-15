"""Schemas MDM — Decimal cho tiền, không float."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="direct")
    mitapro_names: list[str] = Field(default_factory=list)


class DepartmentUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    mitapro_names: list[str] | None = None


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    name_local: str | None = None
    level: int | None = None
    is_management: bool
    sort_order: int
    is_active: bool


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    category: str
    mitapro_names: list[str]
    is_active: bool = True


class TeamOut(BaseModel):
    """Tổ — cấp 2 của cây tổ chức, luôn đi cùng Bộ phận (23§ — tên tổ trùng giữa bộ phận)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    name_local: str | None = None
    department_id: UUID
    department_code: str | None = None
    department_name: str | None = None
    is_active: bool = True


class LookupValueOut(BaseModel):
    """Danh mục phẳng — dân tộc, tôn giáo, quốc tịch, nơi sinh, nơi cấp CCCD, trình độ (21§21.4)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_code: str
    code: str
    name: str
    name_local: str | None = None
    sort_order: int = 0
    is_active: bool = True


class EmployeeBase(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=200)
    gender: str | None = None
    birth_date: date | None = None
    birth_place_code: str | None = None
    nationality_code: str | None = None
    ethnicity_code: str | None = None
    religion_code: str | None = None
    marital_status: str | None = None
    children_count: int = 0
    education_code: str | None = None
    id_number: str | None = None
    id_issue_date: date | None = None
    id_issue_place_code: str | None = None
    permanent_address: str | None = None
    temporary_address: str | None = None
    urgent_contact: str | None = None
    si_book_no: str | None = None
    bank_account: str | None = None
    pay_channel: str = "CASH"
    # NV thuộc về TỔ, bộ phận suy ra qua team.department_id — không lưu department_id
    # riêng ở employees (21§21.3, dọn dẹp đợt 1). team_code không duy nhất toàn hệ thống
    # (trùng giữa các bộ phận) nên khi tạo/import bằng mã, cần kèm department_code.
    team_id: UUID | None = None
    team_code: str | None = None
    department_code: str | None = None  # đi kèm team_code để phân giải khi mã tổ trùng
    position_code: str | None = None
    position_title: str | None = None
    join_date: date | None = None
    contract_signed_at: date | None = None
    probation_salary: Decimal = Decimal("0")
    contract_salary: Decimal = Decimal("0")
    si_base_override: Decimal | None = None
    si_enrolled: bool = True
    pit_enrolled: bool = True
    tax_dependent_count: int = 0
    union_fee_override: Decimal | None = None
    status: str = "active"
    resign_date: date | None = None
    phone: str | None = None

    @field_validator("probation_salary", "contract_salary", "si_base_override", "union_fee_override", mode="before")
    @classmethod
    def money_not_float_ok(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return None if v == "" else v
        return Decimal(str(v))

    @field_validator("pay_channel")
    @classmethod
    def pay_channel_ok(cls, v: str) -> str:
        up = v.upper()
        if up not in ("ATM", "CASH"):
            raise ValueError("Trợ Lý AI: pay_channel chỉ ATM hoặc CASH.")
        return up

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str) -> str:
        allowed = {"active", "probation", "resigned", "suspended", "maternity"}
        if v not in allowed:
            raise ValueError("Trợ Lý AI: status không hợp lệ.")
        return v


class EmployeeCreate(EmployeeBase):
    pass


class ValidationIssueOut(BaseModel):
    field: str
    code: str
    level: Literal["error", "warn", "info"]
    message: str
    meta: dict | None = None


class EmployeeValidateRequest(BaseModel):
    is_new: bool = True
    employee_id: UUID | None = None
    payload: dict


class EmployeeValidateResult(BaseModel):
    ok: bool
    issues: list[ValidationIssueOut]
    error_count: int
    warn_count: int
    suggested_code: str | None = None


class EmployeeSuggestCodeOut(BaseModel):
    suggested_code: str


class EmployeeRehireRequest(BaseModel):
    rehire_date: date
    rehire_mode: Literal["fresh_start", "continuity"] = "fresh_start"
    rehire_reason: str | None = None
    team_id: UUID
    status: Literal["active", "probation"] = "probation"
    contract_salary: Decimal | None = None
    probation_salary: Decimal | None = None

    @field_validator("contract_salary", "probation_salary", mode="before")
    @classmethod
    def money_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return None
        s = str(v).replace(",", "").replace(" ", "").strip()
        return Decimal(s)


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    birth_place_code: str | None = None
    nationality_code: str | None = None
    ethnicity_code: str | None = None
    religion_code: str | None = None
    marital_status: str | None = None
    children_count: int | None = None
    education_code: str | None = None
    id_number: str | None = None
    id_issue_date: date | None = None
    id_issue_place_code: str | None = None
    permanent_address: str | None = None
    temporary_address: str | None = None
    urgent_contact: str | None = None
    si_book_no: str | None = None
    bank_account: str | None = None
    pay_channel: str | None = None
    team_id: UUID | None = None
    team_code: str | None = None
    department_code: str | None = None
    position_code: str | None = None
    position_title: str | None = None
    join_date: date | None = None
    contract_signed_at: date | None = None
    probation_salary: Decimal | None = None
    contract_salary: Decimal | None = None
    si_base_override: Decimal | None = None
    si_enrolled: bool | None = None
    pit_enrolled: bool | None = None
    tax_dependent_count: int | None = None
    union_fee_override: Decimal | None = None
    status: str | None = None
    resign_date: date | None = None
    phone: str | None = None

    @field_validator("probation_salary", "contract_salary", "si_base_override", "union_fee_override", mode="before")
    @classmethod
    def money_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return None
        return Decimal(str(v))

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"active", "probation", "resigned", "suspended", "maternity"}
        if v not in allowed:
            raise ValueError("Trợ Lý AI: status không hợp lệ.")
        return v


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_code: str
    full_name: str
    gender: str | None
    birth_date: date | None = None
    birth_place_code: str | None = None
    nationality_code: str | None = None
    ethnicity_code: str | None = None
    religion_code: str | None = None
    marital_status: str | None = None
    children_count: int = 0
    education_code: str | None = None
    id_number: str | None
    id_issue_date: date | None = None
    id_issue_place_code: str | None = None
    permanent_address: str | None = None
    temporary_address: str | None = None
    urgent_contact: str | None = None
    si_book_no: str | None = None
    bank_account: str | None
    pay_channel: str
    department_id: UUID | None
    department_code: str | None = None
    department_name: str | None = None
    team_id: UUID | None = None
    team_code: str | None = None
    team_name: str | None = None
    position_code: str | None = None
    position_title: str | None
    join_date: date | None
    contract_signed_at: date | None
    probation_salary: Decimal
    contract_salary: Decimal
    allowance_total: Decimal = Decimal("0")
    total_salary: Decimal = Decimal("0")
    # Suy ra, không lưu cột — nguồn duy nhất để lưới và Excel xuất khớp nhau (hạng mục 1.4)
    seniority_label: str | None = None
    contract_type_label: str = "Chính thức"
    si_base_override: Decimal | None
    si_enrolled: bool
    pit_enrolled: bool
    tax_dependent_count: int
    union_fee_override: Decimal | None
    status: str
    # Suy ra từ HĐ / ngày ký / đơn nghỉ — dùng lọc tab Thử việc · Thai sản · Chính thức
    effective_status: str | None = None
    status_label: str | None = None
    resign_date: date | None
    phone: str | None
    has_photo: bool = False
    photo_url: str | None = None
    # Tài khoản công nhân (login Worker)
    account_status: Literal["active", "locked", "resigned"] = "active"
    account_status_label: str = "Hoạt động"
    is_locked: bool = False
    failed_attempts: int = 0
    has_worker_account: bool = False
    # Có chế độ về sớm (Thai sản / Nuôi con) hiệu lực hôm nay — lọc tab «Chế độ đặc biệt»
    wt_regime_active: bool = False


class EmployeeRehireOut(BaseModel):
    employee: EmployeeOut
    rehire_mode: str
    message: str


class UnlockResetPasswordOut(BaseModel):
    detail: str
    employee_id: UUID
    employee_code: str
    new_password: str
    account_status: Literal["active", "locked", "resigned"]
    account_status_label: str


class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str]
    detail: str


class BulkSalaryRaiseRequest(BaseModel):
    """Tăng thành phần lương hàng loạt — cộng số tiền cố định."""

    scope: Literal["all", "department", "employees"]
    department_code: str | None = None
    employee_ids: list[UUID] | None = None
    target: Literal["contract_salary", "probation_salary", "allowance"] = "contract_salary"
    allowance_code: str | None = None
    amount: Decimal = Field(..., description="Số tiền tăng (VND), > 0")
    effective_from: date | None = None
    confirm: bool = False
    confirm_again: bool = False

    @field_validator("amount", mode="before")
    @classmethod
    def amount_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            raise ValueError("Trợ Lý AI: cần nhập số tiền tăng.")
        raw = str(v).strip().replace(" ", "").replace(",", "")
        # 300.000 / 1.200.000 → nghìn VN
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
            raw = raw.replace(".", "")
        return Decimal(raw)

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Trợ Lý AI: số tiền tăng phải > 0.")
        return v

    @field_validator("employee_ids")
    @classmethod
    def employees_non_empty(cls, v: list[UUID] | None, info) -> list[UUID] | None:  # noqa: ANN001
        scope = info.data.get("scope")
        if scope == "employees" and (not v or len(v) == 0):
            raise ValueError("Trợ Lý AI: chọn ít nhất một nhân viên.")
        return v


class BulkSalaryRaisePreview(BaseModel):
    scope: str
    department_code: str | None
    department_name: str | None
    target: str
    target_label: str
    allowance_code: str | None
    amount: Decimal
    affected_count: int
    message: str


class BulkSalaryRaiseResult(BaseModel):
    scope: str
    department_code: str | None
    target: str
    target_label: str
    allowance_code: str | None
    amount: Decimal
    affected_count: int
    message: str


class TransferTeamRequest(BaseModel):
    """Chuyển tổ hàng loạt từ lưới danh sách NV (23§145, hạng mục 1.5)."""

    employee_ids: list[UUID] = Field(min_length=1)
    team_id: UUID
    position_code: str | None = None
    effective_from: date
    decision_no: str | None = None
    reason_code: str | None = None
    confirm: bool = False

    @field_validator("effective_from")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError(
                "Trợ Lý AI: ngày hiệu lực không được ở tương lai — chưa hỗ trợ chuyển tổ "
                "theo lịch định trước."
            )
        return v


class TransferTeamSkipped(BaseModel):
    employee_code: str
    full_name: str
    reason: str


class TransferTeamPreview(BaseModel):
    team_id: UUID
    team_code: str
    team_name: str
    department_code: str | None = None
    effective_from: date
    total_selected: int
    affected_count: int
    skipped: list[TransferTeamSkipped]
    message: str


class TransferTeamResult(BaseModel):
    team_id: UUID
    team_code: str
    team_name: str
    effective_from: date
    affected_count: int
    skipped: list[TransferTeamSkipped]
    message: str


class EmployeeAssignmentOut(BaseModel):
    """Một dòng lịch sử đổi tổ / chức vụ của một NV (21§21.3)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    team_id: UUID
    team_code: str | None = None
    team_name: str | None = None
    position_code: str | None = None
    effective_from: date
    effective_to: date | None = None
    decision_no: str | None = None
    reason_code: str | None = None
    approved_by_name: str | None = None
    created_at: datetime | None = None


class EmployeeViolationCreate(BaseModel):
    occurred_at: datetime
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    penalty: str = ""


class EmployeeViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    occurred_at: datetime
    title: str
    description: str
    penalty: str
    has_attachment: bool = False
    attachment_url: str | None = None
    created_at: datetime | None = None


class EmployeeViolationBoardItem(BaseModel):
    employee_id: UUID
    employee_code: str
    full_name: str
    department_code: str | None = None
    status: str
    violation_count: int
    last_occurred_at: datetime | None = None


class EmployeeDocumentCreate(BaseModel):
    doc_type: str = Field(default="other", max_length=40)
    title: str = Field(min_length=1, max_length=200)
    note: str = ""


class EmployeeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    doc_type: str
    title: str
    note: str
    file_url: str
    created_at: datetime | None = None


# --- 5.2 labour_contracts ---

CONTRACT_TYPE_CODES = frozenset({"TV", "HD1", "HD2", "VTH"})
CONTRACT_STATUSES = frozenset({"draft", "active", "expired", "terminated"})


class LabourContractCreate(BaseModel):
    employee_id: UUID
    contract_type_code: str = Field(min_length=1, max_length=20)
    seq_no: int | None = None
    sign_date: date | None = None
    start_date: date
    end_date: date | None = None
    base_salary: Decimal = Decimal("0")
    position_code: str | None = None
    team_id: UUID | None = None
    status: str = "draft"
    file_path: str | None = None

    @field_validator("base_salary", mode="before")
    @classmethod
    def money_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return Decimal("0")
        return Decimal(str(v))

    @field_validator("contract_type_code")
    @classmethod
    def contract_type_ok(cls, v: str) -> str:
        up = v.strip().upper()
        if up not in CONTRACT_TYPE_CODES:
            raise ValueError(
                "Trợ Lý AI: contract_type_code phải là TV, HD1, HD2 hoặc VTH."
            )
        return up

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str) -> str:
        low = v.strip().lower()
        if low not in CONTRACT_STATUSES:
            raise ValueError("Trợ Lý AI: status HĐ phải là draft, active, expired hoặc terminated.")
        return low


class LabourContractUpdate(BaseModel):
    contract_type_code: str | None = None
    seq_no: int | None = None
    sign_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    base_salary: Decimal | None = None
    position_code: str | None = None
    team_id: UUID | None = None
    status: str | None = None
    file_path: str | None = None

    @field_validator("base_salary", mode="before")
    @classmethod
    def money_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return None
        return Decimal(str(v))

    @field_validator("contract_type_code")
    @classmethod
    def contract_type_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        up = v.strip().upper()
        if up not in CONTRACT_TYPE_CODES:
            raise ValueError(
                "Trợ Lý AI: contract_type_code phải là TV, HD1, HD2 hoặc VTH."
            )
        return up

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        low = v.strip().lower()
        if low not in CONTRACT_STATUSES:
            raise ValueError("Trợ Lý AI: status HĐ phải là draft, active, expired hoặc terminated.")
        return low


class LabourContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    contract_type_code: str
    contract_type_label: str = ""
    contract_no: str = ""
    times_label: str = ""
    seq_no: int
    sign_date: date | None
    start_date: date
    end_date: date | None
    base_salary: Decimal
    position_code: str | None
    team_id: UUID | None
    status: str
    file_path: str | None
    days_until_expiry: int | None = None
    created_at: datetime | None = None


class LabourContractRenewPreview(BaseModel):
    employee_id: UUID
    employee_code: str
    previous_contract_id: UUID | None
    previous_contract_type_code: str | None
    previous_contract_type_label: str | None
    suggested_contract_type_code: str
    suggested_contract_type_label: str
    suggested_seq_no: int
    suggested_contract_no: str
    suggested_start_date: date
    suggested_end_date: date | None
    suggested_sign_date: date
    suggested_base_salary: Decimal
    allowed_contract_type_codes: list[str]
    message: str


class LabourContractRenewRequest(BaseModel):
    employee_id: UUID
    contract_type_code: str | None = None
    sign_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    base_salary: Decimal | None = None

    @field_validator("base_salary", mode="before")
    @classmethod
    def money_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return None
        return Decimal(str(v))

    @field_validator("contract_type_code")
    @classmethod
    def contract_type_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        up = v.strip().upper()
        if up not in CONTRACT_TYPE_CODES:
            raise ValueError(
                "Trợ Lý AI: contract_type_code phải là TV, HD1, HD2 hoặc VTH."
            )
        return up


# --- 5.3 employee_family_members ---

RELATIONSHIP_CODES = frozenset({"cha", "me", "con", "chi", "anh", "khac"})


class EmployeeFamilyMemberCreate(BaseModel):
    relationship_code: str = Field(min_length=1, max_length=20)
    full_name: str = Field(min_length=1, max_length=200)
    birth_date: date | None = None
    id_number: str | None = None
    is_tax_dependent: bool = False
    dependent_from: date | None = None
    dependent_to: date | None = None

    @field_validator("relationship_code")
    @classmethod
    def relationship_ok(cls, v: str) -> str:
        low = v.strip().lower()
        if low not in RELATIONSHIP_CODES:
            raise ValueError(
                "Trợ Lý AI: relationship_code phải là cha, me, con, chi, anh hoặc khac."
            )
        return low


class EmployeeFamilyMemberUpdate(BaseModel):
    relationship_code: str | None = None
    full_name: str | None = None
    birth_date: date | None = None
    id_number: str | None = None
    is_tax_dependent: bool | None = None
    dependent_from: date | None = None
    dependent_to: date | None = None

    @field_validator("relationship_code")
    @classmethod
    def relationship_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        low = v.strip().lower()
        if low not in RELATIONSHIP_CODES:
            raise ValueError(
                "Trợ Lý AI: relationship_code phải là cha, me, con, chi, anh hoặc khac."
            )
        return low


class EmployeeFamilyMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    relationship_code: str
    full_name: str
    birth_date: date | None
    id_number: str | None
    is_tax_dependent: bool
    dependent_from: date | None
    dependent_to: date | None
    is_effective: bool = False
    created_at: datetime | None = None


class TaxDependentsOut(BaseModel):
    """Số người phụ thuộc hiệu lực — tính ra từ employee_family_members (22§22.10)."""

    employee_id: UUID
    as_of_date: date
    effective_count: int
    members: list[EmployeeFamilyMemberOut]


# --- 5.4 employee_resignations ---

RESIGN_TYPE_CODES = frozenset({"DPR", "AFL", "LWA", "CID", "DIS"})


class EmployeeResignationCreate(BaseModel):
    seq_no: int | None = None
    resign_type_code: str = Field(min_length=1, max_length=20)
    applied_date: date | None = None
    last_working_date: date
    reason: str | None = None
    severance_months: int = 0
    severance_amount: Decimal = Decimal("0")
    handover_done: bool = False
    rehired_at: date | None = None
    finalize: bool = False

    @field_validator("severance_amount", mode="before")
    @classmethod
    def money_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return Decimal("0")
        return Decimal(str(v))

    @field_validator("resign_type_code")
    @classmethod
    def resign_type_ok(cls, v: str) -> str:
        up = v.strip().upper()
        if up not in RESIGN_TYPE_CODES:
            raise ValueError(
                "Trợ Lý AI: resign_type_code phải là DPR, AFL, LWA, CID hoặc DIS."
            )
        return up


class EmployeeResignationUpdate(BaseModel):
    seq_no: int | None = None
    resign_type_code: str | None = None
    applied_date: date | None = None
    last_working_date: date | None = None
    reason: str | None = None
    severance_months: int | None = None
    severance_amount: Decimal | None = None
    handover_done: bool | None = None
    rehired_at: date | None = None

    @field_validator("severance_amount", mode="before")
    @classmethod
    def money_dec(cls, v):  # noqa: ANN001
        if v is None or v == "":
            return None
        return Decimal(str(v))

    @field_validator("resign_type_code")
    @classmethod
    def resign_type_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        up = v.strip().upper()
        if up not in RESIGN_TYPE_CODES:
            raise ValueError(
                "Trợ Lý AI: resign_type_code phải là DPR, AFL, LWA, CID hoặc DIS."
            )
        return up


class EmployeeResignationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    seq_no: int
    resign_type_code: str
    applied_date: date | None
    last_working_date: date
    reason: str | None
    severance_months: int
    severance_amount: Decimal
    handover_done: bool
    rehired_at: date | None
    rehire_mode: str | None = None
    rehire_reason: str | None = None
    created_at: datetime | None = None


class ResignationPreviewOut(BaseModel):
    employee_id: UUID
    employee_code: str
    full_name: str
    resign_type_code: str
    last_working_date: date
    tenure_years: int
    severance_months: int
    severance_amount: Decimal
    annual_leave_remaining: Decimal
    account_will_lock: bool = True


class HrMovementOut(BaseModel):
    """Một dòng biến động — hợp nhất assignment / lương / vi phạm (23§23.4)."""

    id: str
    movement_type: str
    occurred_at: datetime | date
    employee_id: UUID
    employee_code: str
    full_name: str
    summary: str
    value_before: str | None = None
    value_after: str | None = None
    decision_no: str | None = None
    approved_by_name: str | None = None


class EmployeeSalaryHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    field_code: str
    effective_from: date
    old_value: Decimal
    new_value: Decimal
    decision_no: str | None
    approved_by_name: str | None = None
    note: str | None
    created_at: datetime | None = None


# --- 5.1 employee profile subrecords ---


class EmployeeEducationCreate(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    school_name: str = Field(min_length=1, max_length=200)
    major: str | None = None
    degree_code: str | None = None
    note: str = ""


class EmployeeEducationUpdate(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    school_name: str | None = None
    major: str | None = None
    degree_code: str | None = None
    note: str | None = None


class EmployeeEducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    from_date: date | None
    to_date: date | None
    school_name: str
    major: str | None
    degree_code: str | None
    note: str
    created_at: datetime | None = None


RegimeType = Literal["PREGNANT", "CHILD"]


class EmployeeWtRegimeCreate(BaseModel):
    regime_type: RegimeType
    hours_early: int = Field(ge=1, le=3)
    date_from: date
    date_to: date
    note: str = ""


class EmployeeWtRegimeUpdate(BaseModel):
    """PATCH — chỉ sửa date_to, hours_early, note (giữ regime_type, date_from cũ)."""

    hours_early: int | None = Field(default=None, ge=1, le=3)
    date_to: date | None = None
    note: str | None = None


class EmployeeWtRegimeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    regime_type: str
    hours_early: int
    date_from: date
    date_to: date
    note: str
    created_at: datetime | None = None
    ended_at: datetime | None = None


class EmployeeExperienceCreate(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    company_name: str = Field(min_length=1, max_length=200)
    position_title: str | None = None
    note: str = ""


class EmployeeExperienceUpdate(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    company_name: str | None = None
    position_title: str | None = None
    note: str | None = None


class EmployeeExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    from_date: date | None
    to_date: date | None
    company_name: str
    position_title: str | None
    note: str
    created_at: datetime | None = None


class EmployeeHealthCheckCreate(BaseModel):
    check_date: date
    facility_name: str | None = None
    result_summary: str | None = None
    note: str = ""


class EmployeeHealthCheckUpdate(BaseModel):
    check_date: date | None = None
    facility_name: str | None = None
    result_summary: str | None = None
    note: str | None = None


class EmployeeHealthCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    check_date: date
    facility_name: str | None
    result_summary: str | None
    note: str
    created_at: datetime | None = None
