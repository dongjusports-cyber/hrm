"""
Đọc punch Mitapro — query Hiến pháp 04§4.1b.
Máy nhà máy: xác nhận thêm cột vào/ra / số máy khi có SQLEXPRESS.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

VN_TZ = timezone(timedelta(hours=7))

# Query chuẩn (read-only)
PUNCH_SQL = """
SELECT
    nv.MaNhanVien AS employee_code,
    io.MaChamCong AS ma_cham_cong,
    io.GioCham AS punch_time
FROM CheckInOut io
INNER JOIN NHANVIEN nv ON nv.MaChamCong = io.MaChamCong
WHERE io.GioCham >= ? AND io.GioCham < ?
ORDER BY io.GioCham ASC
"""


@dataclass
class PunchRow:
    employee_code: str
    punch_time: datetime
    ma_cham_cong: str | None = None
    device_id: str | None = None
    raw: dict[str, Any] | None = None

    def to_api_dict(self) -> dict[str, Any]:
        pt = self.punch_time
        if pt.tzinfo is None:
            pt = pt.replace(tzinfo=VN_TZ)
        return {
            "employee_code": str(self.employee_code).strip(),
            "punch_time": pt.isoformat(),
            "ma_cham_cong": self.ma_cham_cong,
            "device_id": self.device_id,
            "raw": self.raw
            or {
                "MaNhanVien": str(self.employee_code).strip(),
                "MaChamCong": self.ma_cham_cong,
                "GioCham": pt.isoformat(),
            },
        }


class PunchSource(Protocol):
    def fetch_punches(self, dt_from: datetime, dt_to: datetime) -> list[PunchRow]: ...


def to_mitapro_naive(dt: datetime) -> datetime:
    """GioCham trên SQL Mitapro là giờ VN không TZ. Không được lột UTC thành naive."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(VN_TZ).replace(tzinfo=None)


class MockPunchSource:
    """Test / máy chưa có SQL Server."""

    def __init__(self, rows: list[PunchRow] | None = None) -> None:
        self._rows = rows or []

    def fetch_punches(self, dt_from: datetime, dt_to: datetime) -> list[PunchRow]:
        out: list[PunchRow] = []
        for r in self._rows:
            t = r.punch_time
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            f = dt_from if dt_from.tzinfo else dt_from.replace(tzinfo=timezone.utc)
            to = dt_to if dt_to.tzinfo else dt_to.replace(tzinfo=timezone.utc)
            if f <= t < to:
                out.append(r)
        return out


class MitaproSqlSource:
    """Đọc SQL Server qua pyodbc — chỉ SELECT."""

    def __init__(self, odbc_conn_str: str) -> None:
        self.odbc_conn_str = odbc_conn_str

    def fetch_punches(self, dt_from: datetime, dt_to: datetime) -> list[PunchRow]:
        try:
            import pyodbc  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Chưa cài pyodbc. Chạy: pip install -r requirements.txt "
                "và cài ODBC Driver 17/18 for SQL Server."
            ) from exc

        # SQL Server nhận datetime naive — phải là giờ VN, không phải UTC đã lột TZ.
        f = to_mitapro_naive(dt_from)
        t = to_mitapro_naive(dt_to)

        rows: list[PunchRow] = []
        try:
            conn = pyodbc.connect(self.odbc_conn_str, timeout=30)
        except pyodbc.Error as exc:
            err = str(exc)
            if "IM002" in err or "Data source name not found" in err:
                from dj_agent.odbc_util import odbc_setup_hint

                raise RuntimeError(
                    f"Không kết nối được SQL Mitapro — {odbc_setup_hint(self.odbc_conn_str)} "
                    "Chạy KIEM_TRA_ODBC.bat và sửa MITAPRO_ODBC trong .env."
                ) from exc
            raise RuntimeError(f"Không kết nối được SQL Mitapro: {exc}") from exc
        with conn:
            conn.timeout = 60
            cur = conn.cursor()
            cur.execute(PUNCH_SQL, f, t)
            for emp, ma, gio in cur.fetchall():
                if gio is None or emp is None:
                    continue
                if isinstance(gio, datetime):
                    punch_time = gio
                else:
                    punch_time = datetime.fromisoformat(str(gio))
                rows.append(
                    PunchRow(
                        employee_code=str(emp).strip(),
                        punch_time=punch_time,
                        ma_cham_cong=str(ma).strip() if ma is not None else None,
                        raw={
                            "MaNhanVien": str(emp).strip(),
                            "MaChamCong": str(ma).strip() if ma is not None else None,
                            "GioCham": str(gio),
                        },
                    )
                )
        return rows


def build_source(*, mock: bool, odbc: str, mock_rows: list[PunchRow] | None = None) -> PunchSource:
    if mock:
        return MockPunchSource(mock_rows)
    return MitaproSqlSource(odbc)
