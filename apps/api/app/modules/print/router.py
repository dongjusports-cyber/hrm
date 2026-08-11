"""API mẫu in HTML (5.9)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUser, DbSession
from app.modules.core.models import User
from app.modules.mdm.schemas import BulkSalaryRaiseRequest
from app.modules.print import service

router = APIRouter(prefix="/print", tags=["print"])


def _hr(user: CurrentUser) -> User:
    service.require_hr_access(user)
    return user


@router.get("/employees/{employee_id}/contract", response_class=HTMLResponse)
def print_contract(
    employee_id: UUID,
    db: DbSession,
    _user: Annotated[User, Depends(_hr)],
    contract_id: UUID | None = Query(default=None),
) -> HTMLResponse:
    return HTMLResponse(service.render_contract(db, employee_id, contract_id=contract_id))


@router.get("/employees/{employee_id}/probation", response_class=HTMLResponse)
def print_probation(
    employee_id: UUID,
    db: DbSession,
    _user: Annotated[User, Depends(_hr)],
    contract_id: UUID | None = Query(default=None),
) -> HTMLResponse:
    return HTMLResponse(service.render_probation(db, employee_id, contract_id=contract_id))


@router.get("/employees/{employee_id}/decision", response_class=HTMLResponse)
def print_decision(
    employee_id: UUID,
    db: DbSession,
    _user: Annotated[User, Depends(_hr)],
    decision_no: str | None = Query(default=None),
) -> HTMLResponse:
    return HTMLResponse(service.render_decision(db, employee_id, decision_no=decision_no))


@router.post("/salary-raise", response_class=HTMLResponse)
def print_salary_raise(
    body: BulkSalaryRaiseRequest,
    db: DbSession,
    _user: Annotated[User, Depends(_hr)],
) -> HTMLResponse:
    """In phụ lục tăng lương — toàn công ty / bộ phận / danh sách NV (xem trước hoặc sau lưu)."""
    return HTMLResponse(service.render_salary_raise_appendix(db, body))
