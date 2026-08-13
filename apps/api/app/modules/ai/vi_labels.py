"""Nhãn tiếng Việt cho ngữ cảnh AI — đồng bộ với apps/web/src/shared/viLabels.ts."""


def label_emp_status(code: str | None) -> str:
    match (code or "").lower():
        case "active":
            return "Chính thức"
        case "probation":
            return "Thử việc"
        case "resigned":
            return "Thôi việc"
        case "suspended":
            return "Tạm đình chỉ"
        case "maternity":
            return "Thai sản"
        case _:
            return code or "—"


def label_pay_channel(code: str | None) -> str:
    match (code or "").upper():
        case "ATM":
            return "ATM"
        case "CASH":
            return "Tiền mặt"
        case _:
            return code or "—"


def label_period_status(code: str | None) -> str:
    match (code or "").lower():
        case "open":
            return "Đang mở"
        case "calculating":
            return "Đang tính"
        case "calculated":
            return "Đã tính"
        case "published":
            return "Đã phát hành"
        case "locked":
            return "Đã khóa"
        case "closed":
            return "Đã đóng"
        case _:
            return code or "—"


def label_payslip_status(code: str | None) -> str:
    match (code or "").lower():
        case "draft":
            return "Nháp"
        case "calculated":
            return "Đã tính"
        case "published":
            return "Đã phát hành"
        case "confirmed":
            return "CN đã xác nhận"
        case "disputed":
            return "Đang khiếu nại"
        case "resolved":
            return "Đã xử lý (có thể phát hành lại)"
        case _:
            return code or "—"


def label_dispute_status(code: str | None) -> str:
    match (code or "").lower():
        case "open":
            return "Mở"
        case "ai_reviewed":
            return "AI đã rà — chờ HR"
        case "hr_pending":
            return "HR đang xử lý"
        case "closed":
            return "Đã đóng"
        case _:
            return code or "—"


def label_sync_status(code: str | None) -> str:
    match (code or "").lower():
        case "success":
            return "thành công"
        case "partial":
            return "một phần"
        case "error":
            return "lỗi"
        case "running":
            return "đang chạy"
        case "requested":
            return "đã yêu cầu"
        case _:
            return code or "—"


def label_ai_mode(*, stub: bool) -> str:
    return "chế độ giả lập" if stub else "Gemini"


def label_settings_source(code: str | None) -> str:
    match (code or "").lower():
        case "database":
            return "cơ sở dữ liệu"
        case "env":
            return "biến môi trường"
        case "none":
            return "chưa có"
        case _:
            return code or "—"


def label_policy_version(*, package_id, has_snapshot: bool) -> str:
    if package_id:
        return str(package_id)
    if has_snapshot:
        return "ảnh chụp chính sách"
    return "—"
