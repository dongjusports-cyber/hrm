"""Trích xuất 100% hồ sơ từ file Excel GenusSuite (cột D = ảnh chân dung).

Ưu tiên file mới nhất trong thư mục empinfo, ví dụ:
  «Thông tin full DS công nhân 14.08.xls» (có ~359 ảnh nhúng)

Output (mặc định):
  HIEN_PHAP/Thông tin danh sách nhân viên/trich_xuat_<ngày>/
    employees.json          — toàn bộ NV trong 1 file
    photos/{MSNV}.{ext}     — ảnh chân dung (nếu có trong file)
    BAO_CAO_THIEU.csv       — MSNV thiếu / không tách được
    manifest.json           — thống kê trích xuất

Chạy (từ apps/api):
  python -m app.scripts.extract_empinfo_profiles
  python -m app.scripts.extract_empinfo_profiles --xls path/to/file.xls --out path/to/out
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import olefile
import xlrd

from app.scripts.empinfo_lookup_map import (
    infer_contract_type,
    resolve_education_code,
    resolve_nationality_code,
    resolve_place_code,
)
from app.scripts.import_employee_list_1108 import (
    _clean_digits,
    _clean_phone,
    _gender,
    _norm,
    _parse_vn_date,
)

SCHEMA_VERSION = 1

# Cột Excel (0-based) — phải khớp header row
COL = {
    "department_name": 0,
    "employee_code": 1,
    "full_name": 2,
    "picture": 3,
    "birth_date": 4,
    "join_date": 5,
    "birth_place_text": 6,
    "contract_salary": 7,
    "team_name": 8,
    "gender_raw": 9,
    "position_title": 10,
    "phone_raw": 11,
    "education_raw": 12,
    "permanent_address": 13,
    "id_number_raw": 14,
    "id_issue_place_text": 15,
    "id_issue_date": 16,
    "si_book_no_raw": 17,
    "contract_no": 18,
    # Cột T Excel — «Start Contract» = ngày ký / bắt đầu HĐ (hiển thị «Ngày Ký HĐ» trên web)
    "contract_start": 19,
    "contract_end": 20,
    "left_date": 21,
}

# Trường bắt buộc để coi là «tách 100%»
REQUIRED_FIELDS = (
    "employee_code",
    "full_name",
    "birth_date",
    "join_date",
    "birth_place_text",
    "contract_salary",
    "gender",
    "team_name",
    "department_name",
    "position_title",
    "phone",
    "education_code",
    "permanent_address",
    "id_number",
    "id_issue_place_text",
    "id_issue_date",
    "si_book_no",
    "contract_no",
    "contract_start",
)

HEADER_MARKERS = {"dept", "empid", "id", "no.", "picture"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def find_empinfo_dir() -> Path:
    base = repo_root() / "HIEN_PHAP"
    for child in base.iterdir():
        if child.is_dir() and "nh" in child.name.lower() and "vi" in child.name.lower():
            return child
    raise FileNotFoundError("Không tìm thấy thư mục «Thông tin danh sách nhân viên»")


def find_latest_profile_xls(empinfo: Path | None = None) -> Path:
    """Chọn file hồ sơ GenusSuite mới / đầy đủ nhất (ưu tiên tên «full», rồi size lớn)."""
    folder = empinfo or find_empinfo_dir()
    candidates = [
        p
        for p in folder.glob("*.xls")
        if p.suffix.lower() == ".xls" and "bộ phận" not in p.name.lower() and "danh sách nhân" not in p.name.lower()
    ]
    if not candidates:
        raise FileNotFoundError(f"Không có file hồ sơ .xls trong {folder}")

    def score(p: Path) -> tuple[int, int, float]:
        name = unicodedata.normalize("NFC", p.name).lower()
        has_full = 1 if "full" in name else 0
        has_thong_tin = 1 if "thông tin" in name or "thong tin" in name else 0
        return (has_full, has_thong_tin, p.stat().st_size)

    return max(candidates, key=score)


def default_xls_path() -> Path:
    return find_latest_profile_xls()


def default_out_dir(xls_path: Path | None = None) -> Path:
    src = xls_path or default_xls_path()
    stem = unicodedata.normalize("NFC", src.stem)
    tag = "140826" if "14.08" in stem else "110826"
    return src.parent / f"trich_xuat_{tag}"


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Không serialize được: {type(value)!r}")


def _cell_raw(sh: xlrd.sheet.Sheet, row: int, col: int) -> Any:
    return sh.cell_value(row, col)


def _cell_text(raw: Any) -> str | None:
    if raw in ("", None):
        return None
    if isinstance(raw, float) and raw == int(raw):
        raw = int(raw)
    text = _norm(str(raw).replace("\xa0", " "))
    return text or None


def _parse_msnv(raw: Any) -> str | None:
    if raw in ("", None):
        return None
    text = _cell_text(raw)
    if not text or text.lower() in HEADER_MARKERS:
        return None
    try:
        return str(int(float(raw)))
    except (TypeError, ValueError):
        return text


def _is_summary_row(sh: xlrd.sheet.Sheet, row: int) -> bool:
    c0 = _cell_text(_cell_raw(sh, row, COL["department_name"]))
    c2 = _cell_text(_cell_raw(sh, row, COL["full_name"]))
    if c0 and ("total" in c0.lower() or "grand total" in c0.lower()):
        return True
    if not c2 and _parse_msnv(_cell_raw(sh, row, COL["employee_code"])) in ("1", "2", "3"):
        c0l = (c0 or "").lower()
        if "total" in c0l or c0l == "":
            return True
    return False


def _is_header_row(sh: xlrd.sheet.Sheet, row: int) -> bool:
    c0 = _cell_text(_cell_raw(sh, row, COL["department_name"]))
    c1 = _cell_text(_cell_raw(sh, row, COL["employee_code"]))
    if c0 and c0.lower() == "dept":
        return True
    if c1 and c1.lower() in ("empid", "id"):
        return True
    return False


def _education_code(raw: Any) -> str | None:
    return resolve_education_code(raw)


def _build_record(sh: xlrd.sheet.Sheet, row: int, datemode: int) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for key, col in COL.items():
        raw[key] = _cell_raw(sh, row, col)

    msnv = _parse_msnv(raw["employee_code"])
    contract_no = _cell_text(raw["contract_no"])
    left = _parse_vn_date(raw["left_date"], datemode)

    parsed: dict[str, Any] = {
        "employee_code": msnv,
        "department_name": _cell_text(raw["department_name"]),
        "team_name": _cell_text(raw["team_name"]),
        "full_name": _cell_text(raw["full_name"]),
        "birth_date": _parse_vn_date(raw["birth_date"], datemode),
        "join_date": _parse_vn_date(raw["join_date"], datemode),
        "birth_place_text": _cell_text(raw["birth_place_text"]),
        "contract_salary": Decimal(str(raw["contract_salary"] or 0)),
        "gender": _gender(str(raw["gender_raw"] or "")),
        "position_title": _cell_text(raw["position_title"]),
        "phone": _clean_phone(raw["phone_raw"]),
        "education_code": _education_code(raw["education_raw"]),
        "permanent_address": _cell_text(raw["permanent_address"]),
        "id_number": _clean_digits(raw["id_number_raw"]),
        "id_issue_place_text": _cell_text(raw["id_issue_place_text"]),
        "id_issue_date": _parse_vn_date(raw["id_issue_date"], datemode),
        "si_book_no": _clean_digits(raw["si_book_no_raw"]),
        "contract_no": contract_no,
        "contract_type_code": infer_contract_type(contract_no),
        "contract_start": _parse_vn_date(raw["contract_start"], datemode),
        "contract_end": _parse_vn_date(raw["contract_end"], datemode),
        "left_date": left,
        "birth_place_code": resolve_place_code("birth_place", _cell_text(raw["birth_place_text"])),
        "id_issue_place_code": resolve_place_code(
            "id_issue_place", _cell_text(raw["id_issue_place_text"])
        ),
        "nationality_code": resolve_nationality_code(None)
        if _clean_digits(raw["id_number_raw"])
        else None,
        "photo_file": None,
        "photo_status": "missing_in_xls",
    }
    ctype = parsed["contract_type_code"]
    cstart = parsed["contract_start"]
    if cstart:
        parsed["contract_signed_at"] = cstart
    if left:
        parsed["status"] = "resigned"
    elif ctype == "TV":
        parsed["status"] = "probation"
    else:
        parsed["status"] = "active"

    raw_export: dict[str, Any] = {}
    for key, col in COL.items():
        val = raw[key]
        if isinstance(val, float) and val == int(val) and key.endswith("_raw"):
            val = int(val)
        raw_export[key] = val

    return {
        "row_index": row + 1,
        "parsed": parsed,
        "raw": raw_export,
    }


def _missing_fields(parsed: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        val = parsed.get(field)
        if val is None or val == "" or val == Decimal("0") and field == "contract_salary":
            if field == "contract_salary" and val == Decimal("0"):
                missing.append(field)
            elif val is None or val == "":
                missing.append(field)
    # contract_end có thể trống với HĐ vô thời hạn — không bắt buộc
    return missing


def _scan_embedded_images(xls_path: Path) -> list[dict[str, Any]]:
    """Quét binary OLE — file .xls hiện tại thường không nhúng JPEG/PNG."""
    found: list[dict[str, Any]] = []
    if not olefile.isOleFile(str(xls_path)):
        return found
    ole = olefile.OleFileIO(str(xls_path))
    try:
        data = ole.openstream("Workbook").read()
    finally:
        ole.close()

    for sig, ext in ((b"\xff\xd8\xff", "jpg"), (b"\x89PNG\r\n\x1a\n", "png"), (b"BM", "bmp")):
        start = 0
        while True:
            idx = data.find(sig, start)
            if idx < 0:
                break
            found.append({"offset": idx, "format": ext, "size_hint": len(data) - idx})
            start = idx + len(sig)
    return found


def _extract_photos_excel_com(xls_path: Path, out_photos: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Gọi subprocess trích ảnh — tránh lỗi clipboard khi chạy cùng xlrd."""
    import subprocess
    import sys

    api_root = Path(__file__).resolve().parents[2]
    mapping: dict[str, str] = {}
    issues: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.scripts.extract_empinfo_photos",
                str(xls_path),
                str(out_photos),
            ],
            cwd=str(api_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7200,
        )
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.returncode not in (0, 1) and proc.stderr:
            issues.append(
                {
                    "employee_code": "",
                    "full_name": "",
                    "row_index": 0,
                    "issue_type": "photo_extract_error",
                    "missing_fields": "picture",
                    "detail": proc.stderr.strip()[:500],
                }
            )
    except Exception as exc:
        issues.append(
            {
                "employee_code": "",
                "full_name": "",
                "row_index": 0,
                "issue_type": "photo_extract_error",
                "missing_fields": "picture",
                "detail": str(exc),
            }
        )
        return mapping, issues

    manifest_path = out_photos.parent / "photos_manifest.json"
    if manifest_path.is_file():
        report = json.loads(manifest_path.read_text(encoding="utf-8"))
        mapping = dict(report.get("mapping") or {})
        for item in report.get("issues") or []:
            issues.append(
                {
                    "employee_code": item.get("employee_code") or "",
                    "full_name": item.get("full_name") or "",
                    "row_index": item.get("row_index") or 0,
                    "issue_type": "missing_photo",
                    "missing_fields": "picture",
                    "detail": item.get("detail") or item.get("issue") or "missing",
                }
            )
    return mapping, issues


