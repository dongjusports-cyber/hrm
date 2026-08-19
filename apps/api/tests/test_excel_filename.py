from app.modules.core.excel_filename import (
    ascii_filename_fallback,
    attachment_content_disposition,
    company_excel_filename,
    month_year_tag,
)


def test_month_year_tag_from_period():
    assert month_year_tag("2026-08") == "08.2026"
    assert month_year_tag("2026-09") == "09.2026"
    assert month_year_tag("2026-10") == "10.2026"


def test_salary_and_ot_names_follow_period_month():
    assert company_excel_filename("Lương", period="2026-08") == (
        "Lương 08.2026 công ty Dongju Sports VN.xlsx"
    )
    assert company_excel_filename("Lương", period="2026-09") == (
        "Lương 09.2026 công ty Dongju Sports VN.xlsx"
    )
    assert company_excel_filename("Lương", period="2026-10") == (
        "Lương 10.2026 công ty Dongju Sports VN.xlsx"
    )
    assert company_excel_filename("OT", period="2026-08") == (
        "OT 08.2026 công ty Dongju Sports VN.xlsx"
    )


def test_other_exports_keep_company_suffix():
    assert company_excel_filename("KPI", period="2026-08") == (
        "KPI 08.2026 công ty Dongju Sports VN.xlsx"
    )
    assert company_excel_filename("Chu kỳ", period="2026-08") == (
        "Chu kỳ 08.2026 công ty Dongju Sports VN.xlsx"
    )
    assert company_excel_filename("Chu kỳ", period="2026-09") == (
        "Chu kỳ 09.2026 công ty Dongju Sports VN.xlsx"
    )
    from datetime import date

    assert company_excel_filename(
        "Danh sách nhân viên", as_of=date(2026, 8, 20)
    ) == "Danh sách nhân viên 20.08.2026 công ty Dongju Sports VN.xlsx"
    assert company_excel_filename(
        "Danh sách nhân viên", as_of=date(2026, 8, 22)
    ) == "Danh sách nhân viên 22.08.2026 công ty Dongju Sports VN.xlsx"


def test_content_disposition_has_utf8_star():
    name = company_excel_filename("Lương", period="2026-08", extra="5290")
    header = attachment_content_disposition(name)
    assert "5290" in header
    assert "08.2026" in header
    assert "filename*=UTF-8''" in header
    assert "Luong" in ascii_filename_fallback(name)
