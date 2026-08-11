"""holidays + work_week_rules (schema 07§7.3)."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class Holiday(Base):
    __tablename__ = "holidays"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkWeekRule(Base):
    __tablename__ = "work_week_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # 1=Mon .. 7=Sun — JSON để chạy được cả Postgres và SQLite test
    work_weekdays: Mapped[list] = mapped_column(JSON, nullable=False)
    morning_start: Mapped[time] = mapped_column(Time, nullable=False)
    morning_end: Mapped[time] = mapped_column(Time, nullable=False)
    afternoon_start: Mapped[time] = mapped_column(Time, nullable=False)
    afternoon_end: Mapped[time] = mapped_column(Time, nullable=False)
    grace_late_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
