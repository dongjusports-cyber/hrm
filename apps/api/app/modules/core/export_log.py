"""Ghi audit khi xuất dữ liệu (HIEN_PHAP 12§12.3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base


class ExportLog(Base):
    __tablename__ = "export_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filename: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


def log_export(
    db: Session,
    *,
    user_id: uuid.UUID,
    kind: str,
    period: str | None,
    row_count: int,
    filename: str,
) -> ExportLog:
    row = ExportLog(
        user_id=user_id,
        kind=kind,
        period=period,
        row_count=row_count,
        filename=filename,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
