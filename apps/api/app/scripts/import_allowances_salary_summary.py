"""Nạp phụ cấp cố định từ «Danh sách Nhân Viên - Bộ phận hiện tại.xls».

Cột (header dòng 2): PCCC+HSE_AMT, POS_AMT, TOXIC_AMT, INDUS_AMT, TRANS_AMT, TECH_AMT, OTHER_AMT
Map INDUS_AMT → ATTEND (GenusSuite: mức chuyên cần/tháng trên bảng lương tóm tắt).

Chạy:
  docker compose exec api python -m app.scripts.import_allowances_salary_summary /tmp/empinfo [--dry-run]
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

import xlrd

from app.core.database import SessionLocal
from app.modules.mdm.models import Employee
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent
from app.modules.payroll.seed_allowances import seed_allowance_types

# (cột index, mã pay_component)
COL_MAP: list[tuple[int, str]] = [
    (9, "PCCC"),
    (10, "POSITION"),
    (11, "TOXIC"),
    (12, "ATTEND"),  # INDUS_AMT trên file GenusSuite = mức chuyên cần HĐ
    (13, "TRANSPORT"),
    (14, "TECH"),
    (15, "OTHER"),
]


def _parse_amount(raw) -> Decimal | None:
    if raw in ("", None):
        return None
    try:
        return Decimal(str(raw).strip().replace(",", ""))
    except Exception:
        return None


def load_rows(xls_path: Path) -> dict[str, dict[str, Decimal | None]]:
    wb = xlrd.open_workbook(str(xls_path))
    sh = wb.sheet_by_index(0)
    out: dict[str, dict[str, Decimal | None]] = {}
    for r in range(3, sh.nrows):
        try:
            msnv = str(int(float(sh.cell_value(r, 3))))
        except (TypeError, ValueError):
            continue
        codes: dict[str, Decimal | None] = {}
        for col, code in COL_MAP:
            codes[code] = _parse_amount(sh.cell_value(r, col))
        out[msnv] = codes
    return out


def run(data_dir: str, *, dry_run: bool = False) -> None:
    base = Path(data_dir)
    xls = next(base.glob("Danh sách*.xls"))
    rows = load_rows(xls)
    print(f"Đọc {len(rows)} NV từ {xls.name}")

    db = SessionLocal()
    try:
        seed_allowance_types(db)
        type_by_code = {t.code: t for t in db.query(PayComponent).all()}
        created_cnt = [0]
        updated_cnt = [0]
        deleted_cnt = [0]
        skipped = 0

        def sync(emp: Employee, code: str, amt: Decimal | None) -> None:
            at = type_by_code.get(code)
            if at is None:
                return
            row = (
                db.query(EmployeeAllowanceAssignment)
                .filter(
                    EmployeeAllowanceAssignment.employee_id == emp.id,
                    EmployeeAllowanceAssignment.allowance_type_id == at.id,
                )
                .one_or_none()
            )
            if amt is None or amt <= 0:
                if row is not None:
                    db.delete(row)
                    deleted_cnt[0] += 1
                return
            if row is None:
                db.add(
                    EmployeeAllowanceAssignment(
                        employee_id=emp.id,
                        allowance_type_id=at.id,
                        amount=amt,
                    )
                )
                created_cnt[0] += 1
            else:
                row.amount = amt
                updated_cnt[0] += 1

        for msnv, codes in sorted(rows.items()):
            emp = db.query(Employee).filter(Employee.employee_code == msnv).first()
            if emp is None:
                skipped += 1
                continue
            for code, amt in codes.items():
                if dry_run:
                    if amt is not None and amt > 0:
                        print(f"  {msnv} {code}={amt}")
                    continue
                sync(emp, code, amt)

        if dry_run:
            print(f"DRY-RUN — {len(rows)} NV, bỏ qua {skipped}")
            db.rollback()
        else:
            db.commit()
            print(
                f"HOÀN TẤT: tạo {created_cnt[0]}, cập nhật {updated_cnt[0]}, "
                f"xóa {deleted_cnt[0]}, bỏ qua NV không có {skipped}"
            )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("data_dir")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    run(args.data_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
