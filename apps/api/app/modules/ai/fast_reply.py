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


def wants_llm_analysis(message: str) -> bool:
    return bool(_ANALYSIS_RE.search((message or "").strip()))


def format_employee_lookup_answer(context_block: str) -> str:
    """Định dạng khối ngữ cảnh CSDL thành câu trả lời đọc được."""
    body = context_block.strip()
    if body.startswith("### Tra cứu nhân viên"):
        return body.replace("### Tra cứu nhân viên\n", "", 1).strip()
    header = "### Dữ liệu nhân viên (đọc từ CSDL — chỉ phân tích, không tự sửa)"
    if body.startswith(header):
        body = body[len(header) :].strip()
    if not body:
        return "Không có dữ liệu tra cứu."
    parts = [p.strip() for p in body.split("\n\n") if p.strip()]
    lines = ["Kết quả tra cứu từ hệ thống:", ""]
    for i, block in enumerate(parts):
        if i > 0:
            lines.append("")
        lines.extend(block.splitlines())
    return "\n".join(lines)
