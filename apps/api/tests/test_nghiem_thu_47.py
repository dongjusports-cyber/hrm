"""24§ nghiệm thu 4.7 — số phép trên phiếu = tổng bút toán sổ."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.attendance.annual_leave_ledger import verify_annual_leave_nghiem_thu_47
from app.modules.payroll.payslip_detail import get_hr_payslip_detail
from tests.test_oct2025_regression import apply_oct2025_fixture


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_nghiem_thu_47_payslip_matches_ledger(client, db):
    """Tiêu chí 24§ đợt 4: số dư phép in trên phiếu = tổng bút toán sổ."""
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    calc = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert calc.status_code == 200, calc.text
    slip = next(s for s in calc.json()["payslips"] if s["employee_code"] == "5290")
    slip_id = UUID(str(slip["id"]))
    emp_id = UUID(str(slip["employee_id"]))

    detail = get_hr_payslip_detail(db, slip_id)
    as_of = date(2025, 10, 31)
    ok, msg = verify_annual_leave_nghiem_thu_47(
        db,
        employee_id=emp_id,
        as_of=as_of,
        payslip_remaining=Decimal(str(detail.annual_leave_remaining)),
    )
    assert ok, msg

    api_detail = client.get(f"/api/payroll/payslips/{slip_id}/detail", headers=headers)
    assert api_detail.status_code == 200
    assert Decimal(str(api_detail.json()["annual_leave_remaining"])) == Decimal(
        str(detail.annual_leave_remaining)
    )
