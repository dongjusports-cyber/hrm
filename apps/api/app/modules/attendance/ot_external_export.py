"""Xuất bảng OT ngoài (ATM riêng) — delegate payroll (22§22.8)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.core.models import User
from app.modules.payroll.ot_external import export_ot_external as _export


def build_ot_external_export(db: Session, period: str, actor: User) -> tuple[bytes, str, str]:
    if len(period) != 7 or period[4] != "-":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: period phải dạng YYYY-MM.",
        )
    data, filename = _export(db, period, actor)
    media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return data, filename, media
