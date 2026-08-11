"""Tests ánh xạ Excel → lookup code (nơi sinh, học vấn, HĐ)."""

from app.scripts.empinfo_lookup_map import (
    infer_contract_type,
    resolve_education_code,
    resolve_nationality_code,
    resolve_place_code,
)


def test_birth_place_tay_ninh():
    assert resolve_place_code("birth_place", "Tây Ninh") == "BIRTH_PLACE030"
    assert resolve_place_code("birth_place", "tay ninh") == "BIRTH_PLACE030"


def test_id_issue_place_and_hcm():
    assert resolve_place_code("id_issue_place", "Tây Ninh") == "ID_ISSUE_PLACE030"
    assert resolve_place_code("id_issue_place", "TP.HCM") == "ID_ISSUE_PLACE006"
    assert resolve_place_code("id_issue_place", "Ho Chi Minh") == "ID_ISSUE_PLACE006"


def test_education_from_excel_english():
    assert resolve_education_code("Intermediate (2 years)") == "EDUCATION_LEVEL006"
    assert resolve_education_code("University") == "EDUCATION_LEVEL008"
    assert resolve_education_code("12/12") == "EDUCATION_LEVEL004"
    assert resolve_education_code("TC2") == "EDUCATION_LEVEL006"


def test_nationality_default_vn():
    assert resolve_nationality_code(None) == "NATIONALITY001"
    assert resolve_nationality_code("Việt Nam") == "NATIONALITY001"


def test_contract_type_from_no():
    assert infer_contract_type("1514/VTH") == "VTH"
    assert infer_contract_type("2001/HD1") == "HD1"
    assert infer_contract_type("") is None
