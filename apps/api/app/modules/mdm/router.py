"""API MDM — employees + departments (file 08)."""

from typing import Annotated
from uuid import UUID

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.deps import AdminUser, DbSession, require_module
from app.modules.core.models import User
from app.modules.mdm import service
from app.modules.mdm.export_employees import export_employees_channel
from app.modules.mdm.import_excel import import_employees_xlsx
from app.modules.mdm.schemas import (
    BulkSalaryRaisePreview,
    BulkSalaryRaiseRequest,
    BulkSalaryRaiseResult,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    EmployeeAssignmentOut,
    EmployeeCreate,
    EmployeeDocumentCreate,
    EmployeeDocumentOut,
    EmployeeEducationCreate,
    EmployeeEducationOut,
    EmployeeEducationUpdate,
    EmployeeExperienceCreate,
    EmployeeExperienceOut,
    EmployeeExperienceUpdate,
    EmployeeFamilyMemberCreate,
    EmployeeHealthCheckCreate,
    EmployeeHealthCheckOut,
    EmployeeHealthCheckUpdate,
    EmployeeFamilyMemberOut,
    EmployeeFamilyMemberUpdate,
    EmployeeOut,
    EmployeeResignationCreate,
    EmployeeResignationOut,
    EmployeeResignationUpdate,
    EmployeeSalaryHistoryOut,
    EmployeeUpdate,
    EmployeeViolationBoardItem,
    EmployeeViolationCreate,
    EmployeeViolationOut,
    HrMovementOut,
    ImportResult,
    LabourContractCreate,
    LabourContractOut,
    LabourContractRenewPreview,
    LabourContractRenewRequest,
    LabourContractUpdate,
    LookupValueOut,
    ResignationPreviewOut,
    TaxDependentsOut,
    TeamOut,
    TransferTeamPreview,
    TransferTeamRequest,
    TransferTeamResult,
    UnlockResetPasswordOut,
)

router = APIRouter(tags=["mdm"])

HrUser = Annotated[User, Depends(require_module("hr"))]


@router.get("/departments", response_model=list[DepartmentOut])
def get_departments(_user: HrUser, db: DbSession) -> list[DepartmentOut]:
    """HR được xem danh mục để gán NV; CRUD chỉ Admin."""
    return service.list_departments(db)


@router.post("/departments", response_model=DepartmentOut, status_code=201)
def post_department(body: DepartmentCreate, _admin: AdminUser, db: DbSession) -> DepartmentOut:
    return service.create_department(db, body)


@router.put("/departments/{dept_id}", response_model=DepartmentOut)
def put_department(
    dept_id: UUID, body: DepartmentUpdate, _admin: AdminUser, db: DbSession
) -> DepartmentOut:
    return service.update_department(db, dept_id, body)


@router.delete("/departments/{dept_id}")
def delete_department(dept_id: UUID, _admin: AdminUser, db: DbSession) -> dict[str, str]:
    return service.delete_department(db, dept_id)


@router.get("/teams", response_model=list[TeamOut])
def get_teams(
    _user: HrUser,
    db: DbSession,
    active_only: bool = Query(default=True),
) -> list[TeamOut]:
    """Danh mục Tổ cho bộ lọc 'Bộ phận › Tổ' của lưới nhân sự (hạng mục 1.4)."""
    return service.list_teams(db, active_only=active_only)


@router.get("/lookup-values", response_model=list[LookupValueOut])
def get_lookup_values(
    _user: HrUser, db: DbSession, group_code: str | None = Query(default=None)
) -> list[LookupValueOut]:
    """Danh mục phẳng — dân tộc, tôn giáo, quốc tịch, nơi sinh, nơi cấp CCCD, trình độ (21§21.4,
    hạng mục 2.1). Sửa/thêm dòng qua màn Admin › Danh mục (hạng mục 2.8), chưa làm ở đây."""
    return service.list_lookup_values(db, group_code=group_code)


@router.get("/lookup-groups", response_model=list[str])
def get_lookup_groups(_user: HrUser, db: DbSession) -> list[str]:
    """Liệt kê group_code hiện có trong lookup_values — cho màn Admin biết có bao nhiêu danh mục."""
    return service.list_lookup_groups(db)


@router.get("/employees", response_model=list[EmployeeOut])
def get_employees(
    _user: HrUser,
    db: DbSession,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    team_id: UUID | None = Query(default=None),
) -> list[EmployeeOut]:
    return service.list_employees(
        db, q=q, status=status, department_id=department_id, team_id=team_id
    )


