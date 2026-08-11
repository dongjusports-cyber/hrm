"""Báo tăng/giảm BHXH — đề xuất, xuất lô, đánh dấu đã nộp (5.5)."""

from __future__ import annotations

import calendar
import csv
from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.modules.attendance.models import PayPeriod
from app.modules.attendance.timesheet import parse_period
from app.modules.insurance.models import InsuranceDeclaration
from app.modules.insurance.schemas import (
    InsuranceDeclarationBatchExportOut,
    InsuranceDeclarationOut,
    InsuranceDeclarationProposeOut,
    InsuranceDeclarationSubmitOut,
)
from app.modules.mdm.models import Employee, EmployeeResignation
from app.modules.payroll.models import Payslip
from app.modules.payroll.money import D, ZERO

DECLARATION_TYPES = frozenset({"increase", "decrease", "salary_change"})
TYPE_LABELS = {
    "increase": "Báo tăng",
    "decrease": "Báo giảm",
    "salary_change": "Đổi mức lương",
}


def _month_bounds(period: str) -> tuple[date, date]:
    year, month = parse_period(period)
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _prev_period(period: str) -> str:
    year, month = parse_period(period)
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


def _si_base_from_slip(slip: Payslip | None) -> Decimal:
    if slip is None:
        return ZERO
    lines = slip.lines if isinstance(slip.lines, dict) else {}
    raw = lines.get("si_contribution_base")
    if raw is not None:
        return D(raw)
    return D(slip.gross or 0)


def _to_out(row: InsuranceDeclaration, emp: Employee) -> InsuranceDeclarationOut:
    return InsuranceDeclarationOut(
        id=row.id,
        employee_id=row.employee_id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        si_book_no=emp.si_book_no,
        declaration_type=row.declaration_type,
        declaration_type_label=TYPE_LABELS.get(row.declaration_type, row.declaration_type),
        effective_month=row.effective_month,
        old_salary=row.old_salary,
        new_salary=row.new_salary,
        reason_code=row.reason_code,
        batch_no=row.batch_no,
        submitted_at=row.submitted_at,
        status=row.status,
        created_at=row.created_at,
    )


def list_declarations(
    db: Session,
    *,
    effective_month: str | None = None,
    status: str | None = None,
    declaration_type: str | None = None,
) -> list[InsuranceDeclarationOut]:
    q = (
        db.query(InsuranceDeclaration, Employee)
        .join(Employee, Employee.id == InsuranceDeclaration.employee_id)
        .order_by(
            InsuranceDeclaration.effective_month.desc(),
            InsuranceDeclaration.declaration_type.asc(),
            Employee.employee_code.asc(),
        )
    )
    if effective_month:
        q = q.filter(InsuranceDeclaration.effective_month == effective_month)
    if status:
        q = q.filter(InsuranceDeclaration.status == status)
    if declaration_type:
        q = q.filter(InsuranceDeclaration.declaration_type == declaration_type)
    return [_to_out(row, emp) for row, emp in q.all()]


