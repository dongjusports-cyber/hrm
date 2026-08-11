"""Khôi phục tên lookup_values từ seed Python (sửa mojibake danh mục).

  docker compose exec api python -m app.scripts.reseed_lookup_names
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.mdm.lookup_seed import LOOKUP_VALUES_SEED


def main() -> None:
    db = SessionLocal()
    try:
        n = 0
        for group_code, code, name, sort_order in LOOKUP_VALUES_SEED:
            r = db.execute(
                text(
                    """
                    UPDATE lookup_values
                    SET name = :name, name_local = :name, sort_order = :sort_order, is_active = true
                    WHERE group_code = :group_code AND code = :code
                      AND (name IS DISTINCT FROM :name OR name_local IS DISTINCT FROM :name)
                    """
                ),
                {
                    "group_code": group_code,
                    "code": code,
                    "name": name,
                    "sort_order": sort_order,
                },
            )
            n += r.rowcount or 0
        db.commit()
        print(f"Đã sửa {n} dòng lookup_values.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
