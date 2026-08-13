"""Tách mã HSE khỏi PCCC trên hồ sơ phụ cấp.

Chạy:
    docker compose exec api python -m app.scripts.migrate_pccc_hse
"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.modules.payroll.seed_allowances import migrate_pccc_hse_assignments


def main() -> None:
    db = SessionLocal()
    try:
        result = migrate_pccc_hse_assignments(db)
        moved = result["moved_to_hse"]
        manual = result["needs_manual_pccc_hse_split"]
        print(f"Chuyển PCCC 50k → HSE: {len(moved)} NV ({', '.join(moved) or '—'})")
        if manual:
            print(
                "Cần HR tách tay PCCC 932k → PCCC 882k + HSE 50k:",
                ", ".join(manual),
            )
        else:
            print("Không có NV PCCC 932k cần tách tay.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