def propose_monthly(db: Session, effective_month: str) -> InsuranceDeclarationProposeOut:
    """Tự đề xuất danh sách tăng/giảm/đổi lương cho tháng — bỏ qua dòng đã có."""
    parse_period(effective_month)
    start, end = _month_bounds(effective_month)
    prev_period = _prev_period(effective_month)

    existing_keys = {
        (r.employee_id, r.declaration_type)
        for r in db.query(InsuranceDeclaration)
        .filter(InsuranceDeclaration.effective_month == effective_month)
        .all()
    }

    created: list[InsuranceDeclarationOut] = []
    counts = {"increase": 0, "decrease": 0, "salary_change": 0}

    # Báo tăng — NV vào làm trong tháng, tham gia BHXH
    join_emps = (
        db.query(Employee)
        .filter(
            Employee.deleted_at.is_(None),
            Employee.si_enrolled.is_(True),
            Employee.join_date.isnot(None),
            Employee.join_date >= start,
            Employee.join_date <= end,
        )
        .all()
    )
    cur_pay = (
        db.query(PayPeriod)
        .filter(
            PayPeriod.year == start.year,
            PayPeriod.month == start.month,
        )
        .one_or_none()
    )
    cur_slips: dict[UUID, Payslip] = {}
    if cur_pay:
        cur_slips = {
            s.employee_id: s
            for s in db.query(Payslip).filter(Payslip.pay_period_id == cur_pay.id).all()
        }

    for emp in join_emps:
        key = (emp.id, "increase")
        if key in existing_keys:
            continue
        slip = cur_slips.get(emp.id)
        new_salary = _si_base_from_slip(slip)
        if new_salary <= 0:
            new_salary = D(emp.contract_salary or emp.si_base_override or 0)
        if new_salary <= 0:
            continue
        row = InsuranceDeclaration(
            employee_id=emp.id,
            declaration_type="increase",
            effective_month=effective_month,
            old_salary=ZERO,
            new_salary=new_salary,
            reason_code="join",
            status="draft",
        )
        db.add(row)
        db.flush()
        created.append(_to_out(row, emp))
        counts["increase"] += 1
        existing_keys.add(key)

    # Báo giảm — nghỉ trong tháng (resign_date hoặc employee_resignations)
    resign_emp_ids: set[UUID] = set()
    for emp in (
        db.query(Employee)
        .filter(
            Employee.resign_date.isnot(None),
            Employee.resign_date >= start,
            Employee.resign_date <= end,
        )
        .all()
    ):
        resign_emp_ids.add(emp.id)
    for res in (
        db.query(EmployeeResignation)
        .filter(
            EmployeeResignation.last_working_date >= start,
            EmployeeResignation.last_working_date <= end,
        )
        .all()
    ):
        resign_emp_ids.add(res.employee_id)

    if resign_emp_ids:
        resign_emps = {
            e.id: e
            for e in db.query(Employee).filter(Employee.id.in_(resign_emp_ids)).all()
        }
        prev_pay = (
            db.query(PayPeriod)
            .filter(
                PayPeriod.year == parse_period(prev_period)[0],
                PayPeriod.month == parse_period(prev_period)[1],
            )
            .one_or_none()
        )
        prev_slips: dict[UUID, Payslip] = {}
        if prev_pay:
            prev_slips = {
                s.employee_id: s
                for s in db.query(Payslip).filter(Payslip.pay_period_id == prev_pay.id).all()
            }
        for emp_id in resign_emp_ids:
            emp = resign_emps.get(emp_id)
            if emp is None:
                continue
            key = (emp.id, "decrease")
            if key in existing_keys:
                continue
            old_salary = _si_base_from_slip(prev_slips.get(emp.id))
            if old_salary <= 0:
                old_salary = D(emp.contract_salary or emp.si_base_override or 0)
            if old_salary <= 0:
                continue
            row = InsuranceDeclaration(
                employee_id=emp.id,
                declaration_type="decrease",
                effective_month=effective_month,
                old_salary=old_salary,
                new_salary=ZERO,
                reason_code="resign",
                status="draft",
            )
            db.add(row)
            db.flush()
            created.append(_to_out(row, emp))
            counts["decrease"] += 1
            existing_keys.add(key)

    # Đổi mức lương — so sánh nền BHXH kỳ hiện tại vs kỳ trước
    prev_pay = (
        db.query(PayPeriod)
        .filter(
            PayPeriod.year == parse_period(prev_period)[0],
            PayPeriod.month == parse_period(prev_period)[1],
        )
        .one_or_none()
    )
    if cur_pay and prev_pay:
        prev_slips = {
            s.employee_id: s
            for s in db.query(Payslip).filter(Payslip.pay_period_id == prev_pay.id).all()
        }
        cur_slips = {
            s.employee_id: s
            for s in db.query(Payslip).filter(Payslip.pay_period_id == cur_pay.id).all()
        }
        active_emps = (
            db.query(Employee)
            .filter(
                Employee.deleted_at.is_(None),
                Employee.si_enrolled.is_(True),
                Employee.status.in_(["active", "probation"]),
            )
            .all()
        )
        for emp in active_emps:
            if emp.id not in cur_slips or emp.id not in prev_slips:
                continue
            old_s = _si_base_from_slip(prev_slips[emp.id])
            new_s = _si_base_from_slip(cur_slips[emp.id])
            if old_s <= 0 or new_s <= 0 or old_s == new_s:
                continue
            key = (emp.id, "salary_change")
            if key in existing_keys:
                continue
            row = InsuranceDeclaration(
                employee_id=emp.id,
                declaration_type="salary_change",
                effective_month=effective_month,
                old_salary=old_s,
                new_salary=new_s,
                reason_code="salary_adjust",
                status="draft",
            )
            db.add(row)
            db.flush()
            created.append(_to_out(row, emp))
            counts["salary_change"] += 1
            existing_keys.add(key)

    db.commit()
    return InsuranceDeclarationProposeOut(
        effective_month=effective_month,
        created_count=len(created),
        by_type=counts,
        items=created,
    )


