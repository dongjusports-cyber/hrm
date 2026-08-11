"""Hạng mục 1.5 — employee_assignments: lịch sử đổi tổ + chuyển tổ hàng loạt từ lưới."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.mdm.models import Department, Employee, EmployeeAssignment, Team


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_team(db: Session, dept_code: str, team_code: str, team_name: str) -> Team:
    dept = db.query(Department).filter(Department.code == dept_code).one()
    team = Team(department_id=dept.id, code=team_code, name=team_name)
    db.add(team)
    db.commit()
    return team


def test_preview_transfer_team_shows_affected_and_skipped(client, db: Session):
    target = _make_team(db, "SW1", "SW1-TX1", "Tổ đích 1")
    same_team = _make_team(db, "SW1", "SW1-TX2", "Tổ đích 1 sẽ giữ")
    emp1 = db.query(Employee).filter(Employee.employee_code == "1514").one()
    emp2 = db.query(Employee).filter(Employee.employee_code == "1643").one()
    emp2.team_id = same_team.id  # để test "đã ở tổ đích" khi chuyển sang same_team
    db.commit()

    headers = _hr_headers(client)
    body = {
        "employee_ids": [str(emp1.id), str(emp2.id)],
        "team_id": str(same_team.id),
        "effective_from": date.today().isoformat(),
        "confirm": False,
    }
    res = client.post("/api/employees/transfer-team/preview", headers=headers, json=body)
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["team_code"] == "SW1-TX2"
    assert out["affected_count"] == 1
    assert len(out["skipped"]) == 1
    assert out["skipped"][0]["employee_code"] == "1643"
    assert "Đã ở tổ" in out["skipped"][0]["reason"]
    assert target.id  # tổ khác chỉ dùng để không trùng code với same_team


def test_apply_transfer_team_writes_assignment_and_updates_employee(client, db: Session):
    dept_qc = db.query(Department).filter(Department.code == "QC1").one()
    team = _make_team(db, "QC1", "QC1-TX1", "QC Tổ 1")
    emp = db.query(Employee).filter(Employee.employee_code == "5321").one()
    old_dept_id = emp.department_id
    assert old_dept_id != dept_qc.id or team.department_id == dept_qc.id

    headers = _hr_headers(client)
    body = {
        "employee_ids": [str(emp.id)],
        "team_id": str(team.id),
        "effective_from": date.today().isoformat(),
        "decision_no": "QD-001/2026",
        "reason_code": "reorg",
        "confirm": True,
    }
    res = client.post("/api/employees/transfer-team", headers=headers, json=body)
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["affected_count"] == 1
    assert out["team_code"] == "QC1-TX1"

    db.expire_all()
    emp2 = db.query(Employee).filter(Employee.employee_code == "5321").one()
    assert emp2.team_id == team.id
    assert emp2.department_id == team.department_id

    rows = (
        db.query(EmployeeAssignment)
        .filter(EmployeeAssignment.employee_id == emp.id)
        .order_by(EmployeeAssignment.effective_from.desc())
        .all()
    )
    assert len(rows) == 1
    assert rows[0].team_id == team.id
    assert rows[0].decision_no == "QD-001/2026"
    assert rows[0].reason_code == "reorg"
    assert rows[0].effective_to is None


def test_apply_transfer_team_closes_previous_open_assignment(client, db: Session):
    team_a = _make_team(db, "SW1", "SW1-TX3", "Tổ A")
    team_b = _make_team(db, "SW1", "SW1-TX4", "Tổ B")
    emp = db.query(Employee).filter(Employee.employee_code == "1732").one()
    headers = _hr_headers(client)

    first = date.today() - timedelta(days=30)
    r1 = client.post(
        "/api/employees/transfer-team",
        headers=headers,
        json={
            "employee_ids": [str(emp.id)],
            "team_id": str(team_a.id),
            "effective_from": first.isoformat(),
            "confirm": True,
        },
    )
    assert r1.status_code == 200, r1.text

    second = date.today()
    r2 = client.post(
        "/api/employees/transfer-team",
        headers=headers,
        json={
            "employee_ids": [str(emp.id)],
            "team_id": str(team_b.id),
            "effective_from": second.isoformat(),
            "confirm": True,
        },
    )
    assert r2.status_code == 200, r2.text

    db.expire_all()
    rows = (
        db.query(EmployeeAssignment)
        .filter(EmployeeAssignment.employee_id == emp.id)
        .order_by(EmployeeAssignment.effective_from.asc())
        .all()
    )
    assert len(rows) == 2
    assert rows[0].team_id == team_a.id
    assert rows[0].effective_to == second - timedelta(days=1)
    assert rows[1].team_id == team_b.id
    assert rows[1].effective_to is None


def test_transfer_team_rejects_future_effective_from(client, db: Session):
    team = _make_team(db, "SW1", "SW1-TX5", "Tổ tương lai")
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    headers = _hr_headers(client)
    future = (date.today() + timedelta(days=5)).isoformat()
    res = client.post(
        "/api/employees/transfer-team/preview",
        headers=headers,
        json={
            "employee_ids": [str(emp.id)],
            "team_id": str(team.id),
            "effective_from": future,
            "confirm": False,
        },
    )
    assert res.status_code == 422


def test_transfer_team_skips_resigned_employee(client, db: Session):
    team = _make_team(db, "SW1", "SW1-TX6", "Tổ nghỉ việc")
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    emp.status = "resigned"
    db.commit()

    headers = _hr_headers(client)
    res = client.post(
        "/api/employees/transfer-team/preview",
        headers=headers,
        json={
            "employee_ids": [str(emp.id)],
            "team_id": str(team.id),
            "effective_from": date.today().isoformat(),
            "confirm": False,
        },
    )
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["affected_count"] == 0
    assert out["skipped"][0]["reason"] == "Đã nghỉ việc"


def test_transfer_team_requires_confirm(client, db: Session):
    team = _make_team(db, "SW1", "SW1-TX7", "Tổ chưa xác nhận")
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    headers = _hr_headers(client)
    res = client.post(
        "/api/employees/transfer-team",
        headers=headers,
        json={
            "employee_ids": [str(emp.id)],
            "team_id": str(team.id),
            "effective_from": date.today().isoformat(),
            "confirm": False,
        },
    )
    assert res.status_code == 400


def test_list_employee_assignments_history(client, db: Session):
    team = _make_team(db, "SW1", "SW1-TX8", "Tổ lịch sử")
    emp = db.query(Employee).filter(Employee.employee_code == "1643").one()
    headers = _hr_headers(client)
    client.post(
        "/api/employees/transfer-team",
        headers=headers,
        json={
            "employee_ids": [str(emp.id)],
            "team_id": str(team.id),
            "effective_from": date.today().isoformat(),
            "decision_no": "QD-002/2026",
            "confirm": True,
        },
    )
    res = client.get(f"/api/employees/{emp.id}/assignments", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) == 1
    assert rows[0]["team_code"] == "SW1-TX8"
    assert rows[0]["decision_no"] == "QD-002/2026"
    assert rows[0]["approved_by_name"]
