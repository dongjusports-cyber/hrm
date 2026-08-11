"""Bootstrap HĐ hiện tại + luồng ký tiếp TV→HD1→HD2→VTH."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.mdm import labour_contract_flow as lcf
from app.modules.mdm.models import Department, Employee, LabourContract, Team


@pytest.mark.parametrize(
    "status,expected",
    [
        ("probation", "TV"),
        ("active", "VTH"),
        ("maternity", "VTH"),
        ("resigned", "VTH"),
    ],
)
def test_infer_current_contract_type(status: str, expected: str):
    emp = Employee(employee_code="X", full_name="X", status=status)
    assert lcf.infer_current_contract_type(emp) == expected


def test_allowed_first_contract_probation():
    assert lcf.allowed_first_contract_types("probation", "TV") == ["TV", "HD1"]


def test_allowed_first_contract_active_boss_override():
    assert lcf.allowed_first_contract_types("active", "HD1") == ["HD1", "HD2", "VTH"]


def test_seed_current_labour_contracts_script(db):
    from app.scripts.seed_current_labour_contracts import seed_employee

    dept = Department(code="T1", name="Test Dept", category="direct")
    db.add(dept)
    db.flush()
    team = Team(department_id=dept.id, code="T1-1", name="Team 1", effective_from=date(2020, 1, 1))
    db.add(team)
    db.flush()

    emp = Employee(
        employee_code="9999",
        full_name="SEED TEST",
        status="active",
        team_id=team.id,
        join_date=date(2018, 3, 1),
        contract_signed_at=date(2018, 6, 1),
        contract_salary=Decimal("8000000"),
    )
    db.add(emp)
    db.commit()

    msg = seed_employee(db, emp, dry_run=False)
    assert msg is not None
    db.commit()

    row = db.query(LabourContract).filter(LabourContract.employee_id == emp.id).one()
    assert row.contract_type_code == "VTH"
    assert row.status == "active"
    assert row.end_date is None
    assert row.seq_no == 1

    assert seed_employee(db, emp, dry_run=False) is None
