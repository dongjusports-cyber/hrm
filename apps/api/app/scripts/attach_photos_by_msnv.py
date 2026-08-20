"""Gắn ảnh chân dung vào NV đúng MSNV. Không tạo/xóa NV, không sửa hồ sơ khác.

Nguồn: thư mục photos/{MSNV}.jpg (hoặc file .jpg ngay trong --dir).
Đích: data/uploads/employee_photos/{uuid}.jpg + employees.photo_path.

  python -m app.scripts.attach_photos_by_msnv /tmp/photos
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.mdm.models import Employee
from app.modules.mdm.service import _photo_dir


def _iter_photos(src: Path) -> list[Path]:
    roots = [src]
    nested = src / "photos"
    if nested.is_dir():
        roots.append(nested)
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        for path in sorted(root.iterdir()):
            if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            code = path.stem.strip()
            if not code or code in seen:
                continue
            if path.stat().st_size < 500:
                continue
            seen.add(code)
            out.append(path)
    return out


def attach_photos(db: Session, src: Path) -> tuple[int, int, list[str]]:
    files = _iter_photos(src)
    dest_root = _photo_dir()
    dest_root.mkdir(parents=True, exist_ok=True)
    ok = 0
    missing: list[str] = []
    for path in files:
        code = path.stem.strip()
        emp = (
            db.query(Employee)
            .filter(Employee.employee_code == code, Employee.deleted_at.is_(None))
            .first()
        )
        if emp is None:
            missing.append(code)
            continue
        dest = dest_root / f"{emp.id}.jpg"
        dest.write_bytes(path.read_bytes())
        emp.photo_path = dest.name
        ok += 1
    return ok, len(files), missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=Path)
    args = parser.parse_args()
    src = args.dir.resolve()
    if not src.is_dir():
        raise SystemExit(f"Khong thay thu muc anh: {src}")

    db = SessionLocal()
    try:
        ok, total, missing = attach_photos(db, src)
        db.commit()
        with_photo = (
            db.query(Employee)
            .filter(
                Employee.deleted_at.is_(None),
                Employee.photo_path.isnot(None),
                Employee.photo_path != "",
            )
            .count()
        )
        nv = db.query(Employee).filter(Employee.deleted_at.is_(None)).count()
    finally:
        db.close()

    print(f"file_anh {total} | gan {ok} | khong_co_MSNV {len(missing)}")
    if missing[:15]:
        print("thieu NV:", ", ".join(missing[:15]) + ("…" if len(missing) > 15 else ""))
    print(f"NV {nv} | dang_co_anh {with_photo}")


if __name__ == "__main__":
    main()
