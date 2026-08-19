"""GET /api/ai/inbox — một round-trip cho badge + việc cần làm + gợi ý HR."""

from __future__ import annotations

from app.modules.ai.schemas import AiInboxOut, AiSuggestion, TodoCardOut
from app.modules.ai.service import count_unread_visible, list_mine
from app.modules.ai.todos import compute_todo_cards
from app.modules.core.models import User
from sqlalchemy.orm import Session

_ASK: dict[str, tuple[str, str]] = {
    "punch_odd_current": ("Ai chấm lẻ?", "Ai chấm lẻ tháng này"),
    "leave_requests_pending": ("Đơn phép chờ?", "Đơn phép chờ duyệt"),
    "attendance_penalty_risk": ("Chuyên cần?", "Sắp mất chuyên cần"),
    "expiring_contracts_60d": ("HĐ hết hạn?", "Hợp đồng sắp hết hạn"),
    "wt_regime_expiring": ("Chế độ T−3?", "Chế độ sắp hết hạn"),
    "payslip_unconfirmed": ("Phiếu chưa XN?", "Phiếu lương chưa xác nhận"),
    "open_disputes": ("Khiếu nại?", "Danh sách khiếu nại đang mở"),
    "insurance_declarations_pending": ("BHXH chưa nộp?", "Báo BHXH tháng này chưa nộp"),
}


def suggestions_from_cards(cards: list[TodoCardOut]) -> list[AiSuggestion]:
    out = [
        AiSuggestion(
            label="Tóm tắt hôm nay",
            message="Tóm tắt việc cần làm hôm nay",
            href=None,
        )
    ]
    for card in cards:
        pair = _ASK.get(card.key)
        msg = card.ask_message or (pair[1] if pair else "")
        label = pair[0] if pair else card.title[:24]
        if not msg:
            continue
        out.append(AiSuggestion(label=label, message=msg, href=card.href))
    return out[:8]


def followups_for_kind(kind: str) -> list[AiSuggestion]:
    mapping: dict[str, list[AiSuggestion]] = {
        "punch_review": [
            AiSuggestion(label="Mở lưới ngày", href="/m/timekeeping?view=daily"),
        ],
        "leave_review": [
            AiSuggestion(label="Duyệt phép", href="/m/timekeeping?view=leave"),
        ],
        "attendance_risk": [
            AiSuggestion(label="Tổng hợp tháng", href="/m/timekeeping?view=monthly"),
        ],
        "contract_review": [
            AiSuggestion(label="Hợp đồng", href="/m/hr/contracts"),
        ],
        "wt_review": [
            AiSuggestion(label="Chế độ đặc biệt", href="/m/hr/lists/special_regime"),
        ],
        "insurance_review": [
            AiSuggestion(label="Bảo hiểm", href="/m/insurance"),
        ],
        "payroll_review": [
            AiSuggestion(label="Tính lương", href="/m/payroll"),
        ],
        "dispute_list": [
            AiSuggestion(label="Khiếu nại", href="/m/dispute"),
        ],
        "daily_briefing": [
            AiSuggestion(label="Chấm công", href="/m/timekeeping?view=daily"),
            AiSuggestion(label="Nhân sự", href="/m/hr"),
        ],
        "employee_lookup": [
            AiSuggestion(label="Hồ sơ NV", href="/m/hr"),
        ],
        "probation_list": [
            AiSuggestion(label="Tab thử việc", href="/m/hr/lists/probation"),
        ],
        "resign_list": [
            AiSuggestion(label="Tab thôi việc", href="/m/hr/lists/resigned"),
        ],
    }
    return mapping.get(kind, [])


def build_inbox(db: Session, user: User, *, light: bool, evaluate: bool) -> AiInboxOut:
    todos = compute_todo_cards(db, user)
    if light:
        return AiInboxOut(
            unread_count=count_unread_visible(db, user),
            todo_total=todos.total,
            light=True,
            message="Badge (không chạy rule KPI).",
        )
    alerts = list_mine(db, user, evaluate=evaluate)
    return AiInboxOut(
        unread_count=alerts.unread_count,
        todo_total=todos.total,
        light=False,
        alerts=alerts.alerts,
        cards=todos.cards,
        suggestions=suggestions_from_cards(todos.cards),
        message="Việc cần làm + nhắc việc (0 token).",
    )
