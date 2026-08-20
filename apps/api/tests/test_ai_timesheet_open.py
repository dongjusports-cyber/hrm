"""Lệnh mở / in bảng công — parse không cần DB."""

from app.modules.ai.fast_reply import detect_ops_kind, format_employee_lookup_answer
from app.modules.ai.timesheet_open import parse_timesheet_open, wants_timesheet_open


def test_wants_timesheet_open_phrases():
    assert wants_timesheet_open("mở bảng công") is True
    assert wants_timesheet_open("In bảng công cả công ty") is True
    assert wants_timesheet_open("xuất excel bảng công bộ phận SW1") is True
    assert wants_timesheet_open("tổng hợp tháng 5290") is True
    assert wants_timesheet_open("thông tin MSNV 1519") is False
    assert wants_timesheet_open("Ai chấm lẻ tháng này") is False


def test_detect_ops_kind_timesheet_vs_punch():
    assert detect_ops_kind("mở bảng công") == "timesheet_open"
    assert detect_ops_kind("bảng công 5290") == "timesheet_open"
    assert detect_ops_kind("in bảng công bộ phận May 1") == "timesheet_open"
    assert detect_ops_kind("Ai chấm lẻ tháng này") == "punch_review"
    assert detect_ops_kind("thông tin 5290") == ""


def test_parse_timesheet_open_company_print():
    intent = parse_timesheet_open("In bảng công cả công ty tháng 8 năm 2026")
    assert intent is not None
    assert intent.scope == "company"
    assert intent.wants_print is True
    assert intent.view == "monthly"
    assert intent.period == "2026-08"


def test_parse_timesheet_open_dept_and_emp():
    dept = parse_timesheet_open("mở bảng công bộ phận SW1")
    assert dept is not None
    assert dept.scope == "dept"
    assert dept.dept_token.upper() == "SW1"
    assert dept.wants_print is False

    emp = parse_timesheet_open("mở bảng công 5290")
    assert emp is not None
    assert emp.scope == "emp"
    assert emp.employee_code == "5290"


def test_parse_timesheet_open_daily_today():
    intent = parse_timesheet_open("mở bảng công hôm nay")
    assert intent is not None
    assert intent.view == "daily"


def test_format_timesheet_open_answer():
    ctx = "### Bảng công — đọc từ CSDL\nKỳ 2026-08 · toàn công ty."
    out = format_employee_lookup_answer(ctx)
    assert "Kết quả bảng công từ hệ thống" in out
    assert "2026-08" in out
