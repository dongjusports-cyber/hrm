"""Tra cứu nhanh — không gọi Gemini khi chỉ cần số liệu."""

from app.modules.ai.fast_reply import format_employee_lookup_answer, wants_llm_analysis


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
