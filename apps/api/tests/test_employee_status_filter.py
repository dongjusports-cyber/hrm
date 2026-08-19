"""Lọc NV theo trạng thái suy ra — thử việc / thai sản."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.modules.attendance.models import LeaveRequest
from app.modules.mdm.models import Employee, EmployeeWtRegime


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_probation_filter_by_unsigned_contract(client):
    """NV active nhưng chưa ký HĐ chính thức → tab Thử việc."""
    headers = _hr_headers(client)
    code = "9101"
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": "NV Thử Việc Filter",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": date.today().isoformat(),
            "contract_signed_at": None,
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]
    assert created.json()["effective_status"] == "probation"

    listed = client.get("/api/employees?status=probation", headers=headers).json()
    codes = {e["employee_code"] for e in listed}
    assert code in codes

    active_list = client.get("/api/employees?status=active", headers=headers).json()
    assert code not in {e["employee_code"] for e in active_list}

    # Tìm MSNV trên tab Chính thức vẫn thấy NV (đang thuộc tab Thử việc)
    search_active = client.get(f"/api/employees?status=active&q={code}", headers=headers).json()
    assert code in {e["employee_code"] for e in search_active}
    assert search_active[0]["effective_status"] == "probation"

    future = (date.today() + timedelta(days=30)).isoformat()
    client.put(
        f"/api/employees/{emp_id}",
        headers=headers,
        json={"contract_signed_at": future},
    )
    detail = client.get(f"/api/employees/{emp_id}", headers=headers).json()
    assert detail["effective_status"] == "probation"


def test_maternity_filter_by_status(client):
    """NV status=maternity xuất hiện ở tab Thai sản, không ở Chính thức."""
    headers = _hr_headers(client)
    code = "9102"
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": "NV Thai San Filter",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "status": "maternity",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["effective_status"] == "maternity"

    mat_list = client.get("/api/employees?status=maternity", headers=headers).json()
    assert code in {e["employee_code"] for e in mat_list}

    active_list = client.get("/api/employees?status=active", headers=headers).json()
    assert code not in {e["employee_code"] for e in active_list}


def test_pt_leave_stays_on_active_tab(client, db):
    """PT (khám thai) — không đẩy NV khỏi tab Chính thức (J1, 22§22.6)."""
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    emp.status = "active"
    emp.contract_signed_at = date(2020, 1, 15)
    db.commit()

    today = date.today()
    db.add(
        LeaveRequest(
            employee_id=emp.id,
            leave_type_code="PT",
            from_date=today,
            to_date=today,
            total_days=Decimal("0.5"),
            reason="Khám thai",
            status="approved",
        )
    )
    db.commit()

    active_list = client.get("/api/employees?status=active", headers=headers).json()
    assert "1514" in {e["employee_code"] for e in active_list}
    mat_list = client.get("/api/employees?status=maternity", headers=headers).json()
    assert "1514" not in {e["employee_code"] for e in mat_list}


def test_mle_leave_on_maternity_tab(client, db):
    """MLE vẫn đưa NV vào tab Thai sản khi đơn approved bao phủ hôm nay."""
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.status = "active"
    emp.contract_signed_at = date(2010, 1, 1)
    db.commit()

    today = date.today()
    db.add(
        LeaveRequest(
            employee_id=emp.id,
            leave_type_code="MLE",
            from_date=today - timedelta(days=5),
            to_date=today + timedelta(days=30),
            total_days=Decimal("35"),
            reason="Thai sản",
            status="approved",
        )
    )
    db.commit()

    mat_list = client.get("/api/employees?status=maternity", headers=headers).json()
    assert "5290" in {e["employee_code"] for e in mat_list}
    active_list = client.get("/api/employees?status=active", headers=headers).json()
    assert "5290" not in {e["employee_code"] for e in active_list}


def test_special_regime_filter_by_wt_regime(client):
    """Tab «Chế độ đặc biệt» — lọc NV có chế độ về sớm hiệu lực (không dùng status)."""
    headers = _hr_headers(client)
    code = "9104"
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": "NV Che Do Dac Biet",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": "2020-01-15",
            "contract_signed_at": "2020-01-15",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]

    # Chưa có regime → không nằm trong tab special_regime, vẫn ở tab Chính thức
    before = client.get("/api/employees?status=special_regime", headers=headers).json()
    assert code not in {e["employee_code"] for e in before}
    active_before = client.get("/api/employees?status=active", headers=headers).json()
    assert code in {e["employee_code"] for e in active_before}

    today = date.today()
    reg = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "CHILD",
            "hours_early": 2,
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=30)).isoformat(),
        },
    )
    assert reg.status_code == 201, reg.text

    special = client.get("/api/employees?status=special_regime", headers=headers).json()
    assert code in {e["employee_code"] for e in special}
    row = next(e for e in special if e["employee_code"] == code)
    assert row["wt_regime_type"] == "CHILD"
    assert row["wt_regime_date_from"] == today.isoformat()
    assert row["wt_regime_date_to"] == (today + timedelta(days=30)).isoformat()
    assert row["join_date"] == "2020-01-15"
    assert row["team_name"] or row["team_code"]
    assert Decimal(str(row["si_base"])) >= Decimal("6000000")
    # Vẫn còn ở tab Chính thức (chế độ đặc biệt không đổi effective_status)
    active_after = client.get("/api/employees?status=active", headers=headers).json()
    assert code in {e["employee_code"] for e in active_after}


def test_special_regime_includes_maternity_even_if_resigned(client, db):
    """Nghỉ thai sản vẫn vào tab Chế độ đặc biệt dù hồ sơ gắn resigned (GenusSuite)."""
    headers = _hr_headers(client)
    today = date.today()
    mat = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "9105",
            "full_name": "NV Nghi Thai San Resigned",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": "2020-01-15",
            "contract_signed_at": "2020-01-15",
            "status": "resigned",
            "resign_date": today.isoformat(),
        },
    )
    assert mat.status_code == 201, mat.text
    mat_id = mat.json()["id"]
    db.add(
        EmployeeWtRegime(
            employee_id=UUID(mat_id),
            regime_type="MATERNITY",
            hours_early=0,
            date_from=today - timedelta(days=10),
            date_to=today + timedelta(days=60),
            note="test maternity resigned",
        )
    )

    child = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "9106",
            "full_name": "NV Nuoi Con Resigned",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": "2020-01-15",
            "contract_signed_at": "2020-01-15",
            "status": "resigned",
            "resign_date": today.isoformat(),
        },
    )
    assert child.status_code == 201, child.text
    db.add(
        EmployeeWtRegime(
            employee_id=UUID(child.json()["id"]),
            regime_type="CHILD",
            hours_early=2,
            date_from=today - timedelta(days=10),
            date_to=today + timedelta(days=60),
            note="test child resigned",
        )
    )
    db.commit()

    special = client.get("/api/employees?status=special_regime", headers=headers).json()
    codes = {e["employee_code"] for e in special}
    assert "9105" in codes
    assert "9106" not in codes
    row = next(e for e in special if e["employee_code"] == "9105")
    assert row["wt_regime_type"] == "MATERNITY"


def test_special_regime_skips_ended_overlap(client, db):
    """Regime đã cắt (ended_at) không đè regime mở còn hiệu lực."""
    headers = _hr_headers(client)
    today = date.today()
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "9107",
            "full_name": "NV Regime Ended Overlap",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": "2020-01-15",
            "contract_signed_at": "2020-01-15",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    emp_id = UUID(created.json()["id"])
    db.add(
        EmployeeWtRegime(
            employee_id=emp_id,
            regime_type="CHILD",
            hours_early=1,
            date_from=today,
            date_to=today,
            ended_at=datetime.now(tz=timezone.utc),
            note="ended 1-day",
        )
    )
    db.add(
        EmployeeWtRegime(
            employee_id=emp_id,
            regime_type="CHILD",
            hours_early=2,
            date_from=today - timedelta(days=30),
            date_to=today + timedelta(days=90),
            note="open real",
        )
    )
    db.commit()

    special = client.get("/api/employees?status=special_regime", headers=headers).json()
    row = next(e for e in special if e["employee_code"] == "9107")
    assert row["wt_regime_date_to"] == (today + timedelta(days=90)).isoformat()
    assert row["wt_regime_date_from"] == (today - timedelta(days=30)).isoformat()
