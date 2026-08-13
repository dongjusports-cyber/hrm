"""Unit tests — parse MSNV cho AI tra cứu."""

from app.modules.ai.employee_context import extract_employee_codes


def test_extract_msnv_keyword():
    assert extract_employee_codes("Lấy thông tin MSNV 1519") == ["1519"]
    assert extract_employee_codes("nhân viên 5290 là ai?") == ["5290"]


def test_extract_bare_code():
    assert extract_employee_codes("tra cứu 1519") == ["1519"]


def test_skip_year_like():
    assert extract_employee_codes("kỳ lương 2025-10") == []


def test_max_codes():
    codes = extract_employee_codes("so sánh 1519 5290 1643 1732")
    assert len(codes) <= 3
