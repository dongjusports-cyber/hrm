"""API Payroll — calculate + publish/lock + export ATM/CASH + điều chỉnh + phụ cấp."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from app.core.deps import AdminUser, CurrentUser, DbSession, require_module
from app.modules.core.excel_filename import attachment_content_disposition
from app.modules.core.models import User
from app.modules.payroll import adjustments as adj_mod
from app.modules.payroll import employee_bonuses as bonus_mod
from app.modules.payroll import export_pay, import_allowances, publisher, service, simulate
from app.modules.payroll.ot_external import build_ot_external_summary
from app.modules.payroll.ot_external_schemas import OtExternalPayRowOut, OtExternalSummaryOut
from app.modules.payroll.adjustments import AdjustmentCreate, AdjustmentOut
from app.modules.payroll.import_allowances import (
    AllowanceAssignmentOut,
    AllowanceAssignmentUpsert,
    AllowanceImportResult,
    AllowanceTypeOut,
)
from app.modules.payroll.schemas import (
    CalculateResult,
    EmployeeBonusCreate,
    EmployeeBonusOut,
    HRPayslipDetailOut,
    PeriodActionResult,
    PeriodOut,
    PayslipComponentOut,
    PayslipOut,
    PolicyOptionOut,
    SimulateRequest,
    SimulateResult,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])

PayrollUser = Annotated[User, Depends(require_module("payroll"))]


def require_hr_or_payroll(user: CurrentUser) -> User:
    if user.role == "admin" or user.has_module("hr") or user.has_module("payroll"):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Trợ Lý AI: cần quyền Nhân Sự hoặc Tính Lương để quản lý phụ cấp.",
    )


HrOrPayroll = Annotated[User, Depends(require_hr_or_payroll)]


@router.get("/periods/{period}", response_model=PeriodOut)
def get_period(period: str, _user: PayrollUser, db: DbSession) -> PeriodOut:
    return publisher.get_period(db, period)


@router.post("/periods/{period}/calculate", response_model=CalculateResult)
def calculate_period(period: str, user: PayrollUser, db: DbSession) -> CalculateResult:
    """period = YYYY-MM (vd 2025-10)."""
    return service.calculate_period(db, period, actor=user)


@router.post("/periods/{period}/publish", response_model=PeriodActionResult)
def publish_period(period: str, user: PayrollUser, db: DbSession) -> PeriodActionResult:
    return publisher.publish_period(db, period, actor=user)


@router.post("/periods/{period}/lock", response_model=PeriodActionResult)
def lock_period(period: str, user: PayrollUser, db: DbSession) -> PeriodActionResult:
    return publisher.lock_period(db, period, actor=user)


@router.post("/periods/{period}/unlock", response_model=PeriodActionResult)
def unlock_period(period: str, admin: AdminUser, db: DbSession) -> PeriodActionResult:
    """Chỉ Admin — mở khóa kỳ đã khóa (audit hộp đen)."""
    return publisher.unlock_period(db, period, actor=admin)


@router.post("/periods/{period}/reopen", response_model=PeriodActionResult)
def reopen_period(period: str, admin: AdminUser, db: DbSession) -> PeriodActionResult:
    """Chỉ Admin — mở lại kỳ published/locked để tính lương (giữ phiếu confirmed)."""
    return publisher.reopen_period(db, period, actor=admin)


@router.get("/payslips", response_model=list[PayslipOut])
def payslips(
    _user: PayrollUser,
    db: DbSession,
    period: Annotated[str, Query(description="YYYY-MM")],
) -> list[PayslipOut]:
    return service.list_payslips(db, period)


@router.get("/payslips/{payslip_id}", response_model=PayslipOut)
def payslip_detail(payslip_id: UUID, _user: PayrollUser, db: DbSession) -> PayslipOut:
    return publisher.get_payslip(db, payslip_id)


@router.get("/payslips/{payslip_id}/detail", response_model=HRPayslipDetailOut)
def payslip_hr_detail(payslip_id: UUID, _user: PayrollUser, db: DbSession) -> HRPayslipDetailOut:
    """Phiếu lương HR — 3 khối components + số dư phép (4.9)."""
    return service.get_hr_payslip(db, payslip_id)


@router.get("/payslips/{payslip_id}/components", response_model=list[PayslipComponentOut])
def payslip_components(
    payslip_id: UUID, _user: PayrollUser, db: DbSession
) -> list[PayslipComponentOut]:
    """Chi tiết từng khoản trên phiếu — hạng mục 4.1."""
    return service.get_payslip_components(db, payslip_id)


@router.get("/periods/{period}/export")
def export_payroll(
    period: str,
    user: PayrollUser,
    db: DbSession,
    channel: Annotated[str, Query(description="ATM | CASH | ALL")] = "ALL",
    department_id: Annotated[
        UUID | None, Query(description="Lọc theo bộ phận (vd Main Office)")
    ] = None,
    employee_code: Annotated[
        str | None, Query(description="Lọc 1 MSNV — chỉ xuất phiếu lương nhân viên đó")
    ] = None,
) -> Response:
    """Xuất bảng lương Excel theo mẫu GenusSuite — ghi audit log."""
    data, filename = export_pay.export_payroll_channel(
        db,
        user,
        period,
        channel,
        department_id=department_id,
        employee_code=employee_code,
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": attachment_content_disposition(filename)},
    )


@router.get("/periods/{period}/ot-external-preview", response_model=OtExternalSummaryOut)
def ot_external_preview(period: str, _user: PayrollUser, db: DbSession) -> OtExternalSummaryOut:
    """Xem trước OT ngoài + tiền (22§22.8) — không ghi payslip chính."""
    summary = build_ot_external_summary(db, period)
    return OtExternalSummaryOut(
        period=summary.period,
        employee_count=summary.employee_count,
        total_raw_hours=summary.total_raw_hours,
        total_effective_hours=summary.total_effective_hours,
        total_amount_vnd=summary.total_amount_vnd,
        policy_note=summary.policy_note,
        rows=[OtExternalPayRowOut.model_validate(r, from_attributes=True) for r in summary.rows],
    )


@router.get("/periods/{period}/export-ot-external")
def export_ot_external_payroll(period: str, user: PayrollUser, db: DbSession) -> Response:
    """Excel OT ngoài có tiền — chi ATM riêng, tách audit lương chính."""
    from app.modules.payroll.ot_external import export_ot_external

    data, filename = export_ot_external(db, period, user)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": attachment_content_disposition(filename)},
    )


@router.get("/adjustments", response_model=list[AdjustmentOut])
def list_pay_adjustments(
    _user: PayrollUser,
    db: DbSession,
    period: Annotated[str, Query()],
    employee_code: str | None = None,
) -> list[AdjustmentOut]:
    return adj_mod.list_adjustments(db, period, employee_code=employee_code)


@router.post("/adjustments", response_model=AdjustmentOut)
def create_pay_adjustment(
    body: AdjustmentCreate,
    user: PayrollUser,
    db: DbSession,
) -> AdjustmentOut:
    return adj_mod.create_adjustment(db, body, user)


@router.delete("/adjustments/{adjustment_id}")
def delete_pay_adjustment(
    adjustment_id: UUID,
    user: PayrollUser,
    db: DbSession,
) -> dict:
    return adj_mod.delete_adjustment(db, adjustment_id, user)


@router.get("/allowances/types", response_model=list[AllowanceTypeOut])
def allowance_types(
    _user: HrOrPayroll,
    db: DbSession,
    assignable: bool = Query(default=False),
) -> list[AllowanceTypeOut]:
    return import_allowances.list_allowance_types(db, assignable=assignable)


@router.get("/allowances", response_model=list[AllowanceAssignmentOut])
def allowance_assignments(
    _user: HrOrPayroll,
    db: DbSession,
    employee_code: str | None = None,
) -> list[AllowanceAssignmentOut]:
    return import_allowances.list_assignments(db, employee_code=employee_code)


@router.post("/allowances/assignments", response_model=AllowanceAssignmentOut, status_code=201)
def upsert_allowance_assignment(
    body: AllowanceAssignmentUpsert,
    user: HrOrPayroll,
    db: DbSession,
) -> AllowanceAssignmentOut:
    return import_allowances.upsert_assignment(db, body, actor=user)


@router.delete("/allowances/assignments/{assignment_id}")
def delete_allowance_assignment(
    assignment_id: UUID,
    user: HrOrPayroll,
    db: DbSession,
) -> dict[str, str]:
    return import_allowances.delete_assignment(db, assignment_id, actor=user)


@router.post("/allowances/import", response_model=AllowanceImportResult)
async def import_allowances_excel(
    user: HrOrPayroll,
    db: DbSession,
    file: UploadFile = File(...),
) -> AllowanceImportResult:
    """Import phụ cấp Excel (rộng hoặc dài) — Go-live 10.9."""
    content = await file.read()
    return import_allowances.import_allowances_xlsx(
        db,
        content,
        file.filename or "allowances.xlsx",
        actor=user,
    )


@router.get("/bonuses", response_model=list[EmployeeBonusOut])
def list_employee_bonuses(
    _user: HrOrPayroll,
    db: DbSession,
    period: Annotated[str | None, Query(description="YYYY-MM")] = None,
    employee_code: str | None = None,
) -> list[EmployeeBonusOut]:
    return bonus_mod.list_bonuses(db, period=period, employee_code=employee_code)


@router.post("/bonuses", response_model=EmployeeBonusOut, status_code=201)
def create_employee_bonus(
    body: EmployeeBonusCreate,
    user: HrOrPayroll,
    db: DbSession,
) -> EmployeeBonusOut:
    return bonus_mod.create_bonus(
        db,
        employee_code=body.employee_code,
        bonus_year=body.bonus_year,
        seq_times=body.seq_times,
        bonus_amount=body.bonus_amount,
        period=body.period,
        bonus_code=body.bonus_code,
        base_salary=body.base_salary,
        bonus_rate=body.bonus_rate,
        reason=body.reason,
        actor=user,
    )


@router.delete("/bonuses/{bonus_id}")
def delete_employee_bonus(
    bonus_id: UUID,
    user: HrOrPayroll,
    db: DbSession,
) -> dict[str, str]:
    return bonus_mod.delete_bonus(db, bonus_id, actor=user)


@router.get("/simulate/policy-options", response_model=list[PolicyOptionOut])
def simulate_policy_options(_user: PayrollUser, db: DbSession) -> list[PolicyOptionOut]:
    """Danh sách gói chính sách cho dropdown Chạy thử (4.10)."""
    return simulate.list_policy_options(db)


@router.post("/simulate", response_model=SimulateResult)
def run_simulate(body: SimulateRequest, _user: PayrollUser, db: DbSession) -> SimulateResult:
    """Mô phỏng lương — không ghi CSDL."""
    return simulate.simulate_period(db, body)
