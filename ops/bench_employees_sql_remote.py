#!/usr/bin/env python3
"""Chay TRONG container api — dem so cau SQL cua list_employees tren Session MOI.

Session moi = giong mot HTTP request that (get_db). Do tren Session dung lai se bi
identity map che mat cac lenh ghi lap. CHI DOC + ROLLBACK, khong commit gi.
"""
import json
import statistics
import time

from sqlalchemy import event, func

from app.core.database import SessionLocal, engine
from app.modules.attendance.models import AnnualLeaveEntry, AnnualLeaveLedger
from app.modules.mdm import service

RUNS = 3
_sql: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, params, context, executemany):
    _sql.append(statement.strip().split(maxsplit=1)[0].upper())


def one_call() -> tuple[float, dict[str, int], int]:
    db = SessionLocal()
    _sql.clear()
    try:
        t0 = time.perf_counter()
        rows = service.list_employees(db)
        ms = (time.perf_counter() - t0) * 1000
        kinds: dict[str, int] = {}
        for kind in _sql:
            kinds[kind] = kinds.get(kind, 0) + 1
        return ms, kinds, len(rows)
    finally:
        db.rollback()
        db.close()


samples: list[float] = []
kinds: dict[str, int] = {}
rows = 0
for _ in range(RUNS):
    ms, kinds, rows = one_call()
    samples.append(ms)

db = SessionLocal()
try:
    year = time.gmtime().tm_year
    ledgers = (
        db.query(func.count(AnnualLeaveLedger.id))
        .filter(AnnualLeaveLedger.year == year)
        .scalar()
    )
    entries = db.query(func.count(AnnualLeaveEntry.id)).scalar()
finally:
    db.close()

print(
    json.dumps(
        {
            "rows": rows,
            "p50_ms": round(statistics.median(samples), 1),
            "max_ms": round(max(samples), 1),
            "sql_theo_loai": kinds,
            "tong_sql": sum(kinds.values()),
            "ghi_tren_duong_doc": sum(
                v for k, v in kinds.items() if k in ("INSERT", "UPDATE", "DELETE")
            ),
            f"so_phep_nam_{year}": ledgers,
            "so_but_toan": entries,
        },
        indent=2,
        ensure_ascii=False,
    )
)
