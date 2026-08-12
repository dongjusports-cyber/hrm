"""Nghiệm thu P0 validation + P3 tái tuyển — chạy sau deploy/migrate.

  docker compose exec api alembic upgrade head
  docker compose exec api python -m app.scripts.nghiem_thu_validation_rehire
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import inspect

from app.core.database import SessionLocal, engine
from app.modules.mdm import employee_validation as ev
from app.modules.mdm.models import Employee, EmployeeResignation
from app.modules.mdm.schemas import EmployeeCreate


@dataclass
class Result:
    code: str
    ok: bool
    detail: str


def run() -> list[Result]:
    db = SessionLocal()
    out: list[Result] = []
    try:
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("employee_resignations")}
        out.append(
            Result(
                "P3-migration",
                {"snapshot_json", "rehire_mode", "rehire_reason"} <= cols,
                f"Cột tái tuyển: {sorted(cols & {'snapshot_json', 'rehire_mode', 'rehire_reason'})}",
            )
        )

        suggested = ev.suggest_employee_code(db)
        out.append(
            Result(
                "P0-suggest",
                suggested.isdigit() and len(suggested) >= 3,
                f"Gợi ý MSNV: {suggested}",
            )
        )

        issues = ev.validate_employee_create(
            db,
            EmployeeCreate.model_validate(
                {
                    "employee_code": "xx",
                    "full_name": "A",
                    "contract_salary": "0",
                    "pay_channel": "CASH",
                }
            ),
        )
        err_codes = {i.code for i in issues if i.level == "error"}
        out.append(
            Result(
                "P0-validate-errors",
                {"format", "min"} <= err_codes or "required" in err_codes,
                f"Mã lỗi: {sorted(err_codes)}",
            )
        )

        resigned = (
            db.query(Employee)
            .filter(Employee.status == "resigned", Employee.deleted_at.is_(None))
            .first()
        )
        if resigned is None:
            out.append(Result("P3-resigned-sample", False, "Không có NV resigned trong DB — bỏ qua tái tuyển"))
        else:
            last = (
                db.query(EmployeeResignation)
                .filter(EmployeeResignation.employee_id == resigned.id)
                .order_by(EmployeeResignation.seq_no.desc())
                .first()
            )
            has_snap = last is not None and isinstance(last.snapshot_json, dict)
            out.append(
                Result(
                    "P3-snapshot-on-resign",
                    has_snap or last is None,
                    "Có snapshot_json" if has_snap else "Chưa có bản ghi nghỉ hoặc snapshot (NV cũ trước migrate)",
                )
            )

        out.append(Result("P0-module", True, "employee_validation.py hoạt động"))
    finally:
        db.close()
    return out


def main() -> None:
    results = run()
    ok = sum(1 for r in results if r.ok)
    print("=== Nghiệm thu P0 + P3 ===")
    for r in results:
        mark = "OK" if r.ok else "FAIL"
        print(f"[{mark}] {r.code}: {r.detail}")
    print(f"Tổng: {ok}/{len(results)} đạt")
    if ok < len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
