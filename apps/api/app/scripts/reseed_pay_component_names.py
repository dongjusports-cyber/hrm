"""Khôi phục tên pay_components từ CATALOG (sửa mojibake dropdown phụ cấp).

  docker compose exec api python -m app.scripts.reseed_pay_component_names
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.payroll.seed_allowances import CATALOG


def main() -> None:
    db = SessionLocal()
    try:
        n = 0
        for item in CATALOG:
            r = db.execute(
                text(
                    """
                    UPDATE pay_components
                    SET name = :name
                    WHERE code = :code AND name IS DISTINCT FROM :name
                    """
                ),
                {"code": item["code"], "name": item["name"]},
            )
            n += r.rowcount or 0
        db.commit()
        print(f"Đã sửa {n} dòng pay_components.name.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
