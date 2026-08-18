"""GET /payroll/periods/{period} không được INSERT kỳ lương.

Cùng bài học GET /employees (HR-H002): đường đọc chỉ SELECT.
Trước đây get_period → ensure_pay_period → INSERT + commit khi kỳ chưa có.
"""

from __future__ import annotations

from sqlalchemy import event

from app.modules.attendance.models import PayPeriod
from app.modules.attendance.timesheet import ensure_pay_period

MISSING = "2099-01"


def _hr_headers(client) -> dict[str, str]:
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class _SqlCounter:
    def __init__(self, bind) -> None:
        self._bind = bind
        self.statements: list[str] = []

    def __enter__(self) -> _SqlCounter:
        event.listen(self._bind, "before_cursor_execute", self._record)
        return self

    def __exit__(self, *_exc) -> None:
        event.remove(self._bind, "before_cursor_execute", self._record)

    def _record(self, conn, cursor, statement, params, context, executemany) -> None:
        self.statements.append(statement.strip().split(maxsplit=1)[0].upper())

    @property
    def writes(self) -> list[str]:
        return [s for s in self.statements if s in ("INSERT", "UPDATE", "DELETE")]


def _period_count(db, year: int, month: int) -> int:
    db.expire_all()
    return db.query(PayPeriod).filter(PayPeriod.year == year, PayPeriod.month == month).count()


def test_get_payroll_period_missing_is_404_and_does_not_insert(client, db):
    headers = _hr_headers(client)
    assert _period_count(db, 2099, 1) == 0

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get(f"/api/payroll/periods/{MISSING}", headers=headers)

    assert res.status_code == 404, res.text
    assert _period_count(db, 2099, 1) == 0
    assert counter.writes == [], (
        f"GET /payroll/periods/{MISSING} ghi DB {counter.writes} — {counter.statements}"
    )


def test_get_payslips_and_adjustments_missing_period_empty_no_insert(client, db):
    headers = _hr_headers(client)

    slips = client.get("/api/payroll/payslips", headers=headers, params={"period": MISSING})
    adjs = client.get("/api/payroll/adjustments", headers=headers, params={"period": MISSING})

    assert slips.status_code == 200, slips.text
    assert slips.json() == []
    assert adjs.status_code == 200, adjs.text
    assert adjs.json() == []
    assert _period_count(db, 2099, 1) == 0


def test_get_payroll_period_ok_after_period_exists(client, db):
    ensure_pay_period(db, MISSING)
    headers = _hr_headers(client)

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get(f"/api/payroll/periods/{MISSING}", headers=headers)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["period"] == MISSING
    assert body["status"] == "open"
    assert counter.writes == [], f"GET kỳ đã có vẫn ghi DB {counter.writes}"
