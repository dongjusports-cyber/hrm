"""Seed catalog khoản lương (`pay_components`, đổi tên từ allowance_types — 2.3) + gán
mẫu cho fixture Oct/2025."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.mdm.models import Department, Employee
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent

SENIORITY_RULES = {
    "tiers": [
        {"min_months": 6, "max_months": 120, "base": 25000, "per_6_months": 25000},
        {"min_months": 120, "max_months": 180, "fixed": 550000},
        {"min_months": 180, "max_months": 240, "fixed": 600000},
        {"min_months": 240, "max_months": 360, "fixed": 650000},
        {"min_months": 360, "max_months": 10000, "fixed": 700000},
    ]
}

# 9 mã cũ + "ADJUST" (nêu tên trong 21§21.2) + 10 mã mới suy ra trực tiếp từ 148 cột bảng
# THR_SALARY_EMP / THR_ABEMPMAS (GenuiSuite_Code.sql — "Employee Work day Report" /
# "Employee Master") — mỗi mã có comment tiếng Việt gốc làm chứng, KHÔNG suy đoán:
#   RESPONSIBILITY <- ALLOW_AMT   "tro cap trach nhiem"
#   BONUS          <- INC_AMT     "TIEN THUONG"
#   TRAINING       <- TRAIN_ALLOW "Phu cap dao tao"
#   HOUSING        <- HOUSE_AMT   "House allowance"
#   ADVANCE        <- ADV_AMT     "Advance Amount"
#   SEVERANCE      <- SEVERANCE_AMT/SEVERANCE_YEAR (rõ nghĩa từ tên cột)
#   HARD           <- HARD_WORK_AMT/HARD_AMT (phân biệt TREAT_ALLOW="TRO CAP DOC HAI" — trùng
#                     TOXIC nên KHÔNG thêm mã riêng cho TREAT_ALLOW, tránh trùng lặp)
#   INCENTIVE      <- INCENTIVE_PROD, HEALTHCARD <- HEALTH_CARD, EQUIPMENT <- EQUIPMENT
#                     (tên cột tự rõ nghĩa, không có comment riêng)
# Vẫn còn thiếu để đủ ~30 mã (21§21.4) — cột còn lại trong 148 cột là ngày công/OT/nghỉ
# (đã có ở attendance_days, leave_types, engine OT riêng) hoặc cột kỹ thuật (PK, CRT_DT…),
# không phải "khoản lương" riêng. HR bổ sung tiếp qua Admin (2.8) nếu phát sinh khoản thật
# chưa có ở đây — không bịa thêm khi chưa có nguồn (N2).
CATALOG: list[dict] = [
    {
        "code": "ATTEND",
        "name": "Chuyên cần",
        "proration": "attend_penalty",
        "include_in_si_base": False,
        "include_in_ot_base": True,
        "default_amount": Decimal("230000"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "TRANSPORT",
        "name": "Đi lại",
        "proration": "by_worked_days",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("760000"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "by_worked_days",
    },
    {
        "code": "TOXIC",
        "name": "Độc hại",
        "proration": "by_worked_days",
        "include_in_si_base": True,
        "include_in_ot_base": True,
        "default_amount": Decimal("100000"),
        "kind": "earning",
        "affects_si_base": True,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "by_worked_days",
    },
    {
        "code": "POSITION",
        "name": "Chức vụ",
        "proration": "by_worked_days",
        "include_in_si_base": True,
        "include_in_ot_base": True,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": True,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "by_worked_days",
    },
    {
        "code": "PCCC",
        "name": "PCCC+HSE",
        "proration": "by_worked_days",
        "include_in_si_base": True,
        "include_in_ot_base": True,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": True,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "by_worked_days",
    },
    {
        "code": "TECH",
        "name": "Tay nghề may",
        "proration": "by_worked_days",
        "include_in_si_base": True,
        "include_in_ot_base": True,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": True,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "by_worked_days",
    },
    {
        "code": "SENIORITY",
        "name": "Thâm niên",
        "proration": "seniority_tiers",
        "include_in_si_base": True,
        "include_in_ot_base": True,
        "default_amount": Decimal("0"),
        "rules": SENIORITY_RULES,
        "kind": "earning",
        "affects_si_base": True,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "OTHER",
        "name": "Khác",
        "proration": "by_worked_days",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "by_worked_days",
    },
    {
        "code": "CHILD",
        "name": "Con nhỏ",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("100000"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "ADJUST",
        "name": "Điều chỉnh (truy lĩnh / trừ khác)",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "info",  # dấu +/- do payslip_components.amount quyết định, không cố định earning/deduction
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,
        "proration_rule": "none",
    },
    {
        "code": "RESPONSIBILITY",
        "name": "Trách nhiệm",
        "proration": "fixed",
        "include_in_si_base": True,
        "include_in_ot_base": True,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": True,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "BONUS",
        "name": "Tiền thưởng",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "TRAINING",
        "name": "Đào tạo",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "HOUSING",
        "name": "Nhà ở",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "ADVANCE",
        "name": "Tạm ứng",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "info",  # tạm ứng rồi trừ lại kỳ sau — dấu +/- theo payslip_components.amount
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,
        "proration_rule": "none",
    },
    {
        "code": "SEVERANCE",
        "name": "Trợ cấp thôi việc",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,  # trợ cấp thôi việc theo luật thường miễn thuế trong hạn mức
        "proration_rule": "none",
    },
    {
        "code": "HARD",
        "name": "Nặng nhọc",
        "proration": "fixed",
        "include_in_si_base": True,
        "include_in_ot_base": True,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": True,
        "affects_ot_base": True,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "INCENTIVE",
        "name": "Năng suất / sản lượng",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "HEALTHCARD",
        "name": "Thẻ khám sức khỏe",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "EQUIPMENT",
        "name": "Dụng cụ / trang bị",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    # Mã hệ thống — phiếu lương chi tiết (4.1)
    {
        "code": "WD",
        "name": "Lương ngày công",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "OT",
        "name": "Tăng ca",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "earning",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": True,
        "proration_rule": "none",
    },
    {
        "code": "BHXH",
        "name": "BHXH (NLĐ)",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "deduction",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,
        "proration_rule": "none",
    },
    {
        "code": "BHYT",
        "name": "BHYT (NLĐ)",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "deduction",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,
        "proration_rule": "none",
    },
    {
        "code": "BHTN",
        "name": "BHTN (NLĐ)",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "deduction",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,
        "proration_rule": "none",
    },
    {
        "code": "UNION",
        "name": "Công đoàn",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "deduction",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,
        "proration_rule": "none",
    },
    {
        "code": "PIT",
        "name": "Thuế TNCN",
        "proration": "fixed",
        "include_in_si_base": False,
        "include_in_ot_base": False,
        "default_amount": Decimal("0"),
        "kind": "deduction",
        "affects_si_base": False,
        "affects_ot_base": False,
        "affects_pit": False,
        "proration_rule": "none",
    },
]

# 4.2 — mã nghỉ có lương ngày nghỉ (component_code = mã nghỉ, 22§22.6)
LEAVE_PAY_COMPONENTS: list[dict] = [
    {"code": "ALE", "name": "Lương nghỉ phép năm", "kind": "earning"},
    {"code": "FLE", "name": "Lương nghỉ tang chế", "kind": "earning"},
    {"code": "WED", "name": "Lương nghỉ cưới", "kind": "earning"},
    {"code": "LA", "name": "Lương nghỉ tai nạn LĐ", "kind": "earning"},
    {"code": "OFF", "name": "Lương nghỉ bù", "kind": "earning"},
    {"code": "TMP", "name": "Lương nghỉ hết hàng", "kind": "earning"},
    {"code": "PER", "name": "Lương nghỉ có phép (PER)", "kind": "earning"},
]


def seed_allowance_types(db: Session) -> None:
    for row in CATALOG:
        existing = db.query(PayComponent).filter(PayComponent.code == row["code"]).one_or_none()
        if existing:
            continue
        db.add(
            PayComponent(
                code=row["code"],
                name=row["name"],
                proration=row["proration"],
                include_in_si_base=row["include_in_si_base"],
                include_in_ot_base=row["include_in_ot_base"],
                default_amount=row["default_amount"],
                rules=row.get("rules"),
                kind=row["kind"],
                affects_si_base=row["affects_si_base"],
                affects_ot_base=row["affects_ot_base"],
                affects_pit=row["affects_pit"],
                proration_rule=row["proration_rule"],
            )
        )
    for row in LEAVE_PAY_COMPONENTS:
        existing = db.query(PayComponent).filter(PayComponent.code == row["code"]).one_or_none()
        if existing:
            continue
        db.add(
            PayComponent(
                code=row["code"],
                name=row["name"],
                proration="fixed",
                include_in_si_base=False,
                include_in_ot_base=False,
                default_amount=Decimal("0"),
                kind=row["kind"],
                affects_si_base=False,
                affects_ot_base=False,
                affects_pit=True,
                proration_rule="none",
            )
        )
    db.commit()


def _assign(db: Session, emp: Employee, code: str, amount: Decimal | None) -> None:
    at = db.query(PayComponent).filter(PayComponent.code == code).one()
    exists = (
        db.query(EmployeeAllowanceAssignment)
        .filter(
            EmployeeAllowanceAssignment.employee_id == emp.id,
            EmployeeAllowanceAssignment.allowance_type_id == at.id,
        )
        .one_or_none()
    )
    if exists:
        return
    db.add(
        EmployeeAllowanceAssignment(
            employee_id=emp.id,
            allowance_type_id=at.id,
            amount=amount,
        )
    )


def seed_fixture_allowance_assignments(db: Session) -> None:
    """Gán TOXIC cho công nhân xưởng (direct) — **chỉ** fixture test (conftest), không gọi khi tính lương."""
    seed_allowance_types(db)
    toxic = db.query(PayComponent).filter(PayComponent.code == "TOXIC").one()
    emps = db.query(Employee).filter(Employee.deleted_at.is_(None)).all()
    for emp in emps:
        dept = db.get(Department, emp.department_id) if emp.department_id else None
        if dept and dept.category == "direct":
            _assign(db, emp, "TOXIC", toxic.default_amount)
    db.commit()
