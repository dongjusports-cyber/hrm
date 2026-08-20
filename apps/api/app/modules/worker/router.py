"""API Worker Portal — /api/worker/* (file 08). Không AI."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentWorker, DbSession, WorkerPasswordOk
from app.modules.attendance.schemas import LeaveRequestCreate, LeaveRequestOut, LeaveTypeOut
from app.modules.dispute import service as dispute_svc
from app.modules.dispute.schemas import DisputeCreateRequest, DisputeOut, DisputeReasonOut
from app.modules.worker import payslips as payslip_svc
from app.modules.worker import service as worker_service
from app.modules.config.mobile_punch import WorkerPunchIn, WorkerPunchOut, create_worker_punch
from app.modules.worker.schemas import (
    MessageOut,
    WorkerAttendanceMonthOut,
    WorkerChangePasswordRequest,
    WorkerLeaveBalanceOut,
    WorkerLoginRequest,
    WorkerOut,
    WorkerPayslipDetailOut,
    WorkerPayslipListOut,
    WorkerTokenResponse,
)

router = APIRouter(prefix="/worker", tags=["worker"])


@router.post("/login", response_model=WorkerTokenResponse)
def worker_login(body: WorkerLoginRequest, db: DbSession) -> WorkerTokenResponse:
    return worker_service.authenticate_worker(
        db, body.employee_code, body.password, body.device_id
    )


@router.get("/me", response_model=WorkerOut)
def worker_me(worker: CurrentWorker, db: DbSession) -> WorkerOut:
    return worker_service.worker_to_out(db, worker)


@router.post("/change-password", response_model=MessageOut)
def worker_change_password(
    body: WorkerChangePasswordRequest, db: DbSession, worker: CurrentWorker
) -> MessageOut:
    worker_service.change_worker_password(db, worker, body.current_password, body.new_password)
    return MessageOut(
        detail=f"Trợ Lý AI xin chào {worker.full_name}, đã đổi mật khẩu thành công."
    )


@router.get("/payslips", response_model=list[WorkerPayslipListOut])
def worker_payslips(worker: WorkerPasswordOk, db: DbSession) -> list[WorkerPayslipListOut]:
    return payslip_svc.list_worker_payslips(db, worker)


@router.get("/payslips/{payslip_id}", response_model=WorkerPayslipDetailOut)
def worker_payslip_detail(
    payslip_id: UUID, worker: WorkerPasswordOk, db: DbSession
) -> WorkerPayslipDetailOut:
    return payslip_svc.get_worker_payslip(db, worker, payslip_id)


@router.post("/payslips/{payslip_id}/confirm", response_model=WorkerPayslipDetailOut)
def worker_payslip_confirm(
    payslip_id: UUID, worker: WorkerPasswordOk, db: DbSession
) -> WorkerPayslipDetailOut:
    """P4.2 — xác nhận đúng → khóa phiếu (không khiếu nại)."""
    return payslip_svc.confirm_worker_payslip(db, worker, payslip_id)


@router.get("/dispute-reasons", response_model=list[DisputeReasonOut])
def worker_dispute_reasons(_worker: CurrentWorker) -> list[DisputeReasonOut]:
    """Danh sách lý do khiếu nại (P4.3) — không AI."""
    return dispute_svc.list_reasons()


@router.post("/payslips/{payslip_id}/dispute", response_model=DisputeOut)
def worker_payslip_dispute(
    payslip_id: UUID,
    body: DisputeCreateRequest,
    worker: WorkerPasswordOk,
    db: DbSession,
) -> DisputeOut:
    """P4.3 — gửi khiếu nại → ticket + badge nhắc HR."""
    return dispute_svc.create_worker_dispute(db, worker, payslip_id, body)


@router.get("/leave-balance", response_model=WorkerLeaveBalanceOut)
def worker_leave_balance(worker: CurrentWorker, db: DbSession) -> WorkerLeaveBalanceOut:
    """Số dư phép năm — chỉ xem, không ghi sổ."""
    from app.modules.worker import self_service

    return self_service.get_leave_balance(db, worker)


@router.get("/leave-types", response_model=list[LeaveTypeOut])
def worker_leave_types(_worker: CurrentWorker, db: DbSession) -> list[LeaveTypeOut]:
    from app.modules.attendance import timesheet as ts

    return ts.list_leave_types(db)


@router.get("/leave-requests", response_model=list[LeaveRequestOut])
def worker_leave_requests(worker: CurrentWorker, db: DbSession) -> list[LeaveRequestOut]:
    from app.modules.attendance import leave_requests as lr

    emp = worker_service._employee_for_user(db, worker)
    if emp is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy hồ sơ nhân viên.")
    rows = lr.list_leave_requests(db, employee_id=emp.id, include_balance=True)
    return [LeaveRequestOut.model_validate(r) for r in rows]


@router.post("/leave-requests", response_model=LeaveRequestOut)
def worker_leave_request_create(
    body: LeaveRequestCreate,
    worker: CurrentWorker,
    db: DbSession,
) -> LeaveRequestOut:
    from app.modules.attendance import leave_requests as lr

    emp = worker_service._employee_for_user(db, worker)
    if emp is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy hồ sơ nhân viên.")
    row = lr.create_leave_request(
        db,
        employee=emp,
        leave_type_code=body.leave_type_code,
        from_date=body.from_date,
        to_date=body.to_date,
        from_half=body.from_half,
        to_half=body.to_half,
        reason=body.reason,
        submit=body.submit,
    )
    return LeaveRequestOut.model_validate(row)


@router.get("/attendance", response_model=WorkerAttendanceMonthOut)
def worker_attendance(
    worker: WorkerPasswordOk,
    db: DbSession,
    period: str | None = None,
) -> WorkerAttendanceMonthOut:
    """Công tháng của chính mình — chỉ xem, không sửa."""
    from app.modules.worker import self_service

    return self_service.get_attendance_month(db, worker, period)


@router.post("/punches", response_model=WorkerPunchOut)
def worker_mobile_punch(
    body: WorkerPunchIn,
    worker: WorkerPasswordOk,
    db: DbSession,
) -> WorkerPunchOut:
    emp = worker_service._employee_for_user(db, worker)
    if emp is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy hồ sơ nhân viên.")
    return create_worker_punch(db, emp=emp, employee_code=emp.employee_code, body=body)
