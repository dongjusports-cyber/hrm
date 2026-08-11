"""Lý do khiếu nại — mã cố định (không AI trên Worker)."""

REASON_CHOICES: list[tuple[str, str]] = [
    ("wrong_days", "Sai số ngày công / nghỉ"),
    ("wrong_ot", "Sai tăng ca (OT)"),
    ("wrong_allowance", "Sai phụ cấp / chuyên cần"),
    ("wrong_insurance", "Sai BHXH / BHYT / BHTN / công đoàn"),
    ("wrong_net", "Sai thực lãnh"),
    ("other", "Lý do khác"),
]

REASON_LABELS = {code: label for code, label in REASON_CHOICES}


def is_valid_reason(code: str) -> bool:
    return code in REASON_LABELS
