"""Lệnh HR: lọc / mở danh sách chấm lẻ (hôm qua · hôm nay · kỳ) — không tự bịa giờ."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.modules.ai.employee_context import cap_note
from app.modules.ai.schemas import AiSuggestion
from app.modules.attendance.engine import VN_TZ
from app.modules.attendance.review import count_odd_punches, list_odd_punches

CONTEXT_HEADER = "### Chấm lẻ (thiếu vào hoặc ra) — đọc từ CSDL"

_YESTERDAY_RE = re.compile(r"hôm\s*qua|hom\s*qua", re.IGNORECASE)
_TODAY_RE = re.compile(r"hôm\s*nay|hom\s*nay", re.IGNORECASE)
_DAY_BEFORE_RE = re.compile(r"hôm\s*kia", re.IGNORECASE)
_MONTH_RE = re.compile(r"tháng\s*này|kỳ\s*này", re.IGNORECASE)
_DATE_ISO_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_DATE_VN_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b")
_OPEN_RE = re.compile(
    r"mở|lọc|xem\s*ds|danh\s*sách|để\s+tôi\s+chấm|cho\s+tôi\s+chấm",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PunchWindow:
    date_from: date
    date_to: date
    label: str
    single_day: bool
    wants_open: bool


def parse_punch_window(message: str) -> PunchWindow:
    today = datetime.now(tz=VN_TZ).date()
    text = message or ""
    wants_open = bool(_OPEN_RE.search(text))
    if _YESTERDAY_RE.search(text):
        d = today - timedelta(days=1)
        return PunchWindow(d, d, "hôm qua", True, wants_open)
    if _DAY_BEFORE_RE.search(text):
        d = today - timedelta(days=2)
        return PunchWindow(d, d, "hôm kia", True, wants_open)
    iso = _DATE_ISO_RE.search(text)
    if iso:
        d = date.fromisoformat(iso.group(1))
        return PunchWindow(d, d, d.isoformat(), True, wants_open)
    vn = _DATE_VN_RE.search(text)
    if vn:
        day_n, month_n = int(vn.group(1)), int(vn.group(2))
        year_n = int(vn.group(3)) if vn.group(3) else today.year
        try:
            d = date(year_n, month_n, day_n)
        except ValueError:
            d = today
        return PunchWindow(d, d, d.isoformat(), True, wants_open)
    if _TODAY_RE.search(text) and not _MONTH_RE.search(text):
        return PunchWindow(today, today, "hôm nay", True, wants_open)
    month_start = today.replace(day=1)
    return PunchWindow(
        month_start,
        today,
        f"{month_start.isoformat()} → {today.isoformat()}",
        False,
        wants_open,
    )


def punch_review_href(window: PunchWindow) -> str:
    if window.single_day:
        params = {
            "view": "daily",
            "date": window.date_from.isoformat(),
            "period": f"{window.date_from.year:04d}-{window.date_from.month:02d}",
            "odd": "1",
        }
        return "/m/timekeeping?" + urlencode(params)
    return "/m/timekeeping?view=daily"


def build_punch_open(db: Session, message: str, *, limit: int = 20) -> tuple[str, list[AiSuggestion]]:
    window = parse_punch_window(message)
    total = count_odd_punches(db, window.date_from, window.date_to)
    rows = list_odd_punches(db, window.date_from, window.date_to, limit=limit)
    href = punch_review_href(window)
    lines = [
        CONTEXT_HEADER,
        f"Khoảng: {window.label} ({window.date_from.isoformat()} → {window.date_to.isoformat()}).",
        "Luật 01: ghi nhận mốc có, không bịa mốc còn lại, chưa tính công. "
        "HR gọi lập biên bản rồi chấm tay đủ cặp trên lưới ngày — AI không tự điền giờ.",
    ]
    if total == 0:
        lines.append("Không có dòng chấm lẻ.")
    else:
        lines.append(cap_note(total, len(rows), limit))
        for day, emp in rows:
            inn = "có vào" if day.first_in else "thiếu vào"
            out = "có ra" if day.last_out else "thiếu ra"
            lines.append(
                f"- {emp.employee_code} {emp.full_name} {day.work_date.isoformat()} ({inn}, {out})"
            )
    if window.single_day:
        lines.append("Đã lọc lưới ngày «Chỉ chấm lẻ» — HR sửa Vào/Ra trên lưới.")
        label = f"Mở DS lẻ {window.label}"
    else:
        label = "Mở lưới ngày"
    sugg = [AiSuggestion(label=label, href=href)]
    if not window.single_day:
        sugg.append(
            AiSuggestion(
                label="Lẻ hôm qua",
                message="Lọc và mở ds nhân viên lẻ hôm qua",
            )
        )
    return "\n".join(lines), sugg
