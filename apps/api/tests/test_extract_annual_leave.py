"""Parse Excel phép năm GenuSuite."""

from decimal import Decimal
from pathlib import Path

import pytest

from app.scripts.extract_annual_leave import parse_workbook

XLS = (
    Path(__file__).resolve().parents[3]
    / "HIEN_PHAP"
    / "Phép năm GenuSuite"
    / "phép năm 17.08.26.xls"
)


def test_parse_5118_matches_genus_ui():
    if not XLS.is_file():
        pytest.skip("Chưa có file phép năm GenuSuite")
    year, report_date, rows = parse_workbook(XLS)
    assert year == 2026
    assert report_date is not None
    by = {r["employee_code"]: r for r in rows}
    rec = by["5118"]
    assert rec["full_name"] == "CAO THỊ NGỌC DUNG"
    assert rec["al_days"] == Decimal("16")
    assert rec["used"] == Decimal("5")
    assert rec["unused"] == Decimal("11")
    assert rec["used_by_month"]["feb"] == Decimal("1")
    assert rec["used_by_month"]["mar"] == Decimal("1")
    assert rec["used_by_month"]["jun"] == Decimal("2")
    assert rec["used_by_month"]["jul"] == Decimal("1")
    assert rec["used_from_months"] == Decimal("5")
    assert len(rows) == 353
