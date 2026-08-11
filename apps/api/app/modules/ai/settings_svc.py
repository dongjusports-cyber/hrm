"""Cấu hình runtime Gemini — Admin (Cấu Hình → AI)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.ai.crypto_key import encrypt_secret
from app.modules.ai.models import AiRuntimeSettings
from app.modules.ai.provider import resolve_api_key
from app.modules.ai.schemas import AiSettingsOut, AiSettingsUpdate


def ensure_settings(db: Session) -> AiRuntimeSettings:
    row = db.get(AiRuntimeSettings, 1)
    if row is None:
        row = AiRuntimeSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_settings_out(db: Session) -> AiSettingsOut:
    row = ensure_settings(db)
    key = resolve_api_key(row.api_key_encrypted)
    masked = ""
    if key:
        masked = ("*" * max(0, len(key) - 4)) + key[-4:]
    return AiSettingsOut(
        enabled=row.enabled,
        model_name=row.model_name,
        max_queries_per_day=row.max_queries_per_day,
        max_output_tokens=row.max_output_tokens,
        has_api_key=bool(key),
        api_key_masked=masked or None,
        source="database" if row.api_key_encrypted else ("env" if key else "none"),
    )


def update_settings(db: Session, body: AiSettingsUpdate) -> AiSettingsOut:
    row = ensure_settings(db)
    if body.enabled is not None:
        row.enabled = body.enabled
    if body.model_name is not None:
        name = body.model_name.strip()
        if not name or len(name) > 80:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: tên model không hợp lệ.",
            )
        row.model_name = name
    if body.max_queries_per_day is not None:
        if not 1 <= body.max_queries_per_day <= 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: hạn mức câu/ngày phải từ 1 đến 200.",
            )
        row.max_queries_per_day = body.max_queries_per_day
    if body.max_output_tokens is not None:
        if not 128 <= body.max_output_tokens <= 8192:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: max_output_tokens phải từ 128 đến 8192.",
            )
        row.max_output_tokens = body.max_output_tokens
    if body.clear_api_key:
        row.api_key_encrypted = None
    elif body.api_key is not None:
        key = body.api_key.strip()
        if key:
            row.api_key_encrypted = encrypt_secret(key)
    db.commit()
    db.refresh(row)
    return get_settings_out(db)
