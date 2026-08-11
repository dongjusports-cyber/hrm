"""sync_jobs + attendance_punches (schema 07§7.4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

PayloadType = JSON().with_variant(JSONB(), "postgresql")


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    # requested | running | success | partial | error
    records_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="mitapro", nullable=False)
    trigger: Mapped[str] = mapped_column(String(40), default="agent", nullable=False)
    # agent | manual | schedule
    sync_date_from: Mapped[date | None] = mapped_column(Date(), nullable=True)
    sync_date_to: Mapped[date | None] = mapped_column(Date(), nullable=True)

    punches: Mapped[list["AttendancePunch"]] = relationship(back_populates="sync_job")


class AttendancePunch(Base):
    __tablename__ = "attendance_punches"
    __table_args__ = (
        UniqueConstraint("employee_code", "punch_time", name="uq_punch_employee_time"),
    )

    # Integer IDENTITY — tương đương BIGSERIAL quy mô 500 NV; tương thích SQLite test
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    punch_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    direction: Mapped[str | None] = mapped_column(String(3), nullable=True)  # IN | OUT
    sync_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sync_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(40), default="mitapro", nullable=False)
    ma_cham_cong: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw: Mapped[dict | None] = mapped_column(PayloadType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sync_job: Mapped[SyncJob | None] = relationship(back_populates="punches")
