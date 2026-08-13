"""Nhãn tiếng Việt cho ngữ cảnh AI."""

from app.modules.ai.vi_labels import (
    label_ai_mode,
    label_dispute_status,
    label_emp_status,
    label_payslip_status,
    label_sync_status,
)


def test_label_emp_status():
    assert label_emp_status("active") == "Chính thức"
    assert label_emp_status("resigned") == "Thôi việc"


def test_label_dispute_and_payslip():
    assert label_dispute_status("ai_reviewed") == "AI đã rà — chờ HR"
    assert label_payslip_status("published") == "Đã phát hành"


def test_label_sync_and_ai_mode():
    assert label_sync_status("partial") == "một phần"
    assert label_ai_mode(stub=True) == "chế độ giả lập"
    assert label_ai_mode(stub=False) == "Gemini"
