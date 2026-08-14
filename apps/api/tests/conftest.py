"""Fixture test — SQLite memory, không đụng Postgres production."""

import os

# Phải set trước khi import app.core.database
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-dj-hrm-local-32chars!!"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "Admin@DongJu2026"
os.environ["ADMIN_FULL_NAME"] = "Nguyễn Thanh Thiện"
os.environ["DJHRM_AI_STUB"] = "1"
os.environ["GEMINI_API_KEY"] = ""
os.environ["APP_ENV"] = "local"
os.environ["AGENT_TOKEN"] = "test-agent-token-local"
os.environ["SYNC_RECALC_INLINE"] = "1"

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.config import models as config_models  # noqa: F401, E402
from app.modules.core import models as core_models  # noqa: F401, E402
from app.modules.core.service import seed_admin_and_demo  # noqa: E402
from app.modules.policy import models as policy_models  # noqa: F401, E402
from app.modules.policy.service import seed_default_package  # noqa: E402
from app.modules.calendar import models as calendar_models  # noqa: F401, E402
from app.modules.calendar.service import seed_calendar  # noqa: E402
from app.modules.mdm import models as mdm_models  # noqa: F401, E402
from app.modules.mdm.service import seed_mdm  # noqa: E402
from app.modules.worker.service import seed_worker_accounts  # noqa: E402
from app.modules.integration import models as integration_models  # noqa: F401, E402
from app.modules.attendance import models as attendance_models  # noqa: F401, E402
from app.modules.attendance.timesheet import seed_leave_types  # noqa: E402
from app.modules.ai import models as ai_models  # noqa: F401, E402
from app.modules.payroll import models as payroll_models  # noqa: F401, E402
from app.modules.payroll.seed_allowances import seed_fixture_allowance_assignments  # noqa: E402
from app.modules.dispute import models as dispute_models  # noqa: F401, E402
from app.modules.core import export_log as export_log_models  # noqa: F401, E402
from app.modules.audit import models as audit_models  # noqa: F401, E402
from app.modules.insurance import models as insurance_models  # noqa: F401, E402

get_settings.cache_clear()

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        seed_admin_and_demo(session)
        seed_default_package(session)
        seed_calendar(session)
        seed_mdm(session)
        seed_worker_accounts(session)
        seed_leave_types(session)
        seed_fixture_allowance_assignments(session)
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def _override() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
