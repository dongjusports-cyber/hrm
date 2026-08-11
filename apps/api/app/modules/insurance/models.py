"""insurance_declarations — báo tăng/giảm BHXH hàng tháng (21§21.3, hạng mục 5.5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InsuranceDeclaration(Base):
    __tablename__ = "insurance_declarations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    declaration_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # increase | decrease | salary_change
    effective_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    old_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    new_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    batch_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    # draft | exported | submitted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped["Employee"] = relationship()  # noqa: F821
