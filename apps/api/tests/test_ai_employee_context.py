"""Unit tests — parse MSNV / họ tên cho AI tra cứu."""

from app.modules.ai.employee_context import extract_employee_codes, extract_employee_name_query


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


def test_extract_name_query():
    assert extract_employee_name_query("Thông tin Lê Văn C") == "Lê Văn C"
    assert extract_employee_name_query("hồ sơ nhân viên Nguyễn Thị A") == "Nguyễn Thị A"
    assert extract_employee_name_query("nhân viên Lê Văn C là ai?") == "Lê Văn C"
    assert extract_employee_name_query("Thông tin MSNV 1519") == ""
    assert extract_employee_name_query("Ai chấm lẻ tháng này") == ""
    assert extract_employee_name_query("Tóm tắt việc cần làm hôm nay") == ""
    assert extract_employee_name_query("danh sách thử việc") == ""
