"""
DJ HRM — FastAPI entrypoint
Portal 8 ô · Policy metadata-driven · Không Audit Mode · Không AI trên Worker
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.database import check_db
from app.core.logging_setup import setup_logging
from app.core.redis_client import check_redis
from app.core.security_middleware import SecurityHeadersMiddleware
from app.modules.config.catalog_router import router as catalog_router
from app.modules.config.org_router import router as org_router
from app.modules.config.roles_router import router as roles_router
from app.modules.config.router import router as config_router
from app.modules.config.users_router import router as users_router
from app.modules.core.router import router as core_router
from app.modules.policy.router import router as policy_router
from app.modules.policy.router import rates_router as policy_rates_router
from app.modules.calendar.router import router as calendar_router
from app.modules.mdm.router import router as mdm_router
from app.modules.worker.router import router as worker_router
from app.modules.integration.router import router as integration_router
from app.modules.attendance.router import router as attendance_router
from app.modules.ai.router import router as ai_router
from app.modules.payroll.router import router as payroll_router
from app.modules.dispute.router import router as dispute_router
from app.modules.report.router import router as report_router
from app.modules.audit.router import router as audit_router
from app.modules.insurance.router import router as insurance_router
from app.modules.print.router import router as print_router

APP_VERSION = "0.6.8-kpi"
settings = get_settings()
logger = logging.getLogger("djhrm")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging(settings)
    errors, warnings = settings.validate_for_boot()
    for w in warnings:
        logger.warning("Trợ Lý AI: %s", w)
    if errors:
        for e in errors:
            logger.error("Trợ Lý AI: %s", e)
        raise RuntimeError(
            "Trợ Lý AI: cấu hình production chưa an toàn — "
            + "; ".join(errors)
        )
    logger.info(
        "DJ HRM API khởi động (env=%s, docs=%s)",
        settings.app_env,
        settings.openapi_enabled,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    description="Hệ thống quản trị nhân sự DONGJU — DJ HRM",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.openapi_enabled else None,
    redoc_url="/redoc" if settings.openapi_enabled else None,
    openapi_url="/openapi.json" if settings.openapi_enabled else None,
)

app.add_middleware(SecurityHeadersMiddleware, settings=settings)
_cors_kw: dict = {
    "allow_origins": settings.cors_origin_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "expose_headers": ["Content-Disposition"],
}
# Local/LAN: ĐT mở http://192.168.x.x:5173 — cho phép origin nội bộ (không dùng khi production)
if not settings.is_production:
    _cors_kw["allow_origin_regex"] = (
        r"https?://("
        r"localhost|127\.0\.0\.1|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?"
    )
app.add_middleware(CORSMiddleware, **_cors_kw)
if settings.is_production and settings.trusted_hosts_list != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)

app.include_router(core_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(catalog_router, prefix="/api")
app.include_router(org_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(policy_router, prefix="/api")
app.include_router(policy_rates_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")
app.include_router(mdm_router, prefix="/api")
app.include_router(worker_router, prefix="/api")
app.include_router(integration_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(payroll_router, prefix="/api")
app.include_router(dispute_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(insurance_router, prefix="/api")
app.include_router(print_router, prefix="/api")


@app.get("/health")
def health() -> JSONResponse:
    """Health check: api + db + redis (file 12§12.8)."""
    db_ok = check_db()
    redis_ok = check_redis()
    status = "ok" if db_ok and redis_ok else "degraded"
    code = 200 if status == "ok" else 503
    return JSONResponse(
        status_code=code,
        content={
            "status": status,
            "app": settings.app_name,
            "version": APP_VERSION,
            "env": settings.app_env,
            "checks": {
                "api": True,
                "database": db_ok,
                "redis": redis_ok,
            },
            "message": (
                "Hệ thống sẵn sàng."
                if status == "ok"
                else "Trợ Lý AI: một số dịch vụ chưa sẵn sàng. Kiểm tra PostgreSQL/Redis."
            ),
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    out = {
        "app": settings.app_name,
        "health": "/health",
        "message": "Xin chào, đây là API DJ HRM.",
        "version": APP_VERSION,
    }
    if settings.openapi_enabled:
        out["docs"] = "/docs"
    return out