@router.get("/employees/export")
def export_employees(
    user: HrUser,
    db: DbSession,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    team_id: UUID | None = Query(default=None),
    columns: str | None = Query(default=None, description="CSV các khoá cột, ví dụ employee_code,full_name"),
) -> Response:
    """Xuất Excel danh sách NV — đúng cột đang hiện, đúng bộ lọc đang bật (23§ Xuất Excel)."""
    data, filename = export_employees_channel(
        db,
        user,
        q=q,
        status=status,
        department_id=department_id,
        team_id=team_id,
        columns=columns,
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def post_employee(body: EmployeeCreate, _user: HrUser, db: DbSession) -> EmployeeOut:
    return service.create_employee(db, body)


@router.post("/employees/import", response_model=ImportResult)
async def import_employees(
    _user: HrUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> ImportResult:
    content = await file.read()
    return import_employees_xlsx(db, content, file.filename or "import.xlsx")


@router.post("/employees/salary-raise/preview", response_model=BulkSalaryRaisePreview)
def preview_salary_raise(
    body: BulkSalaryRaiseRequest, _user: HrUser, db: DbSession
) -> BulkSalaryRaisePreview:
    return service.preview_salary_raise(db, body)


@router.post("/employees/salary-raise", response_model=BulkSalaryRaiseResult)
def apply_salary_raise(
    body: BulkSalaryRaiseRequest, user: HrUser, db: DbSession
) -> BulkSalaryRaiseResult:
    return service.apply_salary_raise(db, body, user)


@router.get("/employees/violation-board", response_model=list[EmployeeViolationBoardItem])
def get_violation_board(_user: HrUser, db: DbSession) -> list[EmployeeViolationBoardItem]:
    return service.list_violation_board(db)


@router.post("/employees/transfer-team/preview", response_model=TransferTeamPreview)
def preview_transfer_team(
    body: TransferTeamRequest, _user: HrUser, db: DbSession
) -> TransferTeamPreview:
    """Xem trước chuyển tổ hàng loạt từ lưới NV (23§145, hạng mục 1.5) — luôn xem trước."""
    return service.preview_transfer_team(db, body)


@router.post("/employees/transfer-team", response_model=TransferTeamResult)
def apply_transfer_team(
    body: TransferTeamRequest, user: HrUser, db: DbSession
) -> TransferTeamResult:
    """Chuyển tổ hàng loạt — ghi employee_assignments, 1 giao dịch (20§N4)."""
    return service.apply_transfer_team(db, body, user)


@router.get("/employees/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: UUID, _user: HrUser, db: DbSession) -> EmployeeOut:
    return service.get_employee(db, emp_id)


@router.put("/employees/{emp_id}", response_model=EmployeeOut)
def put_employee(
    emp_id: UUID, body: EmployeeUpdate, _user: HrUser, db: DbSession
) -> EmployeeOut:
    return service.update_employee(db, emp_id, body)


@router.post(
    "/employees/{emp_id}/unlock-reset-password",
    response_model=UnlockResetPasswordOut,
)
def post_unlock_reset_password(
    emp_id: UUID, user: HrUser, db: DbSession
) -> UnlockResetPasswordOut:
    """HR: mở khóa tài khoản công nhân + reset mật khẩu Worker + 4 số cuối CCCD."""
    return service.unlock_and_reset_worker_password(db, emp_id, user)


@router.post("/employees/{emp_id}/photo", response_model=EmployeeOut)
async def post_employee_photo(
    emp_id: UUID,
    _user: HrUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> EmployeeOut:
    content = await file.read()
    return service.upload_employee_photo(
        db,
        emp_id,
        content=content,
        content_type=file.content_type,
        filename=file.filename,
    )


@router.get("/employees/{emp_id}/photo")
def get_employee_photo(emp_id: UUID, _user: HrUser, db: DbSession) -> FileResponse:
    path, media_type = service.resolve_employee_photo_file(db, emp_id)
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/employees/{emp_id}/assignments", response_model=list[EmployeeAssignmentOut])
def get_employee_assignments(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeAssignmentOut]:
    """Lịch sử đổi tổ / chức vụ của một NV (21§21.3, hạng mục 1.5)."""
    return service.list_employee_assignments(db, emp_id)


@router.get("/employees/{emp_id}/salary-history", response_model=list[EmployeeSalaryHistoryOut])
def get_employee_salary_history(
    emp_id: UUID, _user: HrUser, db: DbSession
) -> list[EmployeeSalaryHistoryOut]:
    """Lịch sử thay đổi lương của một NV (21§21.3)."""
    return service.list_employee_salary_history(db, emp_id)


@router.get("/employees/{emp_id}/violations", response_model=list[EmployeeViolationOut])
def get_employee_violations(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeViolationOut]:
    return service.list_violations(db, emp_id)


@router.post("/employees/{emp_id}/violations", response_model=EmployeeViolationOut, status_code=201)
async def post_employee_violation(
    emp_id: UUID,
    user: HrUser,
    db: DbSession,
    occurred_at: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    penalty: str = Form(""),
    file: UploadFile | None = File(None),
) -> EmployeeViolationOut:
    try:
        when = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: thời gian vi phạm không hợp lệ.",
        ) from exc
    content = await file.read() if file is not None else None
    return service.create_violation(
        db,
        emp_id,
        EmployeeViolationCreate(
            occurred_at=when,
            title=title,
            description=description,
            penalty=penalty,
        ),
        actor=user,
        file_content=content if content else None,
        content_type=file.content_type if file else None,
        filename=file.filename if file else None,
    )


@router.get("/employees/{emp_id}/violations/{violation_id}/attachment")
def get_violation_attachment(
    emp_id: UUID, violation_id: UUID, _user: HrUser, db: DbSession
) -> FileResponse:
    path, media_type = service.resolve_violation_attachment(db, emp_id, violation_id)
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.delete("/employees/{emp_id}/violations/{violation_id}")
def delete_employee_violation(
    emp_id: UUID, violation_id: UUID, user: HrUser, db: DbSession
) -> dict[str, str]:
    return service.delete_violation(db, emp_id, violation_id, actor=user)


@router.get("/employees/{emp_id}/documents", response_model=list[EmployeeDocumentOut])
def get_employee_documents(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeDocumentOut]:
    return service.list_documents(db, emp_id)


@router.post("/employees/{emp_id}/documents", response_model=EmployeeDocumentOut, status_code=201)
async def post_employee_document(
    emp_id: UUID,
    user: HrUser,
    db: DbSession,
    title: str = Form(...),
    doc_type: str = Form("other"),
    note: str = Form(""),
    file: UploadFile = File(...),
) -> EmployeeDocumentOut:
    content = await file.read()
    return service.create_document(
        db,
        emp_id,
        EmployeeDocumentCreate(title=title, doc_type=doc_type, note=note),
        actor=user,
        file_content=content,
        content_type=file.content_type,
        filename=file.filename,
    )


@router.get("/employees/{emp_id}/documents/{document_id}/file")
def get_document_file(
    emp_id: UUID, document_id: UUID, _user: HrUser, db: DbSession
) -> FileResponse:
    path, media_type = service.resolve_document_file(db, emp_id, document_id)
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.delete("/employees/{emp_id}/documents/{document_id}")
def delete_employee_document(
    emp_id: UUID, document_id: UUID, user: HrUser, db: DbSession
) -> dict[str, str]:
    return service.delete_document(db, emp_id, document_id, actor=user)


# --- 5.2 labour_contracts ---


@router.get("/labour-contracts", response_model=list[LabourContractOut])
def get_labour_contracts(
    _user: HrUser,
    db: DbSession,
    employee_id: UUID | None = Query(default=None),
    expiring_within_days: int | None = Query(default=None, ge=1, le=365),
) -> list[LabourContractOut]:
    """Danh sách HĐ — lọc theo NV hoặc HĐ sắp hết hạn (mặc định cảnh báo 60 ngày khi truyền param)."""
    return service.list_labour_contracts(
        db, employee_id=employee_id, expiring_within_days=expiring_within_days
    )


@router.get("/labour-contracts/expiring", response_model=list[LabourContractOut])
def get_expiring_labour_contracts(
    _user: HrUser,
    db: DbSession,
    within_days: int = Query(default=60, ge=1, le=365),
) -> list[LabourContractOut]:
    """HĐ active sắp hết hạn trong N ngày (mặc định 60 — hạng mục 5.2)."""
    return service.list_labour_contracts(db, expiring_within_days=within_days)


@router.post("/labour-contracts", response_model=LabourContractOut, status_code=201)
def post_labour_contract(body: LabourContractCreate, _user: HrUser, db: DbSession) -> LabourContractOut:
    return service.create_labour_contract(db, body)


@router.get(
    "/labour-contracts/renew-preview",
    response_model=LabourContractRenewPreview,
)
def get_labour_contract_renew_preview(
    _user: HrUser,
    db: DbSession,
    employee_id: UUID = Query(...),
) -> LabourContractRenewPreview:
    """Gợi ý loại HĐ tiếp theo (TV→HD1→HD2/VTH) theo GenusSuite."""
    return service.preview_renew_labour_contract(db, employee_id)


@router.post(
    "/labour-contracts/renew",
    response_model=LabourContractOut,
    status_code=201,
)
def post_labour_contract_renew(
    body: LabourContractRenewRequest, _user: HrUser, db: DbSession
) -> LabourContractOut:
    """Ký HĐ tiếp — tự điền seq_no, ngày bắt đầu sau HĐ cũ."""
    return service.renew_labour_contract(db, body)


@router.get("/labour-contracts/{contract_id}", response_model=LabourContractOut)
def get_labour_contract(contract_id: UUID, _user: HrUser, db: DbSession) -> LabourContractOut:
    return service.get_labour_contract(db, contract_id)


@router.put("/labour-contracts/{contract_id}", response_model=LabourContractOut)
def put_labour_contract(
    contract_id: UUID, body: LabourContractUpdate, _user: HrUser, db: DbSession
) -> LabourContractOut:
    return service.update_labour_contract(db, contract_id, body)


@router.delete("/labour-contracts/{contract_id}")
def delete_labour_contract(contract_id: UUID, _user: HrUser, db: DbSession) -> dict[str, str]:
    return service.delete_labour_contract(db, contract_id)


# --- 5.3 employee_family_members ---


@router.get("/employees/{emp_id}/family-members", response_model=list[EmployeeFamilyMemberOut])
def get_family_members(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeFamilyMemberOut]:
    return service.list_family_members(db, emp_id)


@router.get("/employees/{emp_id}/tax-dependents", response_model=TaxDependentsOut)
def get_tax_dependents(
    emp_id: UUID,
    _user: HrUser,
    db: DbSession,
    as_of: date | None = Query(default=None),
) -> TaxDependentsOut:
    """Số người phụ thuộc hiệu lực — tính ra từ employee_family_members (22§22.10)."""
    return service.compute_tax_dependents(db, emp_id, as_of=as_of)


@router.post(
    "/employees/{emp_id}/family-members",
    response_model=EmployeeFamilyMemberOut,
    status_code=201,
)
def post_family_member(
    emp_id: UUID, body: EmployeeFamilyMemberCreate, _user: HrUser, db: DbSession
) -> EmployeeFamilyMemberOut:
    return service.create_family_member(db, emp_id, body)


@router.put(
    "/employees/{emp_id}/family-members/{member_id}",
    response_model=EmployeeFamilyMemberOut,
)
def put_family_member(
    emp_id: UUID,
    member_id: UUID,
    body: EmployeeFamilyMemberUpdate,
    _user: HrUser,
    db: DbSession,
) -> EmployeeFamilyMemberOut:
    return service.update_family_member(db, emp_id, member_id, body)


@router.delete("/employees/{emp_id}/family-members/{member_id}")
def delete_family_member(
    emp_id: UUID, member_id: UUID, _user: HrUser, db: DbSession
) -> dict[str, str]:
    return service.delete_family_member(db, emp_id, member_id)


# --- 5.4 employee_resignations ---


@router.get("/employees/{emp_id}/resignations", response_model=list[EmployeeResignationOut])
def get_resignations(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeResignationOut]:
    return service.list_resignations(db, emp_id)


@router.get("/employees/{emp_id}/resignation-preview", response_model=ResignationPreviewOut)
def get_resignation_preview(
    emp_id: UUID,
    _user: HrUser,
    db: DbSession,
    resign_type_code: str = Query(min_length=1),
    last_working_date: date = Query(),
) -> ResignationPreviewOut:
    return service.preview_resignation(
        db,
        emp_id,
        resign_type_code=resign_type_code,
        last_working_date=last_working_date,
    )


@router.get("/hr/movements", response_model=list[HrMovementOut])
def get_hr_movements(
    _user: HrUser,
    db: DbSession,
    employee_id: UUID | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=500),
) -> list[HrMovementOut]:
    return service.list_hr_movements(db, employee_id=employee_id, limit=limit)


@router.post(
    "/employees/{emp_id}/resignations",
    response_model=EmployeeResignationOut,
    status_code=201,
)
def post_resignation(
    emp_id: UUID, body: EmployeeResignationCreate, _user: HrUser, db: DbSession
) -> EmployeeResignationOut:
    return service.create_resignation(db, emp_id, body)


@router.put(
    "/employees/{emp_id}/resignations/{resignation_id}",
    response_model=EmployeeResignationOut,
)
def put_resignation(
    emp_id: UUID,
    resignation_id: UUID,
    body: EmployeeResignationUpdate,
    _user: HrUser,
    db: DbSession,
) -> EmployeeResignationOut:
    return service.update_resignation(db, emp_id, resignation_id, body)


@router.delete("/employees/{emp_id}/resignations/{resignation_id}")
def delete_resignation(
    emp_id: UUID, resignation_id: UUID, _user: HrUser, db: DbSession
) -> dict[str, str]:
    return service.delete_resignation(db, emp_id, resignation_id)


# --- 5.1 employee profile subrecords ---


@router.get("/employees/{emp_id}/educations", response_model=list[EmployeeEducationOut])
def get_educations(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeEducationOut]:
    return service.list_educations(db, emp_id)


@router.post(
    "/employees/{emp_id}/educations",
    response_model=EmployeeEducationOut,
    status_code=201,
)
def post_education(
    emp_id: UUID, body: EmployeeEducationCreate, _user: HrUser, db: DbSession
) -> EmployeeEducationOut:
    return service.create_education(db, emp_id, body)


@router.put(
    "/employees/{emp_id}/educations/{row_id}",
    response_model=EmployeeEducationOut,
)
def put_education(
    emp_id: UUID,
    row_id: UUID,
    body: EmployeeEducationUpdate,
    _user: HrUser,
    db: DbSession,
) -> EmployeeEducationOut:
    return service.update_education(db, emp_id, row_id, body)


@router.delete("/employees/{emp_id}/educations/{row_id}")
def delete_education(
    emp_id: UUID, row_id: UUID, _user: HrUser, db: DbSession
) -> dict[str, str]:
    return service.delete_education(db, emp_id, row_id)


@router.get("/employees/{emp_id}/experiences", response_model=list[EmployeeExperienceOut])
def get_experiences(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeExperienceOut]:
    return service.list_experiences(db, emp_id)


@router.post(
    "/employees/{emp_id}/experiences",
    response_model=EmployeeExperienceOut,
    status_code=201,
)
def post_experience(
    emp_id: UUID, body: EmployeeExperienceCreate, _user: HrUser, db: DbSession
) -> EmployeeExperienceOut:
    return service.create_experience(db, emp_id, body)


@router.put(
    "/employees/{emp_id}/experiences/{row_id}",
    response_model=EmployeeExperienceOut,
)
def put_experience(
    emp_id: UUID,
    row_id: UUID,
    body: EmployeeExperienceUpdate,
    _user: HrUser,
    db: DbSession,
) -> EmployeeExperienceOut:
    return service.update_experience(db, emp_id, row_id, body)


@router.delete("/employees/{emp_id}/experiences/{row_id}")
def delete_experience(
    emp_id: UUID, row_id: UUID, _user: HrUser, db: DbSession
) -> dict[str, str]:
    return service.delete_experience(db, emp_id, row_id)


@router.get("/employees/{emp_id}/health-checks", response_model=list[EmployeeHealthCheckOut])
def get_health_checks(emp_id: UUID, _user: HrUser, db: DbSession) -> list[EmployeeHealthCheckOut]:
    return service.list_health_checks(db, emp_id)


@router.post(
    "/employees/{emp_id}/health-checks",
    response_model=EmployeeHealthCheckOut,
    status_code=201,
)
def post_health_check(
    emp_id: UUID, body: EmployeeHealthCheckCreate, _user: HrUser, db: DbSession
) -> EmployeeHealthCheckOut:
    return service.create_health_check(db, emp_id, body)


@router.put(
    "/employees/{emp_id}/health-checks/{row_id}",
    response_model=EmployeeHealthCheckOut,
)
def put_health_check(
    emp_id: UUID,
    row_id: UUID,
    body: EmployeeHealthCheckUpdate,
    _user: HrUser,
    db: DbSession,
) -> EmployeeHealthCheckOut:
    return service.update_health_check(db, emp_id, row_id, body)


@router.delete("/employees/{emp_id}/health-checks/{row_id}")
def delete_health_check(
    emp_id: UUID, row_id: UUID, _user: HrUser, db: DbSession
) -> dict[str, str]:
    return service.delete_health_check(db, emp_id, row_id)
