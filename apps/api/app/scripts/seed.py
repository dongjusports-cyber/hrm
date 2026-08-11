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
from app.modules.worker.service import DEFAULT_WORKER_PASSWORD, seed_worker_accounts
from app.modules.dispute import models as dispute_models  # noqa: F401
from app.modules.payroll import models as payroll_models  # noqa: F401
from app.modules.ai import models as ai_models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_admin_and_demo(db)
        pkg = seed_default_package(db)
        seed_calendar(db)
        mdm = seed_mdm(db)
        workers = seed_worker_accounts(db)
        print("Seed xong:", result, "policy=", pkg.name, "mdm=", mdm, "workers=", workers)
        print("Admin đăng nhập bằng ADMIN_USERNAME / ADMIN_PASSWORD trong .env")
        print("User demo: hr.demo / HrDemo@123456 (7 module, không Cấu Hình)")
        print(f"Worker demo: MSNV 5290 / {DEFAULT_WORKER_PASSWORD} (cổng /worker)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
