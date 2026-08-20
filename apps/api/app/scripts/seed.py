"""Seed portal_tabs + Admin + HR demo. Chạy: python -m app.scripts.seed"""

from app.core.database import SessionLocal, engine
from app.core.database import Base
from app.modules.config import models as config_models  # noqa: F401
from app.modules.core import models as core_models  # noqa: F401
from app.modules.core.service import seed_admin_and_demo
from app.modules.policy import models as policy_models  # noqa: F401
from app.modules.policy.service import seed_default_package
from app.modules.calendar import models as calendar_models  # noqa: F401
from app.modules.calendar.service import seed_calendar
from app.modules.mdm import models as mdm_models  # noqa: F401
from app.modules.mdm.service import seed_mdm
from app.modules.attendance.seed_shifts import assign_default_shift_to_teams, seed_work_shifts
from app.modules.attendance.timesheet import seed_leave_types
from app.modules.worker.service import default_password_from_cccd, seed_worker_accounts
from app.modules.dispute import models as dispute_models  # noqa: F401
from app.modules.payroll import models as payroll_models  # noqa: F401
from app.modules.ai import models as ai_models  # noqa: F401

# Import đủ model để create_all tạo HẾT bảng (chấm công, tích hợp, bảo hiểm,
# nhật ký, export log…). Thiếu các model này → thiếu bảng attendance_punches…
# khiến Tính lương / Chấm công lỗi 500 UndefinedTable.
from app.modules.integration import models as integration_models  # noqa: F401
from app.modules.attendance import models as attendance_models  # noqa: F401
from app.modules.insurance import models as insurance_models  # noqa: F401
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.core import export_log as export_log_models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_admin_and_demo(db)
        pkg = seed_default_package(db)
        seed_calendar(db)
        mdm = seed_mdm(db)
        seed_leave_types(db)
        seed_work_shifts(db)
        assign_default_shift_to_teams(db)
        workers = seed_worker_accounts(db)
        print("Seed xong:", result, "policy=", pkg.name, "mdm=", mdm, "workers=", workers)
        print("Admin đăng nhập bằng ADMIN_USERNAME / ADMIN_PASSWORD trong .env")
        print("User demo: hr.demo / HrDemo@123456 (7 module, không Cấu Hình)")
        print(
            "Worker demo: MSNV 5290 / "
            f"{default_password_from_cccd(None, '5290')} (4 số cuối CCCD hoặc MSNV, cổng /worker)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
