"""GET chấm công không INSERT kỳ lương (cùng bài học HR-H002 / payroll GET)."""

from __future__ import annotations

from sqlalchemy import event

from app.modules.attendance.models import PayPeriod

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


def test_get_pay_period_missing_is_404_and_does_not_insert(client, db):
    headers = _hr_headers(client)
    assert _period_count(db, 2099, 1) == 0

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get("/api/attendance/pay-periods/2099-01", headers=headers)

    assert res.status_code == 404, res.text
    assert _period_count(db, 2099, 1) == 0
    assert counter.writes == [], f"GET pay-periods ghi DB {counter.writes}"


def test_get_timesheets_and_grid_missing_period_empty_no_insert(client, db):
    headers = _hr_headers(client)

    with _SqlCounter(db.get_bind()) as counter:
        sheets = client.get(
            "/api/attendance/timesheets", headers=headers, params={"period": MISSING}
        )
        grid = client.get(
            "/api/attendance/days/grid", headers=headers, params={"date": "2099-01-15"}
        )
        cycle = client.get(
            "/api/attendance/cycle-leave", headers=headers, params={"period": MISSING}
        )
        review = client.get(
            "/api/attendance/review", headers=headers, params={"period": MISSING}
        )

    assert sheets.status_code == 200, sheets.text
    assert sheets.json() == []
    assert grid.status_code == 200, grid.text
    assert cycle.status_code == 200, cycle.text
    assert cycle.json() == []
    assert review.status_code == 200, review.text
    assert review.json()["period_status"] == "none"
    assert _period_count(db, 2099, 1) == 0
    assert counter.writes == [], f"GET chấm công ghi DB {counter.writes}"
