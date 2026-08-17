"""Portal tabs metadata (schema 07§7.3)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

PayloadType = JSON().with_variant(JSONB(), "postgresql")


class PortalTab(Base):
    __tablename__ = "portal_tabs"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MobilePunchSettings(Base):
    """Singleton id=1 — chấm công điện thoại (mặt). GET không tạo dòng."""

    __tablename__ = "mobile_punch_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # off | allowlist | all
    mode: Mapped[str] = mapped_column(String(20), default="allowlist", nullable=False)
    department_codes: Mapped[list] = mapped_column(PayloadType, default=list, nullable=False)
    extra_msnv: Mapped[list] = mapped_column(PayloadType, default=list, nullable=False)
    gps_lat: Mapped[float | None] = mapped_column(nullable=True)
    gps_lng: Mapped[float | None] = mapped_column(nullable=True)
    gps_radius_m: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    require_photo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
