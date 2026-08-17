"""Chấm công điện thoại — allowlist Main Office, GPS, mã xác minh."""

from sqlalchemy.orm import Session

from app.modules.mdm.models import Employee, Team
from app.modules.mdm.service import get_or_create_department_by_code
from tests.worker_auth import unlocked_worker_headers

TINY_HASH = "a" * 64


def _admin(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _assign_dept(db: Session, employee_code: str, dept_code: str, dept_name: str) -> None:
    dept = get_or_create_department_by_code(db, dept_code, dept_name)
    team = Team(department_id=dept.id, code=f"T-{dept_code}-P", name=dept_name)
    db.add(team)
    db.flush()
    emp = db.query(Employee).filter(Employee.employee_code == employee_code).one()
    emp.team_id = team.id
    db.commit()


def test_me_sewing_cannot_punch_by_default(client):
    me = client.get("/api/worker/me", headers=unlocked_worker_headers(client, "5290"))
    assert me.status_code == 200
    body = me.json()
    assert body["can_mobile_punch"] is False
    assert "Main Office" in (body["punch_blocked_reason"] or "")


def test_sewing_post_punch_forbidden(client, db):
    client.put(
        "/api/config/mobile-punch",
        headers=_admin(client),
        json={"require_photo": False},
    )
    res = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "5290"),
        json={},
    )
    assert res.status_code == 403
    assert "Main Office" in res.json()["detail"]


def test_main_office_can_punch(client, db):
    _assign_dept(db, "1732", "03", "Main Office")
    client.put(
        "/api/config/mobile-punch",
        headers=_admin(client),
        json={"mode": "allowlist", "department_codes": ["03"], "require_photo": False},
    )
    me = client.get("/api/worker/me", headers=unlocked_worker_headers(client, "1732"))
    assert me.json()["can_mobile_punch"] is True
    assert me.json()["department_code"] == "03"

    res = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={"device_id": "test-phone"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["source"] == "mobile"
    assert str(res.json()["verify_code"]).startswith("DJ-")

    again = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={},
    )
    assert again.status_code == 429


def test_open_all_allows_sewing(client, db):
    client.put(
        "/api/config/mobile-punch",
        headers=_admin(client),
        json={"mode": "all", "require_photo": False},
    )
    me = client.get("/api/worker/me", headers=unlocked_worker_headers(client, "5290"))
    assert me.json()["can_mobile_punch"] is True
    res = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "5290"),
        json={},
    )
    assert res.status_code == 200, res.text


def test_mode_off_blocks_office(client, db):
    _assign_dept(db, "1732", "03", "Main Office")
    client.put(
        "/api/config/mobile-punch",
        headers=_admin(client),
        json={"mode": "off", "require_photo": False},
    )
    me = client.get("/api/worker/me", headers=unlocked_worker_headers(client, "1732"))
    assert me.json()["can_mobile_punch"] is False
    res = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={},
    )
    assert res.status_code == 403


def test_extra_msnv_allowlist(client, db):
    client.put(
        "/api/config/mobile-punch",
        headers=_admin(client),
        json={"mode": "allowlist", "department_codes": ["03"], "extra_msnv": ["5290"], "require_photo": False},
    )
    me = client.get("/api/worker/me", headers=unlocked_worker_headers(client, "5290"))
    assert me.json()["can_mobile_punch"] is True


def test_gps_outside_rejected(client, db):
    _assign_dept(db, "1732", "03", "Main Office")
    client.put(
        "/api/config/mobile-punch",
        headers=_admin(client),
        json={
            "mode": "allowlist",
            "department_codes": ["03"],
            "require_photo": False,
            "gps_lat": 10.8,
            "gps_lng": 106.7,
            "gps_radius_m": 200,
        },
    )
    missing = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={},
    )
    assert missing.status_code == 400
    far = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={"latitude": 11.0, "longitude": 106.7},
    )
    assert far.status_code == 403
    near = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={"latitude": 10.8005, "longitude": 106.7},
    )
    assert near.status_code == 200, near.text


def test_photo_required(client, db):
    _assign_dept(db, "1732", "03", "Main Office")
    client.put(
        "/api/config/mobile-punch",
        headers=_admin(client),
        json={"mode": "allowlist", "department_codes": ["03"], "require_photo": True},
    )
    missing = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={},
    )
    assert missing.status_code == 400
    ok = client.post(
        "/api/worker/punches",
        headers=unlocked_worker_headers(client, "1732"),
        json={"photo_hash": TINY_HASH},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["verify_code"].startswith("DJ-")
    assert "Mã xác minh" in ok.json()["detail"]


def test_hr_cannot_change_mobile_punch_config(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    res = client.put(
        "/api/config/mobile-punch",
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "all"},
    )
    assert res.status_code == 403


def test_get_config_does_not_insert_row(client, db):
    from app.modules.config.models import MobilePunchSettings

    assert db.get(MobilePunchSettings, 1) is None
    res = client.get("/api/config/mobile-punch", headers=_admin(client))
    assert res.status_code == 200
    assert res.json()["mode"] == "allowlist"
    assert res.json()["department_codes"] == ["03"]
    assert res.json()["persisted"] is False
    assert db.get(MobilePunchSettings, 1) is None
