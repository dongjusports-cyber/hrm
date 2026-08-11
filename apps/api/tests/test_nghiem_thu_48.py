"""24§ nghiệm thu 4.8 — chốt kỳ, đổi policy, số kỳ cũ không đổi (20§ N3)."""

from copy import deepcopy
from decimal import Decimal
from uuid import UUID

from app.modules.payroll.models import Payslip, PolicySnapshot
from tests.test_oct2025_regression import apply_oct2025_fixture


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _confirm_policy_change(client, headers, pkg_id, payload, name):
    for step in ("1", "2", "3"):
        res = client.put(
            f"/api/policies/packages/{pkg_id}",
            headers={**headers, "X-Confirm-Step": step},
            json={"name": name, "payload": payload},
        )
        assert res.status_code == 200, res.text
    return res.json()["package"]


def verify_locked_payslip_unchanged_after_policy_change(
    db,
    *,
    payslip_id,
    net_before: Decimal,
    snapshot_id_before,
) -> tuple[bool, str]:
    """Đọc lại phiếu sau khi đổi policy — net và snapshot_id phải giữ nguyên."""
    slip = db.get(Payslip, payslip_id)
    if slip is None:
        return False, "Không tìm thấy phiếu"
    net_ok = Decimal(str(slip.net)) == net_before
    snap_ok = slip.policy_snapshot_id == snapshot_id_before
    snap = db.get(PolicySnapshot, snapshot_id_before) if snapshot_id_before else None
    attend_snap = None
    if snap and isinstance(snap.payload, dict):
        attend_snap = snap.payload.get("attendance_bonus_monthly")
    ok = net_ok and snap_ok and snap is not None
    detail = (
        f"net={slip.net} (trước {net_before}), snapshot={slip.policy_snapshot_id}, "
        f"attendance_bonus_snapshot={attend_snap}"
    )
    if not net_ok:
        detail += " — net đổi"
    if not snap_ok:
        detail += " — snapshot_id đổi"
    return ok, detail


def test_nghiem_thu_48_locked_period_unchanged_after_policy(client, db):
    """Tiêu chí 24§ đợt 4: chốt kỳ → sửa policy → kỳ đã chốt không đổi."""
    apply_oct2025_fixture(db)
    hr = _hr_headers(client)
    admin = _admin_headers(client)

    calc = client.post("/api/payroll/periods/2025-10/calculate", headers=hr)
    assert calc.status_code == 200, calc.text
    slip_json = next(s for s in calc.json()["payslips"] if s["employee_code"] == "5290")
    net_before = Decimal(str(slip_json["net"]))
    slip_id = UUID(str(slip_json["id"]))
    slip = db.query(Payslip).filter(Payslip.id == slip_id).one()
    snap_id_before = slip.policy_snapshot_id
    assert snap_id_before is not None

    pub = client.post("/api/payroll/periods/2025-10/publish", headers=hr)
    assert pub.status_code == 200, pub.text
    lock = client.post("/api/payroll/periods/2025-10/lock", headers=hr)
    assert lock.status_code == 200, lock.text

    pkg = client.get("/api/policies/packages", headers=admin).json()[0]
    payload = deepcopy(pkg["payload"])
    payload["attendance_bonus_monthly"] = int(payload.get("attendance_bonus_monthly", 600_000)) + 30_000
    _confirm_policy_change(client, admin, pkg["id"], payload, pkg["name"])

    db.expire_all()
    ok, msg = verify_locked_payslip_unchanged_after_policy_change(
        db,
        payslip_id=slip.id,
        net_before=net_before,
        snapshot_id_before=snap_id_before,
    )
    assert ok, msg

    active = client.get("/api/policies/packages", headers=admin).json()[0]
    assert active["payload"]["attendance_bonus_monthly"] == payload["attendance_bonus_monthly"]

    blocked = client.post("/api/payroll/periods/2025-10/calculate", headers=hr)
    assert blocked.status_code == 400
