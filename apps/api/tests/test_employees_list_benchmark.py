"""Bước H — hàng rào hiệu năng cho GET /api/employees (~360 NV).

Bài học từ phiên 15/08/2026: đo bằng milliseconds trên **cùng một Session** đã che một
lỗi thật — `annual_leave_remaining_batch` ghi sổ phép cho từng NV, bị `get_db()` rollback,
rồi lặp lại mỗi request (2.170 câu SQL, TTFB 2,7 giây trên VPS). Từ vòng thứ hai trong
cùng Session thì identity map giữ ledger nên không ghi nữa → benchmark báo "226 ms, đạt".

Vì vậy hàng rào chính ở đây là **đếm câu SQL** và **Session mới mỗi lần gọi**, không phải
milliseconds (SQLite trong test luôn nhanh hơn Postgres thật).
"""

from __future__ import annotations

import statistics
import time
from datetime import date
from decimal import Decimal

from sqlalchemy import event
from sqlalchemy.orm import Session as SaSession

from app.modules.mdm import service
from app.modules.mdm.models import Department, Employee, Team

TARGET_MS = 300
RUNS = 5
EMP_COUNT = 360

# Đường đọc danh sách NV phải thuần đọc và batch: không ghi, số query không tăng theo số NV.
# Mốc đo 15/08/2026 sau khi sửa: 17 query ở tầng service, 22 khi đi qua HTTP (thêm auth).
# Trước khi sửa là 2.170 query cho 359 NV.
MAX_WRITE_STATEMENTS = 0
MAX_STATEMENTS_HTTP = 30
MAX_STATEMENTS_SERVICE = 20


def _hr_headers(client) -> dict[str, str]:
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_employees(db, count: int) -> None:
    dept = db.query(Department).filter(Department.code == "SW1").one()
    team = db.query(Team).filter(Team.department_id == dept.id, Team.code == "T1").one()
    existing = db.query(Employee).filter(Employee.deleted_at.is_(None)).count()
    batch: list[Employee] = []
    for i in range(max(0, count - existing)):
        code = f"B{i:04d}"
        if db.query(Employee.id).filter(Employee.employee_code == code).first():
            continue
        batch.append(
            Employee(
                employee_code=code,
                full_name=f"Benchmark NV {code}",
                gender="M",
                pay_channel="ATM",
                team_id=team.id,
                position_title="Công nhân",
                join_date=date(2019, 1, 15),
                contract_signed_at=date(2019, 4, 15),
                probation_salary=Decimal("4840750"),
                contract_salary=Decimal("5675000"),
                status="active",
                si_enrolled=True,
            )
        )
    if batch:
        db.add_all(batch)
        db.commit()


class _SqlCounter:
    """Đếm câu SQL thực gửi xuống DB trong một khối lệnh."""

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

    def summary(self) -> str:
        kinds: dict[str, int] = {}
        for s in self.statements:
            kinds[s] = kinds.get(s, 0) + 1
        return f"tổng={len(self.statements)} {kinds}"


def test_get_employees_khong_ghi_du_lieu(client, db):
    """GET phải read-only: mọi INSERT/UPDATE ở đây sẽ bị rollback rồi lặp mỗi request."""
    _seed_employees(db, EMP_COUNT)
    headers = _hr_headers(client)
    client.get("/api/employees", headers=headers)

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get("/api/employees", headers=headers)
    assert res.status_code == 200, res.text
    assert len(res.json()) >= EMP_COUNT

    print(f"\n[GET /api/employees] SQL {counter.summary()}")
    assert len(counter.writes) <= MAX_WRITE_STATEMENTS, (
        f"GET /api/employees ghi DB {counter.writes[:10]} — {counter.summary()}"
    )
    assert len(counter.statements) <= MAX_STATEMENTS_HTTP, (
        f"Số query tăng theo số NV (N+1) — {counter.summary()}"
    )


def test_list_employees_session_moi_khong_bi_n_plus_1(client, db):
    """Session mới = một HTTP request thật; Session ấm che được lỗi ghi lặp."""
    _seed_employees(db, EMP_COUNT)
    bind = db.get_bind()

    fresh = SaSession(bind=bind)
    try:
        with _SqlCounter(bind) as counter:
            rows = service.list_employees(fresh)
    finally:
        fresh.rollback()
        fresh.close()

    assert len(rows) >= EMP_COUNT
    print(f"\n[list_employees Session moi] SQL {counter.summary()}")
    assert len(counter.writes) <= MAX_WRITE_STATEMENTS, (
        f"list_employees ghi DB trên Session mới — {counter.summary()}"
    )
    assert len(counter.statements) <= MAX_STATEMENTS_SERVICE, (
        f"list_employees N+1 trên Session mới — {counter.summary()}"
    )


def test_get_employees_list_under_300ms(client, db):
    """Mốc thời gian tham chiếu — Session mới mỗi vòng để không đo trên cache ấm."""
    _seed_employees(db, EMP_COUNT)
    bind = db.get_bind()

    samples: list[float] = []
    n = 0
    for _ in range(RUNS):
        fresh = SaSession(bind=bind)
        try:
            t0 = time.perf_counter()
            rows = service.list_employees(fresh)
            samples.append((time.perf_counter() - t0) * 1000)
            n = len(rows)
        finally:
            fresh.rollback()
            fresh.close()

    p50 = statistics.median(samples)
    print(
        f"\n[list_employees] NV={n} | p50={p50:.1f}ms max={max(samples):.1f}ms "
        f"| target={TARGET_MS}ms | DB=sqlite-memory (Postgres se cham hon)"
    )
    assert p50 <= TARGET_MS, f"p50 {p50:.1f}ms > {TARGET_MS}ms (n={n})"
