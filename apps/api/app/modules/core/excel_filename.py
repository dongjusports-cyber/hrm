"""Tên file Excel xuất ra.

Lương / OT / KPI / chu kỳ: tháng.năm kỳ đang xuất
  → Lương 08.2026 công ty Dongju Sports VN.xlsx
Danh sách NV: ngày bấm xuất (giờ VN)
  → Danh sách nhân viên 20.08.2026 công ty Dongju Sports VN.xlsx
Windows không cho dấu / nên dùng chấm.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

COMPANY_SUFFIX = "công ty Dongju Sports VN"
_VN = timezone(timedelta(hours=7))

_VI_FOLD = str.maketrans(
    "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
    "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ",
    "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
    "AAAAAAAAAAAAAAAAAEEEEEEEEEEEIIIIIOOOOOOOOOOOOOOOOOUUUUUUUUUUUYYYYYD",
)


def month_year_tag(period: str | None = None) -> str:
    """2026-08 → 08.2026. period=None → tháng hiện tại (VN)."""
    if period and period.strip():
        year_s, month_s, *_rest = f"{period.strip()}-01".split("-")
        return f"{int(month_s):02d}.{year_s}"
    now = datetime.now(_VN)
    return f"{now.month:02d}.{now.year}"


def export_day_tag(as_of: date | None = None) -> str:
    """20.08.2026 — ngày xuất hiện tại (VN)."""
    d = as_of or datetime.now(_VN).date()
    return d.strftime("%d.%m.%Y")


def company_excel_filename(
    label: str,
    *,
    period: str | None = None,
    extra: str | None = None,
    on_export_day: bool = False,
    as_of: date | None = None,
) -> str:
    stamp = export_day_tag(as_of) if (on_export_day or as_of is not None) else month_year_tag(period)
    parts = [label.strip(), stamp]
    if extra and extra.strip():
        parts.append(extra.strip())
    parts.append(COMPANY_SUFFIX)
    return f"{' '.join(parts)}.xlsx"


def ascii_filename_fallback(filename: str) -> str:
    folded = filename.translate(_VI_FOLD)
    safe = "".join(ch if ch.isascii() and ch not in '\\/:"*?<>|' else "_" for ch in folded)
    safe = "_".join(safe.split())
    return safe or "download.xlsx"


def attachment_content_disposition(filename: str) -> str:
    """RFC 5987 — trình duyệt lấy filename* (tiếng Việt), ASCII là dự phòng."""
    fallback = ascii_filename_fallback(filename)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"
