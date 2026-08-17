"""Chấm công điện thoại — allowlist + GPS + mã xác minh (không gửi ảnh). GET không ghi DB."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.attendance.engine import VN_TZ
from app.modules.config.models import MobilePunchSettings
from app.modules.integration.models import AttendancePunch
from app.modules.mdm.models import Employee, Team

log = logging.getLogger("dj_hrm.mobile_punch")

DEFAULT_MODE = "allowlist"
DEFAULT_DEPT_CODES = ["03"]
DEFAULT_RADIUS_M = 200
COOLDOWN_SECONDS = 60
MODES = frozenset({"off", "allowlist", "all"})
PHOTO_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")

MSG_OFF = "Chấm công điện thoại đang tắt. Vui lòng chấm bằng máy vân tay."
MSG_PILOT = "Đang thử nghiệm tại Main Office. Bộ phận khác vẫn chấm bằng máy vân tay."
MSG_NO_GPS = "Bật vị trí (GPS) để chấm công tại nhà máy."
MSG_OUTSIDE = "Bạn đang ngoài nhà máy. Chỉ chấm công khi có mặt tại xưởng."
MSG_NO_HASH = "Chụp mặt để lấy mã xác minh. Ảnh không gửi lên máy chủ."
MSG_COOLDOWN = "Vừa chấm xong. Đợi 1 phút rồi chấm lại."
MSG_DUP = "Giờ chấm này đã ghi. Đợi giây lát rồi thử lại."
MSG_NO_EMP = "Trợ Lý AI: không tìm thấy hồ sơ nhân viên."


class MobilePunchSettingsOut(BaseModel):
    mode: str
    department_codes: list[str]
    extra_msnv: list[str]
    gps_lat: float | None
    gps_lng: float | None
    gps_radius_m: int
    require_photo: bool
    gps_enforced: bool
    persisted: bool


class MobilePunchSettingsUpdate(BaseModel):
    mode: str | None = None
    department_codes: list[str] | None = None
    extra_msnv: list[str] | None = None
    gps_lat: float | None = None
    gps_lng: float | None = None
    gps_radius_m: int | None = Field(default=None, ge=20, le=5000)
    require_photo: bool | None = None
    clear_gps: bool = False


class WorkerPunchIn(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    accuracy_m: float | None = None
    photo_hash: str | None = Field(default=None, max_length=64)
    device_id: str | None = Field(default=None, max_length=64)


class WorkerPunchOut(BaseModel):
    id: int
    punch_time: datetime
    source: str = "mobile"
    verify_code: str
    detail: str


@dataclass(frozen=True)
class EffectiveSettings:
    mode: str
    department_codes: tuple[str, ...]
    extra_msnv: tuple[str, ...]
    gps_lat: float | None
    gps_lng: float | None
    gps_radius_m: int
    require_photo: bool
    persisted: bool

    @property
    def gps_enforced(self) -> bool:
        return self.gps_lat is not None and self.gps_lng is not None


def _norm_codes(values: list[Any] | None, *, fallback: list[str] | None = None) -> list[str]:
    if not values:
        return list(fallback or [])
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        code = str(raw or "").strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def _from_row(row: MobilePunchSettings | None) -> EffectiveSettings:
    if row is None:
        return EffectiveSettings(
            mode=DEFAULT_MODE,
            department_codes=tuple(DEFAULT_DEPT_CODES),
            extra_msnv=(),
            gps_lat=None,
            gps_lng=None,
            gps_radius_m=DEFAULT_RADIUS_M,
            require_photo=True,
            persisted=False,
        )
    codes = _norm_codes(row.department_codes, fallback=DEFAULT_DEPT_CODES)
    if not codes:
        codes = list(DEFAULT_DEPT_CODES)
    mode = (row.mode or DEFAULT_MODE).strip().lower()
    if mode not in MODES:
        mode = DEFAULT_MODE
    return EffectiveSettings(
        mode=mode,
        department_codes=tuple(codes),
        extra_msnv=tuple(_norm_codes(row.extra_msnv)),
        gps_lat=row.gps_lat,
        gps_lng=row.gps_lng,
        gps_radius_m=int(row.gps_radius_m or DEFAULT_RADIUS_M),
        require_photo=bool(row.require_photo),
        persisted=True,
    )


def get_effective_settings(db: Session) -> EffectiveSettings:
    """Chỉ SELECT — không INSERT (GET không ghi)."""
    return _from_row(db.get(MobilePunchSettings, 1))


def settings_out(db: Session) -> MobilePunchSettingsOut:
    s = get_effective_settings(db)
    return MobilePunchSettingsOut(
        mode=s.mode,
        department_codes=list(s.department_codes),
        extra_msnv=list(s.extra_msnv),
        gps_lat=s.gps_lat,
        gps_lng=s.gps_lng,
        gps_radius_m=s.gps_radius_m,
        require_photo=s.require_photo,
        gps_enforced=s.gps_enforced,
        persisted=s.persisted,
    )


def update_settings(db: Session, body: MobilePunchSettingsUpdate) -> MobilePunchSettingsOut:
    row = db.get(MobilePunchSettings, 1)
    if row is None:
        row = MobilePunchSettings(
            id=1,
            mode=DEFAULT_MODE,
            department_codes=list(DEFAULT_DEPT_CODES),
            extra_msnv=[],
            gps_radius_m=DEFAULT_RADIUS_M,
            require_photo=True,
        )
        db.add(row)
        db.flush()

    if body.mode is not None:
        mode = body.mode.strip().lower()
        if mode not in MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: mode phải là off, allowlist hoặc all.",
            )
        row.mode = mode
    if body.department_codes is not None:
        codes = _norm_codes(body.department_codes)
        row.department_codes = codes or list(DEFAULT_DEPT_CODES)
    if body.extra_msnv is not None:
        row.extra_msnv = _norm_codes(body.extra_msnv)
    if body.clear_gps:
        row.gps_lat = None
        row.gps_lng = None
    else:
        if body.gps_lat is not None:
            if not -90 <= body.gps_lat <= 90:
                raise HTTPException(status_code=400, detail="Trợ Lý AI: vĩ độ không hợp lệ.")
            row.gps_lat = body.gps_lat
        if body.gps_lng is not None:
            if not -180 <= body.gps_lng <= 180:
                raise HTTPException(status_code=400, detail="Trợ Lý AI: kinh độ không hợp lệ.")
            row.gps_lng = body.gps_lng
    if body.gps_radius_m is not None:
        row.gps_radius_m = body.gps_radius_m
    if body.require_photo is not None:
        row.require_photo = body.require_photo
    db.commit()
    db.refresh(row)
    return settings_out(db)


def employee_dept_code(emp: Employee | None) -> str | None:
    if emp is None or emp.team is None or emp.team.department is None:
        return None
    return (emp.team.department.code or "").strip().upper() or None


def punch_eligibility(
    db: Session, emp: Employee | None, employee_code: str
) -> tuple[bool, str | None]:
    s = get_effective_settings(db)
    if s.mode == "off":
        return False, MSG_OFF
    if s.mode == "all":
        return True, None
    code = (employee_code or "").strip().upper()
    if code and code in s.extra_msnv:
        return True, None
    dept = employee_dept_code(emp)
    if dept and dept in s.department_codes:
        return True, None
    return False, MSG_PILOT


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * asin(sqrt(min(1.0, a)))


def _norm_photo_hash(value: str | None) -> str:
    h = (value or "").strip().lower()
    if not PHOTO_HASH_RE.fullmatch(h):
        raise HTTPException(status_code=400, detail=MSG_NO_HASH)
    return h


def make_verify_code(employee_code: str, punch_time: datetime, photo_hash: str) -> str:
    raw = f"{employee_code}|{punch_time.isoformat()}|{photo_hash}".encode()
    return "DJ-" + hashlib.sha256(raw).hexdigest()[:6].upper()


def load_employee(db: Session, user_emp: Employee | None) -> Employee | None:
    if user_emp is None:
        return None
    return (
        db.query(Employee)
        .options(joinedload(Employee.team).joinedload(Team.department))
        .filter(Employee.id == user_emp.id)
        .first()
    )


def create_worker_punch(
    db: Session,
    *,
    emp: Employee,
    employee_code: str,
    body: WorkerPunchIn,
) -> WorkerPunchOut:
    emp = load_employee(db, emp) or emp
    allowed, reason = punch_eligibility(db, emp, employee_code)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason or MSG_PILOT)

    cfg = get_effective_settings(db)
    if cfg.gps_enforced:
        if body.latitude is None or body.longitude is None:
            raise HTTPException(status_code=400, detail=MSG_NO_GPS)
        dist = haversine_m(cfg.gps_lat or 0, cfg.gps_lng or 0, body.latitude, body.longitude)
        if dist > cfg.gps_radius_m:
            raise HTTPException(status_code=403, detail=MSG_OUTSIDE)

    photo_hash: str | None = None
    if cfg.require_photo or body.photo_hash:
        photo_hash = _norm_photo_hash(body.photo_hash)

    now = datetime.now(VN_TZ)
    cutoff = now - timedelta(seconds=COOLDOWN_SECONDS)
    recent = (
        db.query(AttendancePunch.id)
        .filter(
            AttendancePunch.employee_code == employee_code,
            AttendancePunch.source == "mobile",
            AttendancePunch.punch_time >= cutoff,
        )
        .first()
    )
    if recent:
        raise HTTPException(status_code=429, detail=MSG_COOLDOWN)

    verify_code = make_verify_code(employee_code, now, photo_hash or "none")
    raw: dict[str, Any] = {"channel": "worker_app", "verify_code": verify_code}
    if photo_hash:
        raw["photo_hash"] = photo_hash
    if body.latitude is not None:
        raw["lat"] = body.latitude
        raw["lng"] = body.longitude
        if body.accuracy_m is not None:
            raw["accuracy_m"] = body.accuracy_m
        if cfg.gps_enforced:
            raw["distance_m"] = round(
                haversine_m(cfg.gps_lat or 0, cfg.gps_lng or 0, body.latitude, body.longitude), 1
            )

    punch = AttendancePunch(
        employee_code=employee_code,
        employee_id=emp.id,
        punch_time=now,
        direction=None,
        source="mobile",
        device_id=(body.device_id or "")[:64] or None,
        raw=raw,
    )
    db.add(punch)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=MSG_DUP) from exc

    try:
        from app.modules.attendance.service import recalculate_days

        day = now.date()
        recalculate_days(db, day, day, employee_code)
    except Exception:
        log.exception("mobile punch recalc failed code=%s", employee_code)

    db.commit()
    db.refresh(punch)
    return WorkerPunchOut(
        id=punch.id,
        punch_time=punch.punch_time,
        verify_code=verify_code,
        detail=f"Đã ghi giờ chấm công. Mã xác minh {verify_code}.",
    )
