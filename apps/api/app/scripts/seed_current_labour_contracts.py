"""Nạp một HĐ «hiện tại» cho NV chưa có bản ghi labour_contracts.

Dùng khi chuyển từ GenusSuite — không có lịch sử TV→HD1→HD2, chỉ cần HĐ đang hiệu lực
để cảnh báo hết hạn, in mẫu và ký tiếp đúng thứ tự từ đây.

Quy ước bootstrap:
  - Thử việc → TV (active)
  - Chính thức / thai sản → VTH (active) — tránh cảnh báo hết hạn HD1 giả
  - Đã nghỉ → VTH (terminated), end_date = ngày nghỉ nếu có

Chạy:
  docker compose exec api python -m app.scripts.seed_current_labour_contracts
  docker compose exec api python -m app.scripts.seed_current_labour_contracts --dry-run
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.mdm import labour_contract_flow as lcf
from app.modules.mdm.models import Employee, LabourContract


def _contract_status(emp: Employee, end_date: date | None) -> str:
    if emp.status == "resigned":
        return "terminated"
    if end_date and end_date < date.today():
        return "expired"
    return "active"


def seed_employee(db: Session, emp: Employee, *, dry_run: bool) -> str | None:
    exists = (
        db.query(LabourContract.id)
        .filter(LabourContract.employee_id == emp.id)
        .limit(1)
        .first()
    )
    if exists:
        return None

    ctype = lcf.infer_current_contract_type(emp)
    start = emp.contract_signed_at or emp.join_date or date.today()
    sign = emp.contract_signed_at or start

    if ctype == "TV":
        end = lcf.contract_end_date(start, "TV")
        salary = emp.probation_salary or emp.contract_salary or Decimal("0")
    else:
        end = emp.resign_date if emp.status == "resigned" else None
        salary = emp.contract_salary or Decimal("0")

    status = _contract_status(emp, end)

    if dry_run:
        return f"{emp.employee_code} {ctype} {start} → {end or 'VTH'} ({status})"

    row = LabourContract(
        employee_id=emp.id,
        contract_type_code=ctype,
        seq_no=1,
        sign_date=sign,
        start_date=start,
        end_date=end,
        base_salary=salary,
        position_code=emp.position_code,
        team_id=emp.team_id,
        status=status,
    )
    db.add(row)
    return f"{emp.employee_code} {ctype} ({status})"


def run(*, dry_run: bool = False) -> None:
    db = SessionLocal()
    created = skipped = 0
    samples: list[str] = []
    try:
        employees = (
            db.query(Employee)
            .filter(Employee.deleted_at.is_(None))
            .order_by(Employee.employee_code)
            .all()
        )
        for emp in employees:
            if emp.status not in ("active", "probation", "maternity", "resigned"):
                skipped += 1
                continue
            msg = seed_employee(db, emp, dry_run=dry_run)
            if msg is None:
                skipped += 1
            else:
                created += 1
                if len(samples) < 8:
                    samples.append(msg)
        if not dry_run:
            db.commit()
        mode = "DRY-RUN" if dry_run else "DONE"
        print(f"{mode}: tạo {created} HĐ · bỏ qua {skipped} NV")
        for line in samples:
            print(f"  · {line}")
        if created > len(samples):
            print(f"  … và {created - len(samples)} NV khác")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp HĐ hiện tại cho NV chưa có labour_contracts")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in preview, không ghi DB")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
