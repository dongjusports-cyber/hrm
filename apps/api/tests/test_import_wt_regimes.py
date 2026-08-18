"""Parse Excel chế độ thai sản / nuôi con nhỏ 18.08."""

from datetime import date

from app.scripts.import_wt_regimes import load_wt_regime_xlsx, parse_wt_regime_lines


def test_parse_child_and_pregnant_sections():
    rows = parse_wt_regime_lines(
        [
            "DANH SÁCH CHẾ ĐỘ",
            "Con nhỏ",
            "6472 - MAI THỊ THẢO - Production, Bond - Worker -> 01/06/2026 - 05/12/2026",
            "1648 - TƯỚNG LỆ KIỀU MI - HR & Admin - Supervisor -> 29/06/2026 - 02/02/2027",
            "Mang thai",
            "7113 - TRẦN LUYỆN NGHI THƯỜNG - Sewing - Worker -> 22/07/2026 - 15/12/2026",
            "8724 - TRẦN THỊ THU TRANG - Sewing - Worker -> 10/08/2026 - 21/01/2027",
        ]
    )
    assert len(rows) == 4
    child = {r.employee_code: r for r in rows if r.regime_type == "CHILD"}
    preg = {r.employee_code: r for r in rows if r.regime_type == "PREGNANT"}
    assert set(child) == {"6472", "1648"}
    assert set(preg) == {"7113", "8724"}
    assert child["6472"].hours_early == 2
    assert child["6472"].date_from == date(2026, 6, 1)
    assert child["6472"].date_to == date(2026, 12, 5)
    assert child["6472"].full_name == "MAI THỊ THẢO"
    assert preg["7113"].hours_early == 1
    assert preg["8724"].date_from == date(2026, 8, 10)
    assert preg["8724"].date_to == date(2027, 1, 21)


def test_parse_maternity_leave_section():
    rows = parse_wt_regime_lines(
        [
            "Đang nghỉ chế độ đặc biệt ( Nghỉ sau khi sanh em bé)",
            "8283 - LÊ THỊ KIM NGÂN - Sewing - Worker -> 15/04/2026 - 13/11/2026",
            "8256 - NGUYỄN THỊ DIỄM TRANG - Sewing - Worker -> 02/04/2026 - 01/10/2026",
        ]
    )
    assert {r.employee_code: r.regime_type for r in rows} == {
        "8283": "MATERNITY",
        "8256": "MATERNITY",
    }
    assert rows[0].hours_early == 0
    assert rows[0].date_from == date(2026, 4, 15)
    assert rows[0].date_to == date(2026, 11, 13)


def test_parse_real_xlsx_18_08():
    from app.scripts.import_wt_regimes import _default_xlsx

    xlsx = _default_xlsx()
    assert xlsx.is_file(), xlsx
    rows = load_wt_regime_xlsx(xlsx)
    by_type = {}
    for r in rows:
        by_type.setdefault(r.regime_type, []).append(r.employee_code)
    assert set(by_type["CHILD"]) == {"6472", "1648", "5916", "5191", "7522"}
    assert set(by_type["PREGNANT"]) == {"7113", "8724", "7774"}
    assert set(by_type["MATERNITY"]) == {"8283", "8256", "6880", "5456", "8290"}
    assert len(rows) == 13
    assert all(r.hours_early == 0 for r in rows if r.regime_type == "MATERNITY")
