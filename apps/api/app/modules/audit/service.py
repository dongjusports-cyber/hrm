"""Ghi / đọc hộp đen. Cấm log lương chi tiết, mật khẩu, API key (12§12.1)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import (
    AuditExportOut,
    AuditLogOut,
    AuditPolicyConfirmOut,
    BlackBoxOut,
)
from app.modules.core.export_log import ExportLog
from app.modules.core.models import User
from app.modules.policy.models import PolicyConfirmLog

FORBIDDEN_META_KEYS = {
    "password",
    "password_hash",
    "api_key",
    "token",
    "gemini",
    "net",
    "gross",
    "wd_salary",
    "bhxh",
    "payload",
    "before_payload",
    "after_payload",
}


def _sanitize_meta(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not meta:
        return None
    clean: dict[str, Any] = {}
    for k, v in meta.items():
        lk = str(k).lower()
        if any(bad in lk for bad in FORBIDDEN_META_KEYS):
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            clean[str(k)] = v
        elif isinstance(v, list) and all(isinstance(x, (str, int, float)) for x in v):
            clean[str(k)] = v[:50]
    return clean or None


def write_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str = "",
    entity_id: str | None = None,
    summary: str = "",
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
    commit: bool = True,
) -> AuditLog:
    row = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_username=actor.username if actor else None,
        action=action.strip()[:80],
        entity_type=(entity_type or "")[:80],
        entity_id=(str(entity_id)[:120] if entity_id is not None else None),
        summary=(summary or "")[:2000],
        meta_json=_sanitize_meta(meta),
        ip=(ip[:64] if ip else None),
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def list_audit_logs(db: Session, *, limit: int = 100) -> list[AuditLogOut]:
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [
        AuditLogOut(
            id=r.id,
            actor_user_id=r.actor_user_id,
            actor_username=r.actor_username,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            summary=r.summary,
            meta_json=r.meta_json,
            ip=r.ip,
            created_at=r.created_at,
        )
        for r in rows
    ]


def list_export_logs(db: Session, *, limit: int = 100) -> list[AuditExportOut]:
    rows = (
        db.query(ExportLog, User)
        .outerjoin(User, User.id == ExportLog.user_id)
        .order_by(ExportLog.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    out: list[AuditExportOut] = []
    for log, user in rows:
        out.append(
            AuditExportOut(
                id=log.id,
                user_id=log.user_id,
                username=user.username if user else None,
                full_name=user.full_name if user else None,
                kind=log.kind,
                period=log.period,
                row_count=log.row_count,
                filename=log.filename,
                created_at=log.created_at,
            )
        )
    return out


def list_policy_confirms(db: Session, *, limit: int = 50) -> list[AuditPolicyConfirmOut]:
    rows = (
        db.query(PolicyConfirmLog)
        .order_by(PolicyConfirmLog.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    # Không trả before/after payload (có thể chứa số tiền) — chỉ metadata
    result: list[AuditPolicyConfirmOut] = []
    for r in rows:
        actor = db.get(User, r.actor_user_id)
        result.append(
            AuditPolicyConfirmOut(
                id=r.id,
                package_id=r.package_id,
                actor_user_id=r.actor_user_id,
                actor_username=actor.username if actor else None,
                confirm_step=r.confirm_step,
                note=r.note,
                created_at=r.created_at,
            )
        )
    return result


def black_box(db: Session, *, limit: int = 80) -> BlackBoxOut:
    return BlackBoxOut(
        actions=list_audit_logs(db, limit=limit),
        exports=list_export_logs(db, limit=limit),
        policy_confirms=list_policy_confirms(db, limit=min(40, limit)),
        note=(
            "Hộp đen COSMOS: không lưu mật khẩu, API key, hay bảng lương chi tiết từng đồng. "
            "Chỉ hành động, xuất file, và xác nhận policy 3 bước."
        ),
    )
