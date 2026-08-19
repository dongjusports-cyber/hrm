"""Trả lời nhanh — tra cứu MSNV không gọi Gemini khi chỉ cần số liệu."""

from __future__ import annotations

import re

# Câu hỏi cần suy luận → vẫn gọi Gemini (chậm hơn nhưng có phân tích).
_ANALYSIS_RE = re.compile(
    r"phân\s*tích|so\s*sánh|đề\s*xuất|tại\s*sao|vì\s*sao|giải\s*thích|"
    r"rà\s*soát|đánh\s*giá|nhận\s*xét|lệch|sai\s*ở|nguyên\s*nhân|"
    r"tư\s*vấn|nên\s+làm|bước\s+tiếp",
    re.IGNORECASE,
)

_PUNCH_REVIEW_RE = re.compile(
    r"chấm\s*lẻ|thiếu\s*(?:punch|vân\s*tay|chấm|công)|quên\s*bấm|"
    r"thiếu\s*vào|thiếu\s*ra|không\s*bấm\s*ra|không\s*bấm\s*vào|"
    r"ai\s+quên\s+chấm|danh\s*sách\s*thiếu\s*công",
    re.IGNORECASE,
)
_LEAVE_REVIEW_RE = re.compile(
    r"đơn\s*phép|phép\s*chờ|chờ\s*duyệt\s*phép|duyệt\s*phép|leave\s*request",
    re.IGNORECASE,
)
_CONTRACT_REVIEW_RE = re.compile(
    r"hợp\s*đồng\s*(?:sắp\s*)?hết|hết\s*hạn\s*(?:hđ|hợp\s*đồng)|hđ\s*sắp",
    re.IGNORECASE,
)
_INSURANCE_REVIEW_RE = re.compile(
    r"báo\s*bhxh|tờ\s*khai\s*bh|bhxh\s*(?:tháng|chưa)|khai\s*bảo\s*hiểm",
    re.IGNORECASE,
)
_PAYROLL_OPS_RE = re.compile(
    r"phiếu\s*(?:lương\s*)?chưa\s*xác\s*nhận|kỳ\s*(?:lương\s*)?chưa\s*khóa|"
    r"chưa\s*phát\s*hành|ngày\s*trả\s*lương",
    re.IGNORECASE,
)
_DISPUTE_LIST_RE = re.compile(
    r"khiếu\s*nại\s*(?:đang\s*)?(?:mở|mở)|danh\s*sách\s*khiếu\s*nại",
    re.IGNORECASE,
)
_WT_REVIEW_RE = re.compile(
    r"chế\s*độ\s*(?:sắp\s*)?hết|thai\s*sản\s*sắp|nuôi\s*con\s*sắp|về\s*sớm\s*sắp",
    re.IGNORECASE,
)
_ATTENDANCE_RISK_RE = re.compile(
    r"mất\s*chuyên\s*cần|phạt\s*chuyên\s*cần|nguy\s*cơ\s*chuyên\s*cần|"
    r"trễ\s*.*sớm|sắp\s*mất\s*chuyên\s*cần",
    re.IGNORECASE,
)

_BRIEFING_RE = re.compile(
    r"tóm\s*tắt\s*(?:việc|ngày|hôm\s*nay)|việc\s*cần\s*làm|"
    r"hôm\s*nay\s*(?:làm\s*gì|cần|ưu\s*tiên)|ưu\s*tiên\s*hôm\s*nay|"
    r"briefing|việc\s*hôm\s*nay",
    re.IGNORECASE,
)

_DIRECT_HEADERS: tuple[tuple[str, str], ...] = (
    (
        "### Dữ liệu nhân viên (đọc từ CSDL — chỉ phân tích, không tự sửa)",
        "Kết quả tra cứu từ hệ thống:",
    ),
    ("### Chấm lẻ (thiếu vào hoặc ra) — đọc từ CSDL", "Kết quả rà soát chấm lẻ từ hệ thống:"),
    ("### Đơn phép chờ duyệt — đọc từ CSDL", "Kết quả đơn phép từ hệ thống:"),
    ("### Hợp đồng hết hạn trong 60 ngày — đọc từ CSDL", "Kết quả hợp đồng từ hệ thống:"),
    ("### Báo BHXH tháng chưa nộp — đọc từ CSDL", "Kết quả BHXH từ hệ thống:"),
    ("### Phiếu lương / khóa kỳ — đọc từ CSDL", "Kết quả lương từ hệ thống:"),
    ("### Khiếu nại đang mở — đọc từ CSDL", "Kết quả khiếu nại từ hệ thống:"),
    ("### Chế độ về sớm hết hạn T−3 — đọc từ CSDL", "Kết quả chế độ từ hệ thống:"),
    ("### Nguy cơ chuyên cần kỳ hiện tại — đọc từ CSDL", "Kết quả chuyên cần từ hệ thống:"),
    ("### Việc cần làm hôm nay — đọc từ CSDL", "Tóm tắt việc cần làm hôm nay:"),
)


def wants_llm_analysis(message: str) -> bool:
    return bool(_ANALYSIS_RE.search((message or "").strip()))


def wants_punch_review(message: str) -> bool:
    return bool(_PUNCH_REVIEW_RE.search((message or "").strip()))


def detect_ops_kind(message: str) -> str:
    """Loại câu hỏi nghiệp vụ nhà máy (không gồm tra cứu MSNV)."""
    text = (message or "").strip()
    if not text:
        return ""
    if _BRIEFING_RE.search(text):
        return "daily_briefing"
    if wants_punch_review(text):
        return "punch_review"
    if _LEAVE_REVIEW_RE.search(text):
        return "leave_review"
    if _CONTRACT_REVIEW_RE.search(text):
        return "contract_review"
    if _INSURANCE_REVIEW_RE.search(text):
        return "insurance_review"
    if _PAYROLL_OPS_RE.search(text):
        return "payroll_review"
    if _DISPUTE_LIST_RE.search(text):
        return "dispute_list"
    if _WT_REVIEW_RE.search(text):
        return "wt_review"
    if _ATTENDANCE_RISK_RE.search(text):
        return "attendance_risk"
    return ""


def format_employee_lookup_answer(context_block: str) -> str:
    """Định dạng khối ngữ cảnh CSDL thành câu trả lời đọc được."""
    body = context_block.strip()
    if not body:
        return "Không có dữ liệu tra cứu."
    if body.startswith("### Tra cứu nhân viên"):
        return body.replace("### Tra cứu nhân viên\n", "", 1).strip()
    for header, intro in _DIRECT_HEADERS:
        if body.startswith(header):
            rest = body[len(header) :].strip()
            return f"{intro}\n\n{rest}" if rest else intro
    parts = [p.strip() for p in body.split("\n\n") if p.strip()]
    lines = ["Kết quả tra cứu từ hệ thống:", ""]
    for i, block in enumerate(parts):
        if i > 0:
            lines.append("")
        lines.extend(block.splitlines())
    return "\n".join(lines)