def export_batch(
    db: Session,
    *,
    effective_month: str,
    declaration_ids: list[UUID] | None = None,
) -> InsuranceDeclarationBatchExportOut:
    parse_period(effective_month)
    q = (
        db.query(InsuranceDeclaration)
        .options(joinedload(InsuranceDeclaration.employee))
        .filter(
            InsuranceDeclaration.effective_month == effective_month,
            InsuranceDeclaration.status.in_(("draft", "exported")),
        )
    )
    if declaration_ids:
        q = q.filter(InsuranceDeclaration.id.in_(declaration_ids))
    rows = q.order_by(
        InsuranceDeclaration.declaration_type.asc(),
        InsuranceDeclaration.employee_id.asc(),
    ).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Trợ Lý AI: không có dòng báo BHXH nào để xuất cho tháng {effective_month}.",
        )

    batch_no = f"BHXH-{effective_month.replace('-', '')}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "batch_no",
            "effective_month",
            "declaration_type",
            "employee_code",
            "full_name",
            "si_book_no",
            "old_salary",
            "new_salary",
            "reason_code",
        ]
    )
    for row in rows:
        emp = row.employee
        row.batch_no = batch_no
        row.status = "exported"
        writer.writerow(
            [
                batch_no,
                row.effective_month,
                row.declaration_type,
                emp.employee_code if emp else "",
                emp.full_name if emp else "",
                emp.si_book_no if emp else "",
                str(row.old_salary),
                str(row.new_salary),
                row.reason_code or "",
            ]
        )
    db.commit()
    return InsuranceDeclarationBatchExportOut(
        batch_no=batch_no,
        effective_month=effective_month,
        row_count=len(rows),
        filename=f"bhxh_{effective_month}_{batch_no}.csv",
        content=buf.getvalue(),
    )


def mark_submitted(
    db: Session,
    *,
    effective_month: str | None = None,
    batch_no: str | None = None,
    declaration_ids: list[UUID] | None = None,
) -> InsuranceDeclarationSubmitOut:
    q = db.query(InsuranceDeclaration).filter(InsuranceDeclaration.status == "exported")
    if effective_month:
        parse_period(effective_month)
        q = q.filter(InsuranceDeclaration.effective_month == effective_month)
    if batch_no:
        q = q.filter(InsuranceDeclaration.batch_no == batch_no)
    if declaration_ids:
        q = q.filter(InsuranceDeclaration.id.in_(declaration_ids))
    rows = q.all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Trợ Lý AI: không tìm thấy lô đã xuất để đánh dấu đã nộp.",
        )
    now = datetime.now(timezone.utc)
    for row in rows:
        row.status = "submitted"
        row.submitted_at = now
    db.commit()
    return InsuranceDeclarationSubmitOut(
        marked=len(rows),
        batch_no=batch_no or rows[0].batch_no,
        message=f"Đã đánh dấu {len(rows)} dòng báo BHXH là đã nộp cơ quan.",
    )
