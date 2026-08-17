"""Chấm công điện thoại — allowlist bộ phận + GPS + ảnh. GET không ghi DB."""

from __future__ import annotations

import base64
import binascii
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.modules.attendance.engine import VN_TZ
from app.modules.config.models import MobilePunchSettings
from app.modules.integration.models import AttendancePunch
from app.modules.mdm.models import Employee, Team

log = logging.getLogger("dj_hrm.mobile_punch")

DEFAULT_MODE = "allowlist"
DEFAULT_DEPT_CODES = ["03"]
DEFAULT_RADIUS_M = 200
COOLDOWN_SECONDS = 60
MAX_PHOTO_BYTES = 1_500_000
MODES = frozenset({"off", "allowlist", "all"})

MSG_OFF = "Chấm công điện thoại đang tắt. Vui lòng chấm bằng máy vân tay."
MSG_PILOT = "Đang thử nghiệm tại Main Office. Bộ phận khác vẫn chấm bằng máy vân tay."
MSG_NO_GPS = "Bật vị trí (GPS) để chấm công tại nhà máy."
MSG_OUTSIDE = "Bạn đang ngoài nhà máy. Chỉ chấm công khi có mặt tại xưởng."
MSG_NO_PHOTO = "Chụp mặt để chấm công."
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
    photo_base64: str | None = None
    device_id: str | None = Field(default=None, max_length=64)


class WorkerPunchOut(BaseModel):
    id: int
    punch_time: datetime
    source: str = "mobile"
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


def _decode_photo(raw: str) -> bytes:
    s = raw.strip()
    if not s:
        raise HTTPException(status_code=400, detail=MSG_NO_PHOTO)
    if s.lower().startswith("data:") and "," in s:
        s = s.split(",", 1)[1]
    s = re.sub(r"\s+", "", s)
    try:
        data = base64.b64decode(s, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Ảnh chấm công không đọc được.") from exc
    if len(data) < 24 or len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Ảnh chấm công quá nhỏ hoặc quá lớn.")
    jpeg = data[:3] == b"\xff\xd8\xff"
    png = data[:8] == b"\x89PNG\r\n\x1a\n"
    if not jpeg and not png:
        raise HTTPException(status_code=400, detail="Ảnh phải là JPEG hoặc PNG.")
    return data


def _save_photo(employee_code: str, data: bytes) -> str:
    ext = ".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg"
    root = Path(get_settings().upload_dir).expanduser().resolve() / "worker_punches" / employee_code
    root.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now(VN_TZ).strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}{ext}"
    path = root / name
    path.write_bytes(data)
    return str(path.relative_to(Path(get_settings().upload_dir).expanduser().resolve()))


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

    photo_rel: str | None = None
    if cfg.require_photo:
        if not body.photo_base64:
            raise HTTPException(status_code=400, detail=MSG_NO_PHOTO)
        photo_rel = _save_photo(employee_code, _decode_photo(body.photo_base64))
    elif body.photo_base64:
        photo_rel = _save_photo(employee_code, _decode_photo(body.photo_base64))

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

    raw: dict[str, Any] = {"channel": "worker_app"}
    if body.latitude is not None:
        raw["lat"] = body.latitude
        raw["lng"] = body.longitude
        if body.accuracy_m is not None:
            raw["accuracy_m"] = body.accuracy_m
        if cfg.gps_enforced:
            raw["distance_m"] = round(
                haversine_m(cfg.gps_lat or 0, cfg.gps_lng or 0, body.latitude, body.longitude), 1
            )
    if photo_rel:
        raw["photo"] = photo_rel

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
        detail="Đã ghi giờ chấm công điện thoại.",
    )
