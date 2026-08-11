"""Lớp B — POST /api/ai/query (P4.5). Read-only; cần quyền ai_query."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.ai.models import AiJob
from app.modules.ai.provider import SYSTEM_PROMPT_BASE, generate_text, resolve_api_key
from app.modules.ai.schemas import AiQueryRequest, AiQueryResponse
from app.modules.ai.settings_svc import ensure_settings
from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.core.models import User
from app.modules.dispute.models import Dispute
from app.modules.dispute.reasons import REASON_LABELS
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip, PolicySnapshot


def _queries_today(db: Session, user_id: UUID) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(AiJob.id))
        .filter(AiJob.user_id == user_id, AiJob.created_at >= start)
        .scalar()
        or 0
    )


def _dispute_context(db: Session, dispute_id: UUID) -> tuple[Dispute, str]:
    row = (
        db.query(Dispute, Employee, Payslip, PayPeriod, TimesheetMonth, PolicySnapshot)
        .join(Employee, Employee.id == Dispute.employee_id)
        .join(Payslip, Payslip.id == Dispute.payslip_id)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .outerjoin(
            TimesheetMonth,
            (TimesheetMonth.pay_period_id == Payslip.pay_period_id)
            & (TimesheetMonth.employee_id == Payslip.employee_id),
        )
        .outerjoin(PolicySnapshot, PolicySnapshot.id == Payslip.policy_snapshot_id)
        .filter(Dispute.id == dispute_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy khiếu nại để rà soát.",
        )
    d, emp, slip, pay, ts, snap = row
    period = f"{pay.year:04d}-{pay.month:02d}"
    reason = REASON_LABELS.get(d.reason_code, d.reason_code)
    policy_ver = str(snap.package_id) if snap and snap.package_id else ("snapshot" if snap else "—")
    lines = [
        f"Mã khiếu nại: {d.code} | trạng thái ticket: {d.status}",
        f"MSNV: {emp.employee_code} | Họ tên: {emp.full_name}",
        f"Kỳ lương: {period} | divisor: {pay.salary_divisor} | policy_version: {policy_ver}",
        f"Lý do CN: {reason}",
        f"Mô tả CN: {d.description.split(chr(10) + '---' + chr(10) + 'HR: ')[0]}",
        f"Trạng thái phiếu: {slip.status}",
        f"WD: {slip.wd_salary} | PC: {slip.allowance_total} | OT: {slip.ot_pay} | Gross: {slip.gross}",
        f"BHXH: {slip.bhxh} | BHYT: {slip.bhyt} | BHTN: {slip.bhtn} | CĐ: {slip.union_fee} | Net: {slip.net}",
    ]
    if ts:
        lines.append(
            f"Công: worked_days={ts.worked_days}, AL={ts.al_days}, REM={ts.rem_days}, "
            f"late={ts.late_count}, early={ts.early_count}, "
            f"OT_h weekday/weekend/holiday={ts.ot_hours_weekday}/{ts.ot_hours_weekend}/{ts.ot_hours_holiday}"
        )
    else:
        lines.append("Thiếu timesheet tháng — không có số công/OT để đối chiếu.")
    if d.ai_summary:
        lines.append(f"Tóm tắt AI trước: {d.ai_summary[:500]}")
    return d, "\n".join(lines)


def run_ai_query(db: Session, user: User, body: AiQueryRequest) -> AiQueryResponse:
    if not user.has_permission("ai_query"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Trợ Lý AI xin chào {user.full_name}, bạn không có quyền hỏi AI (`ai_query`). "
                "Liên hệ Admin."
            ),
        )

    cfg = ensure_settings(db)
    if not cfg.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: Admin đã tắt Gemini. Bật lại tại Cấu Hình → AI Gemini.",
        )

    used = _queries_today(db, user.id)
    if used >= cfg.max_queries_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Trợ Lý AI xin chào {user.full_name}, bạn đã dùng hết "
                f"{cfg.max_queries_per_day} câu hỏi AI hôm nay."
            ),
        )

    message = (body.message or "").strip()
    dispute: Dispute | None = None
    context_block = ""
    kind = "chat"
    if body.dispute_id is not None:
        dispute, context_block = _dispute_context(db, body.dispute_id)
        kind = "dispute_review"
        if not message:
            message = f"Rà soát khiếu nại {dispute.code}: phân tích lệch công/OT/phụ cấp và đề xuất bước tiếp theo cho HR."

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: vui lòng nhập câu hỏi hoặc chọn khiếu nại để rà soát.",
        )

    user_payload = (
        f"Người hỏi: {user.full_name} (username={user.username}).\n\n"
        + (f"### Ngữ cảnh khiếu nại\n{context_block}\n\n" if context_block else "")
        + f"### Câu hỏi\n{message}"
    )

    api_key = resolve_api_key(cfg.api_key_encrypted)
    try:
        result = generate_text(
            api_key=api_key,
            model_name=cfg.model_name,
            system=SYSTEM_PROMPT_BASE,
            user_message=user_payload,
            max_output_tokens=cfg.max_output_tokens,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Trợ Lý AI: không gọi được Gemini — {exc}",
        ) from exc

    job = AiJob(
        user_id=user.id,
        kind=kind,
        prompt=user_payload[:8000],
        response=result.text,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        dispute_id=dispute.id if dispute else None,
        model_name=result.model_name,
    )
    db.add(job)

    if dispute is not None:
        dispute.ai_summary = result.text[:4000]
        if dispute.status == "open":
            dispute.status = "ai_reviewed"

    db.commit()
    db.refresh(job)

    remaining = max(0, cfg.max_queries_per_day - used - 1)
    return AiQueryResponse(
        answer=result.text,
        kind=kind,
        job_id=job.id,
        dispute_id=dispute.id if dispute else None,
        dispute_code=dispute.code if dispute else None,
        model_name=result.model_name,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        stub=result.stub,
        remaining_today=remaining,
        message=(
            f"Trợ Lý AI xin chào {user.full_name}, đã trả lời "
            f"({'stub' if result.stub else 'Gemini'}). Còn {remaining} câu hôm nay."
        ),
    )
