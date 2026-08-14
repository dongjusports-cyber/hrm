"""Bulk insert attendance punches — thay vòng lặp nested transaction từng punch."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.modules.attendance.engine import VN_TZ
from app.modules.integration.models import AttendancePunch

_CHUNK = 400


def _key(code: str, punch_time: datetime) -> tuple[str, datetime]:
    if punch_time.tzinfo is None:
        punch_time = punch_time.replace(tzinfo=VN_TZ)
    return (code, punch_time)


def existing_punch_keys(
    db: Session, keys: list[tuple[str, datetime]]
) -> set[tuple[str, datetime]]:
    if not keys:
        return set()
    found: set[tuple[str, datetime]] = set()
    for i in range(0, len(keys), _CHUNK):
        chunk = keys[i : i + _CHUNK]
        rows = (
            db.query(AttendancePunch.employee_code, AttendancePunch.punch_time)
            .filter(tuple_(AttendancePunch.employee_code, AttendancePunch.punch_time).in_(chunk))
            .all()
        )
        found.update(_key(code, pt) for code, pt in rows)
    return found


def _insert_rowcount(result, chunk_len: int) -> int:
    """psycopg3 đôi khi trả rowcount=-1 với INSERT ON CONFLICT — đã lọc trùng trước."""
    rc = result.rowcount
    if rc is None or rc < 0:
        return chunk_len
    return rc


def _insert_chunk(db: Session, sync_job_id: UUID, chunk: list[dict]) -> int:
    if not chunk:
        return 0
    values = [
        {
            "employee_code": r["employee_code"],
            "employee_id": r.get("employee_id"),
            "punch_time": r["punch_time"],
            "direction": r.get("direction"),
            "sync_job_id": sync_job_id,
            "source": r.get("source", "mitapro"),
            "ma_cham_cong": r.get("ma_cham_cong"),
            "device_id": r.get("device_id"),
            "raw": r.get("raw"),
        }
        for r in chunk
    ]
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        stmt = pg_insert(AttendancePunch).values(values)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_punch_employee_time")
        result = db.execute(stmt)
        return _insert_rowcount(result, len(chunk))
    if dialect == "sqlite":
        stmt = sqlite_insert(AttendancePunch).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["employee_code", "punch_time"])
        result = db.execute(stmt)
        return _insert_rowcount(result, len(chunk))
    db.add_all(
        [
            AttendancePunch(
                employee_code=r["employee_code"],
                employee_id=r.get("employee_id"),
                punch_time=r["punch_time"],
                direction=r.get("direction"),
                sync_job_id=sync_job_id,
                source=r.get("source", "mitapro"),
                ma_cham_cong=r.get("ma_cham_cong"),
                device_id=r.get("device_id"),
                raw=r.get("raw"),
            )
            for r in chunk
        ]
    )
    db.flush()
    return len(chunk)


def bulk_insert_punches(
    db: Session,
    *,
    sync_job_id: UUID,
    rows: list[dict],
) -> tuple[int, int, int]:
    """Trả về (inserted, skipped, linked_inserted)."""
    if not rows:
        return 0, 0, 0
    keys = [_key(r["employee_code"], r["punch_time"]) for r in rows]
    existing = existing_punch_keys(db, keys)
    to_add = [r for r in rows if _key(r["employee_code"], r["punch_time"]) not in existing]
    skipped = len(rows) - len(to_add)
    inserted = 0
    linked = sum(1 for r in to_add if r.get("employee_id") is not None)
    for i in range(0, len(to_add), _CHUNK):
        chunk = to_add[i : i + _CHUNK]
        inserted += _insert_chunk(db, sync_job_id, chunk)
    skipped += len(to_add) - inserted
    db.flush()
    return inserted, skipped, linked
