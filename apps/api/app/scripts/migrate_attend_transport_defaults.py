"""Migrate phụ cấp Chuyên cần / Đi lại: 230.000→600.000, 760.000→800.000.

Chạy:
  python -m app.scripts.migrate_attend_transport_defaults
  docker compose exec api python -m app.scripts.migrate_attend_transport_defaults
"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.modules.payroll.seed_allowances import migrate_attend_transport_defaults


def main() -> None:
    db = SessionLocal()
    try:
        stats = migrate_attend_transport_defaults(db)
        print(
            f"OK: catalog {stats['catalog']} rows, "
            f"assignments {stats['assignments']} rows -> ATTEND 600000 / TRANSPORT 800000"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
