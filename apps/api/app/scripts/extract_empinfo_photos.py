"""Trích ảnh cột D từ file GenusSuite .xls — chạy riêng (subprocess) để tránh lỗi clipboard."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import win32com.client
from PIL import Image, ImageGrab


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip())


def _parse_msnv(raw: Any) -> str | None:
    if raw in ("", None):
        return None
    text = str(raw).strip().lower()
    if text in {"dept", "empid", "id", "total:"} or text.startswith("total"):
        return None
    try:
        return str(int(float(raw)))
    except (TypeError, ValueError):
        return str(raw).strip() or None


def _row_for_shape(ws: Any, shape: Any, *, last_row: int) -> int | None:
    best_row: int | None = None
    best_dist = 1e9
    for row in range(4, last_row + 1):
        if not _parse_msnv(ws.Cells(row, 2).Value):
            continue
        cell = ws.Cells(row, 2)
        dist = abs(float(shape.Top) - float(cell.Top))
        if dist < best_dist:
            best_dist = dist
            best_row = row
    return best_row


def _save_image(img: Image.Image, dest: Path) -> bool:
    if img.width < 20 or img.height < 20:
        return False
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=90)
    return dest.stat().st_size >= 500


def _grab_after_copy(excel: Any) -> Image.Image | None:
    for _ in range(4):
        try:
            img = ImageGrab.grabclipboard()
        except OSError:
            img = None
        if isinstance(img, Image.Image):
            return img
        time.sleep(0.12)
    excel.CutCopyMode = False
    return None


def extract_photos(xls_path: Path, out_photos: Path) -> dict[str, Any]:
    out_photos.mkdir(parents=True, exist_ok=True)
    work = out_photos.parent / "_excel_tmp"
    work.mkdir(parents=True, exist_ok=True)
    ascii_xls = work / "source.xls"
    if not ascii_xls.exists() or ascii_xls.stat().st_size != xls_path.stat().st_size:
        shutil.copy2(xls_path, ascii_xls)

    mapping: dict[str, str] = {}
    issues: list[dict[str, Any]] = []

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    wb = excel.Workbooks.Open(str(ascii_xls.resolve()), ReadOnly=True)
    if wb is None:
        excel.Quit()
        raise RuntimeError("Không mở được file Excel")

    ws = wb.Worksheets(1)
    n_shapes = int(ws.Shapes.Count)
    last_row = int(ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1)
    print(f"shapes={n_shapes}", flush=True)

    for i in range(1, n_shapes + 1):
        sh = ws.Shapes(i)
        row = _row_for_shape(ws, sh, last_row=last_row + 5)
        if row is None:
            issues.append(
                {
                    "employee_code": "",
                    "full_name": "",
                    "row_index": 0,
                    "issue_type": "photo_unmapped",
                    "detail": f"shape #{i} khong map duoc dong",
                }
            )
            continue

        msnv = _parse_msnv(ws.Cells(row, 2).Value)
        full_name = _norm(str(ws.Cells(row, 3).Value or ""))
        if not msnv:
            continue

        dest = out_photos / f"{msnv}.jpg"
        if dest.is_file() and dest.stat().st_size >= 500:
            mapping[msnv] = dest.name
            continue

        sh.Copy()
        time.sleep(0.15)
        img = _grab_after_copy(excel)
        excel.CutCopyMode = False

        if img is None:
            issues.append(
                {
                    "employee_code": msnv,
                    "full_name": full_name,
                    "row_index": row,
                    "issue_type": "missing_photo",
                    "detail": "clipboard_empty",
                }
            )
        elif not _save_image(img, dest):
            dest.unlink(missing_ok=True)
            issues.append(
                {
                    "employee_code": msnv,
                    "full_name": full_name,
                    "row_index": row,
                    "issue_type": "missing_photo",
                    "detail": "placeholder_or_too_small",
                }
            )
        else:
            mapping[msnv] = dest.name

        if i % 25 == 0 or i == n_shapes:
            print(f"  {i}/{n_shapes} ok={len(mapping)} miss={len(issues)}", flush=True)

    wb.Close(SaveChanges=False)
    excel.Quit()

    report = {
        "shape_count": n_shapes,
        "photo_ok": len(mapping),
        "photo_issues": len(issues),
        "mapping": mapping,
        "issues": issues,
    }
    (out_photos.parent / "photos_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("xls", type=Path)
    parser.add_argument("out_photos", type=Path)
    args = parser.parse_args()
    report = extract_photos(args.xls, args.out_photos)
    print(
        f"photos OK: {report['photo_ok']}/{report['shape_count']} | "
        f"issues: {report['photo_issues']}"
    )
    if report["photo_ok"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
