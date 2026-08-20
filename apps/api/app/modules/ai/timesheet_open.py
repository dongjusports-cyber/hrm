"""Lệnh HR: mở / in bảng công (CTY · bộ phận · MSNV) — đọc CSDL, không tự sửa công."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.modules.ai.employee_context import extract_employee_codes, lookup_employees_by_name
from app.modules.ai.schemas import AiSuggestion
from app.modules.attendance.engine import VN_TZ
from app.modules.attendance.timesheet import get_pay_period, list_timesheets
from app.modules.mdm.models import Department, Employee

CONTEXT_HEADER = "### Bảng công — đọc từ CSDL"

_SHEET_RE = re.compile(
    r"bảng\s*công|bang\s*cong|tổng\s*hợp\s*tháng|tong\s*hop\s*thang|"
    r"xuất\s*(?:excel\s*)?(?:bảng\s*)?công|in\s+(?:ra\s+)?(?:bảng\s*)?công",
    re.IGNORECASE,
)
_PRINT_RE = re.compile(
    r"in\s*ra|\bin\b|xuất(?:\s*excel)?|tải(?:\s*excel)?|export|print",
    re.IGNORECASE,
)
_DAILY_RE = re.compile(
    r"hôm\s*nay|lưới\s*ngày|công\s*ngày|bảng\s*công\s*ngày|ngày\s*công",
    re.IGNORECASE,
)
_COMPANY_RE = re.compile(
    r"cả\s*công\s*ty|toàn\s*công\s*ty|\bcty\b|toàn\s*nhà\s*máy|cả\s*nhà\s*máy|"
    r"tất\s*cả|toàn\s*bộ|cả\s*nhà|toàn\s*công",
    re.IGNORECASE,
)
_DEPT_RE = re.compile(
    r"(?:bộ\s*phận|bo\s*phan|phòng(?:\s*ban)?|phong|công\s*đoạn|cong\s*doan|dept)\s+"
    r"([A-Za-z0-9À-ỹ][A-Za-z0-9À-ỹ ._\-]{0,39}?)"
    r"(?=\s+(?:tháng|kỳ|năm|msnv|in\b|xuất|tải|của|hôm\s*nay|lưới)|$)",
    re.IGNORECASE,
)
_PERIOD_ISO = re.compile(r"\b(20\d{2}-\d{2})\b")
_PERIOD_SLASH = re.compile(r"\b(\d{1,2})/(20\d{2})\b")
_PERIOD_VN = re.compile(r"tháng\s+(\d{1,2})(?:\s+năm\s+(20\d{2}))?", re.IGNORECASE)
_STRIP_NOISE = re.compile(
    r"trợ\s*lý\s*ơi|hỏi\s*ai|mở(?:\s*ra)?|xem|hiện|in\s*ra|\bin\b|xuất(?:\s*excel)?|"
    r"tải(?:\s*excel)?|print|export|bảng\s*công|bang\s*cong|tổng\s*hợp\s*tháng|"
    r"cả\s*công\s*ty|toàn\s*công\s*ty|\bcty\b|toàn\s*nhà\s*máy|cả\s*nhà\s*máy|"
    r"tất\s*cả|toàn\s*bộ|hôm\s*nay|lưới\s*ngày|công\s*ngày|"
    r"(?:bộ\s*phận|phòng(?:\s*ban)?|công\s*đoạn|dept)\s+[A-Za-z0-9À-ỹ ._\-]{1,40}|"
    r"tháng\s+\d{1,2}(?:\s+năm\s+20\d{2})?|kỳ\s+20\d{2}-\d{2}|20\d{2}-\d{2}|"
    r"\d{1,2}/20\d{2}|msnv|nhân\s*viên|theo\s*lệnh|cho\s+hr|giúp",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TimesheetOpenIntent:
    view: str
    period: str
    wants_print: bool
    scope: str
    dept_token: str = ""
    employee_code: str = ""
    leftover: str = ""


def wants_timesheet_open(message: str) -> bool:
    return bool(_SHEET_RE.search((message or "").strip()))


def _vn_today_period() -> str:
    today = datetime.now(tz=VN_TZ).date()
    return f"{today.year:04d}-{today.month:02d}"


def _extract_period(text: str) -> str:
    if re.search(r"tháng\s*này|kỳ\s*này", text, re.IGNORECASE):
        return _vn_today_period()
    iso = _PERIOD_ISO.search(text)
    if iso:
        return iso.group(1)
    slash = _PERIOD_SLASH.search(text)
    if slash:
        return f"{int(slash.group(2)):04d}-{int(slash.group(1)):02d}"
    vn = _PERIOD_VN.search(text)
    if vn:
        month = int(vn.group(1))
        year = int(vn.group(2)) if vn.group(2) else datetime.now(tz=VN_TZ).year
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"
    return _vn_today_period()


def _leftover(text: str) -> str:
    rest = _STRIP_NOISE.sub(" ", text)
    rest = re.sub(r"\s+", " ", rest).strip(" ?!.,;:\"'«»")
    if len(rest) < 2 or len(rest) > 60:
        return ""
    if rest.lower() in {"ra", "đi", "hộ", "với", "của", "nhé", "ạ"}:
        return ""
    return rest


def parse_timesheet_open(message: str) -> TimesheetOpenIntent | None:
    text = (message or "").strip()
    if not text or not wants_timesheet_open(text):
        return None
    period = _extract_period(text)
    wants_print = bool(_PRINT_RE.search(text))
    view = "daily" if _DAILY_RE.search(text) else "monthly"
    company = bool(_COMPANY_RE.search(text))
    dept_m = _DEPT_RE.search(text)
    dept_token = (dept_m.group(1).strip() if dept_m else "").strip(" .,-")
    codes = extract_employee_codes(text)
    leftover = _leftover(text)
    employee_code = codes[0] if codes else ""
    scope = "company"
    if dept_token:
        scope = "dept"
    elif employee_code:
        scope = "emp"
    elif leftover:
        scope = "leftover"
    if company and not dept_token:
        scope = "company"
        employee_code = ""
        leftover = ""
    return TimesheetOpenIntent(
        view=view,
        period=period,
        wants_print=wants_print,
        scope=scope,
        dept_token=dept_token,
        employee_code=employee_code,
        leftover=leftover,
    )


def find_departments(db: Session, token: str, *, limit: int = 8) -> list[Department]:
    raw = (token or "").strip()
    if len(raw) < 1:
        return []
    t = raw.lower()
    exact = (
        db.query(Department)
        .filter(func.lower(Department.code) == t)
        .order_by(Department.sort_order, Department.code)
        .all()
    )
    if exact:
        return exact
    like = f"%{t}%"
    return (
        db.query(Department)
        .filter(
            or_(
                func.lower(Department.code).like(like),
                func.lower(Department.name).like(like),
                and_(
                    Department.name_local.isnot(None),
                    func.lower(Department.name_local).like(like),
                ),
            )
        )
        .order_by(Department.sort_order, Department.code)
        .limit(limit)
        .all()
    )


def _daily_date(period: str) -> str:
    today = datetime.now(tz=VN_TZ).date()
    if f"{today.year:04d}-{today.month:02d}" == period:
        return today.isoformat()
    return f"{period}-01"


def portal_href(
    *,
    view: str,
    period: str,
    dept: Department | None = None,
    employee_code: str = "",
) -> str:
    params: dict[str, str] = {"view": view, "period": period}
    if view == "daily":
        params["date"] = _daily_date(period)
    if dept is not None:
        params["dept"] = dept.code
    if employee_code:
        params["q"] = employee_code
    return "/m/timekeeping?" + urlencode(params)


def excel_href(
    *,
    period: str,
    dept: Department | None = None,
    employee_code: str = "",
) -> str:
    q: dict[str, str] = {}
    if dept is not None:
        q["department_code"] = dept.code
    if employee_code:
        q["employee_code"] = employee_code
    path = f"/api/attendance/timesheets/{period}/export"
    if q:
        path += "?" + urlencode(q)
    return path


def _scope_label(
    *,
    scope: str,
    dept: Department | None,
    employee_code: str,
    emp_name: str = "",
) -> str:
    if dept is not None:
        return f"bộ phận {dept.code} ({dept.name})"
    if employee_code:
        who = f"{employee_code} {emp_name}".strip()
        return f"MSNV {who}"
    if scope == "company":
        return "toàn công ty"
    return "phạm vi đã chọn"


def _count_rows(
    db: Session,
    period: str,
    *,
    department_id: UUID | None = None,
    employee_code: str | None = None,
) -> int:
    pay = get_pay_period(db, period)
    if pay is None:
        return 0
    return len(
        list_timesheets(
            db,
            period,
            employee_code=employee_code,
            department_id=department_id,
        )
    )


def _suggestions(
    *,
    view: str,
    period: str,
    wants_print: bool,
    dept: Department | None = None,
    employee_code: str = "",
) -> list[AiSuggestion]:
    page = portal_href(view=view, period=period, dept=dept, employee_code=employee_code)
    out = [AiSuggestion(label="Mở bảng công", href=page)]
    if wants_print:
        out.insert(
            0,
            AiSuggestion(
                label="Tải Excel",
                href=excel_href(period=period, dept=dept, employee_code=employee_code),
            ),
        )
    return out


def _answer_lines(
    *,
    period: str,
    scope_label: str,
    view: str,
    n: int,
    has_period: bool,
    wants_print: bool,
    extra: str = "",
) -> str:
    view_label = "lưới ngày" if view == "daily" else "tổng hợp tháng"
    lines = [
        CONTEXT_HEADER,
        f"Kỳ {period} · {scope_label} · {view_label}.",
        "AI không tự sửa giờ công, không tự tổng hợp lại, không tự tính lương.",
    ]
    if extra:
        lines.append(extra)
    if not has_period:
        lines.append(
            f"Chưa có kỳ lương {period} trên CSDL — trang Chấm Công vẫn mở được; "
            "HR bấm Tổng hợp công nếu cần số liệu."
        )
    elif n == 0:
        lines.append(f"Kỳ {period} có 0 dòng bảng công (chưa tổng hợp hoặc không khớp lọc).")
    else:
        lines.append(f"Số dòng bảng công khớp lọc: {n}.")
    if wants_print:
        lines.append("Lệnh in → tải Excel (không dùng window.print lưới).")
    return "\n".join(lines)


def build_timesheet_open(db: Session, message: str) -> tuple[str, list[AiSuggestion]]:
    intent = parse_timesheet_open(message)
    if intent is None:
        return "", []

    dept: Department | None = None
    employee_code = intent.employee_code
    emp_name = ""

    token = intent.dept_token or (intent.leftover if intent.scope == "leftover" else "")
    if intent.scope == "dept":
        found = find_departments(db, intent.dept_token)
        if not found:
            ctx = _answer_lines(
                period=intent.period,
                scope_label=f"bộ phận «{intent.dept_token}»",
                view=intent.view,
                n=0,
                has_period=get_pay_period(db, intent.period) is not None,
                wants_print=False,
                extra=f"Không tìm thấy bộ phận «{intent.dept_token}». Nói lại mã (vd. SW1) hoặc tên (May 1).",
            )
            return ctx, []
        if len(found) > 1:
            lines = [
                CONTEXT_HEADER,
                f"Kỳ {intent.period}. Có {len(found)} bộ phận khớp «{intent.dept_token}» — chọn một:",
            ]
            sugg: list[AiSuggestion] = []
            for d in found:
                lines.append(f"- {d.code} {d.name}")
                sugg.append(
                    AiSuggestion(
                        label=f"Mở {d.code}",
                        href=portal_href(
                            view=intent.view, period=intent.period, dept=d, employee_code=""
                        ),
                    )
                )
            return "\n".join(lines), sugg
        dept = found[0]
    elif intent.scope == "leftover" and token:
        found = find_departments(db, token)
        if len(found) == 1:
            dept = found[0]
        else:
            emps, total = lookup_employees_by_name(db, token, limit=5)
            if total == 1 and emps:
                employee_code = emps[0].employee_code
                emp_name = emps[0].full_name
            elif total > 1:
                lines = [
                    CONTEXT_HEADER,
                    f"Kỳ {intent.period}. Có {total} NV khớp «{token}» (hiện {len(emps)}):",
                ]
                sugg = []
                for emp in emps:
                    lines.append(f"- {emp.employee_code} {emp.full_name}")
                    sugg.append(
                        AiSuggestion(
                            label=f"Công {emp.employee_code}",
                            href=portal_href(
                                view=intent.view,
                                period=intent.period,
                                employee_code=emp.employee_code,
                            ),
                        )
                    )
                return "\n".join(lines), sugg
            elif found:
                lines = [
                    CONTEXT_HEADER,
                    f"Kỳ {intent.period}. Có {len(found)} bộ phận khớp «{token}» — chọn một:",
                ]
                sugg = []
                for d in found:
                    lines.append(f"- {d.code} {d.name}")
                    sugg.append(
                        AiSuggestion(
                            label=f"Mở {d.code}",
                            href=portal_href(view=intent.view, period=intent.period, dept=d),
                        )
                    )
                return "\n".join(lines), sugg
            else:
                ctx = _answer_lines(
                    period=intent.period,
                    scope_label=f"«{token}»",
                    view=intent.view,
                    n=0,
                    has_period=get_pay_period(db, intent.period) is not None,
                    wants_print=False,
                    extra=f"Không khớp bộ phận hay MSNV «{token}».",
                )
                return ctx, []
    elif employee_code:
        emp = (
            db.query(Employee)
            .filter(Employee.employee_code == employee_code, Employee.deleted_at.is_(None))
            .one_or_none()
        )
        if emp is None:
            ctx = _answer_lines(
                period=intent.period,
                scope_label=f"MSNV {employee_code}",
                view=intent.view,
                n=0,
                has_period=get_pay_period(db, intent.period) is not None,
                wants_print=False,
                extra=f"Không tìm thấy MSNV {employee_code}.",
            )
            return ctx, []
        emp_name = emp.full_name

    has_period = get_pay_period(db, intent.period) is not None
    n = _count_rows(
        db,
        intent.period,
        department_id=dept.id if dept else None,
        employee_code=employee_code or None,
    )
    label = _scope_label(
        scope=intent.scope, dept=dept, employee_code=employee_code, emp_name=emp_name
    )
    ctx = _answer_lines(
        period=intent.period,
        scope_label=label,
        view=intent.view,
        n=n,
        has_period=has_period,
        wants_print=intent.wants_print,
    )
    return ctx, _suggestions(
        view=intent.view,
        period=intent.period,
        wants_print=intent.wants_print,
        dept=dept,
        employee_code=employee_code,
    )