def extract(xls_path: Path, out_dir: Path, *, try_com_photos: bool = True) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = out_dir / "photos"
    photos_dir.mkdir(exist_ok=True)

    wb = xlrd.open_workbook(str(xls_path), formatting_info=True)
    sh = wb.sheet_by_index(0)
    datemode = wb.datemode

    employees: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    seen_codes: dict[str, int] = {}

    for row in range(sh.nrows):
        if _is_header_row(sh, row) or _is_summary_row(sh, row):
            continue
        msnv = _parse_msnv(_cell_raw(sh, row, COL["employee_code"]))
        if not msnv:
            if any(_cell_text(_cell_raw(sh, row, c)) for c in COL.values()):
                issues.append(
                    {
                        "employee_code": "",
                        "full_name": _cell_text(_cell_raw(sh, row, COL["full_name"])) or "",
                        "row_index": row + 1,
                        "issue_type": "no_msnv",
                        "missing_fields": "ALL",
                        "detail": "Dòng có dữ liệu nhưng không đọc được MSNV",
                    }
                )
            continue

        if msnv in seen_codes:
            issues.append(
                {
                    "employee_code": msnv,
                    "full_name": _cell_text(_cell_raw(sh, row, COL["full_name"])) or "",
                    "row_index": row + 1,
                    "issue_type": "duplicate_msnv",
                    "missing_fields": "",
                    "detail": f"Trùng MSNV — lần đầu ở dòng {seen_codes[msnv]}",
                }
            )
        seen_codes[msnv] = row + 1

        rec = _build_record(sh, row, datemode)
        parsed = rec["parsed"]
        missing = _missing_fields(parsed)

        if missing:
            issues.append(
                {
                    "employee_code": msnv,
                    "full_name": parsed.get("full_name") or "",
                    "row_index": row + 1,
                    "issue_type": "missing_fields",
                    "missing_fields": ";".join(missing),
                    "detail": f"Thiếu {len(missing)} trường bắt buộc",
                }
            )

        employees.append(rec)

    # Ảnh (GenusSuite nhúng Picture shapes — cần Excel COM trên Windows)
    embedded = _scan_embedded_images(xls_path)
    photo_by_msnv: dict[str, str] = {}
    photo_issues: list[dict[str, Any]] = []
    excel_shape_count = 0
    if try_com_photos:
        photo_by_msnv, photo_issues = _extract_photos_excel_com(xls_path, photos_dir)
        excel_shape_count = len(photo_by_msnv) + sum(
            1 for i in photo_issues if i["issue_type"] == "missing_photo"
        )
    issues.extend(photo_issues)

    photos_ok = 0
    photos_manual: list[dict[str, Any]] = []
    for rec in employees:
        code = rec["parsed"]["employee_code"]
        row_idx = rec["row_index"]
        full_name = rec["parsed"].get("full_name") or ""
        expected = f"photos/{code}.jpg"
        rec["parsed"]["photo_file"] = expected

        if code in photo_by_msnv:
            rec["parsed"]["photo_status"] = "extracted"
            photos_ok += 1
            continue

        disk_photo = photos_dir / f"{code}.jpg"
        if disk_photo.is_file() and disk_photo.stat().st_size >= 500:
            rec["parsed"]["photo_status"] = "extracted"
            photos_ok += 1
            continue

        # Ảnh thiếu — KHÔNG bỏ qua, ghi báo cáo bổ sung tay
        reason = "chua_trich_duoc"
        for pi in photo_issues:
            if pi.get("employee_code") == code:
                reason = pi.get("detail") or pi.get("issue_type") or reason
                break

        rec["parsed"]["photo_status"] = "can_bo_sung_tay"
        manual_row = {
            "employee_code": code,
            "full_name": full_name,
            "row_index": row_idx,
            "expected_file": expected,
            "reason": reason,
            "action": "Copy anh vao photos/{MSNV}.jpg roi chay lai extract hoac import",
        }
        photos_manual.append(manual_row)
        issues.append(
            {
                "employee_code": code,
                "full_name": full_name,
                "row_index": row_idx,
                "issue_type": "missing_photo",
                "missing_fields": "picture",
                "detail": f"CAN_BO_SUNG_TAY: {reason}",
            }
        )

    complete = sum(
        1
        for rec in employees
        if not _missing_fields(rec["parsed"]) and rec["parsed"].get("photo_status") == "extracted"
    )
    data_complete_no_photo = sum(1 for rec in employees if not _missing_fields(rec["parsed"]))

    payload = {
        "schema_version": SCHEMA_VERSION,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(xls_path.resolve()),
        "source_sheet": wb.sheet_names()[0],
        "employee_count": len(employees),
        "employees": [
            {
                "employee_code": rec["parsed"]["employee_code"],
                "row_index": rec["row_index"],
                "profile": rec["parsed"],
                "raw_excel": rec["raw"],
            }
            for rec in sorted(employees, key=lambda r: r["parsed"]["employee_code"] or "")
        ],
    }

    employees_path = out_dir / "employees.json"
    employees_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )

    report_path = out_dir / "BAO_CAO_THIEU.csv"
    with report_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "employee_code",
                "full_name",
                "row_index",
                "issue_type",
                "missing_fields",
                "detail",
            ],
        )
        writer.writeheader()
        for issue in sorted(
            issues,
            key=lambda x: (x["issue_type"], x["employee_code"] or "zzz", x["row_index"]),
        ):
            writer.writerow(issue)

    manual_photo_path = out_dir / "ANH_BO_SUNG_TAY.csv"
    with manual_photo_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "employee_code",
                "full_name",
                "row_index",
                "expected_file",
                "reason",
                "action",
            ],
        )
        writer.writeheader()
        for row in sorted(photos_manual, key=lambda x: x["employee_code"] or ""):
            writer.writerow(row)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "extracted_at": payload["extracted_at"],
        "source_file": payload["source_file"],
        "output_dir": str(out_dir.resolve()),
        "employee_count": len(employees),
        "data_complete_count": data_complete_no_photo,
        "photo_extracted_count": photos_ok,
        "photo_manual_count": len(photos_manual),
        "issue_count": len(issues),
        "embedded_image_signatures": len(embedded),
        "excel_shapes_via_com": excel_shape_count,
        "photos_on_disk": photos_ok,
        "files": {
            "employees_json": str(employees_path.name),
            "report_csv": str(report_path.name),
            "manual_photos_csv": str(manual_photo_path.name),
            "photos_dir": "photos/",
        },
        "notes": [
            "File GenusSuite «full DS» nhúng ảnh dạng Excel Picture shapes (cột D).",
            "Ảnh trích qua Excel COM + clipboard — cần Microsoft Excel trên Windows.",
            "MSNV thiếu ảnh: xem ANH_BO_SUNG_TAY.csv — copy ảnh vào photos/{MSNV}.jpg, không bỏ qua.",
            "Dùng employees.json để nạp test: profile + raw_excel + photos/{MSNV}.jpg.",
        ],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Trích xuất hồ sơ công nhân từ Excel GenusSuite")
    parser.add_argument("--xls", type=Path, default=None, help="Đường dẫn file .xls")
    parser.add_argument("--out", type=Path, default=None, help="Thư mục output")
    parser.add_argument(
        "--no-com-photos",
        action="store_true",
        help="Không thử trích ảnh qua Excel COM (Windows)",
    )
    args = parser.parse_args()

    xls_path = args.xls or default_xls_path()
    out_dir = args.out or default_out_dir(xls_path)

    if not xls_path.is_file():
        raise SystemExit(f"Không tìm thấy file: {xls_path}")

    manifest = extract(xls_path, out_dir, try_com_photos=not args.no_com_photos)
    summary = (
        f"OK: {manifest['employee_count']} NV -> {out_dir / 'employees.json'} | "
        f"du lieu day du: {manifest['data_complete_count']} | "
        f"anh: {manifest['photo_extracted_count']} | "
        f"anh bo sung tay: {manifest.get('photo_manual_count', 0)} | "
        f"canh bao: {manifest['issue_count']} (xem BAO_CAO_THIEU.csv)"
    )
    print(summary)


if __name__ == "__main__":
    main()
