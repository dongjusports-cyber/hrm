"""Tra cứu nhanh — không gọi Gemini khi chỉ cần số liệu."""

from app.modules.ai.fast_reply import (
    detect_ops_kind,
    format_employee_lookup_answer,
    wants_llm_analysis,
    wants_punch_review,
)


def test_wants_llm_analysis():
    assert wants_llm_analysis("phân tích lương 5290") is True
    assert wants_llm_analysis("so sánh 1519 và 5290") is True
    assert wants_llm_analysis("xem bảng lương 1519") is False
    assert wants_llm_analysis("thông tin MSNV 1519") is False


def test_format_employee_lookup_answer():
    ctx = (
        "### Dữ liệu nhân viên (đọc từ CSDL — chỉ phân tích, không tự sửa)\n"
        "MSNV: 1519 | Họ tên: Test\n"
        "Phiếu lương gần nhất (2026-07): thực lĩnh=100"
    )
    out = format_employee_lookup_answer(ctx)
    assert "Kết quả tra cứu từ hệ thống" in out
    assert "MSNV: 1519" in out
    assert "thực lĩnh=100" in out


def test_wants_punch_review():
    assert wants_punch_review("Ai chấm lẻ tháng này") is True
    assert wants_punch_review("thiếu vào thiếu ra") is True
    assert wants_punch_review("lọc và mở ds nhân viên lẻ hôm qua để tôi chấm công") is True
    assert wants_punch_review("thông tin MSNV 1519") is False


def test_detect_ops_kind():
    assert detect_ops_kind("Tóm tắt việc cần làm hôm nay") == "daily_briefing"
    assert detect_ops_kind("đơn phép chờ duyệt") == "leave_review"
    assert detect_ops_kind("HĐ sắp hết hạn") == "contract_review"
    assert detect_ops_kind("báo BHXH tháng này") == "insurance_review"
    assert detect_ops_kind("phiếu chưa xác nhận") == "payroll_review"
    assert detect_ops_kind("danh sách khiếu nại") == "dispute_list"
    assert detect_ops_kind("chế độ sắp hết hạn") == "wt_review"
    assert detect_ops_kind("sắp mất chuyên cần") == "attendance_risk"
    assert detect_ops_kind("nhân viên thử việc") == "probation_list"
    assert detect_ops_kind("thôi việc tháng này") == "resign_list"
    assert detect_ops_kind("mở bảng công") == "timesheet_open"
    assert detect_ops_kind("lọc và mở ds nhân viên lẻ hôm qua để tôi chấm công") == "punch_review"
    assert detect_ops_kind("nhà máy có bao nhiêu module") == ""


def test_format_punch_context():
    ctx = "### Chấm lẻ (thiếu vào hoặc ra) — đọc từ CSDL\n5290 thiếu ra"
    out = format_employee_lookup_answer(ctx)
    assert "Kết quả rà soát chấm lẻ từ hệ thống" in out
    assert "5290 thiếu ra" in out
