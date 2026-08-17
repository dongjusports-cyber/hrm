"""Trích xuất «Thông tin bổ sung 14.08.26.xlsx» + ghi vào employees/{MSNV}.json.

  python -m app.scripts.extract_thong_tin_bo_sung
  python -m app.scripts.extract_thong_tin_bo_sung --xlsx path.xlsx --no-merge
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.scripts.thong_tin_bo_sung import (
    default_extract_dir,
    default_snapshot_dir,
    default_xlsx_path,
    load_supplement,
    merge_into_snapshots,
    write_extract,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trích xuất Thông tin bổ sung 14.08 vào dữ liệu công nhân")
    parser.add_argument("--xlsx", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--snapshots", type=Path, default=None)
    parser.add_argument("--no-merge", action="store_true", help="Chỉ xuất JSON/CSV, không sửa employees/*.json")
    args = parser.parse_args()

    xlsx = (args.xlsx or default_xlsx_path()).resolve()
    out = (args.out or default_extract_dir(xlsx)).resolve()
    records = load_supplement(xlsx)
    print(f"Đọc {len(records)} MSNV từ {xlsx.name}")

    merge_stats = None
    if not args.no_merge:
        snap = (args.snapshots or default_snapshot_dir()).resolve()
        merge_stats = merge_into_snapshots(records, snap)
        print(
            f"Ghi JSON snapshot: {merge_stats['updated']} cập nhật / "
            f"{merge_stats['files']} khớp file, thiếu JSON {merge_stats['missing_json']}"
        )

    write_extract(records, out, xlsx_path=xlsx, merge_stats=merge_stats)
    print(f"Xuất {out / 'employees.json'} + BAO_CAO.csv + manifest.json")


if __name__ == "__main__":
    main()
