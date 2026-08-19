"""Hoàn thiện script nạp STK — không ghi VPS; chỉ logic dry-run / trường cấm."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.scripts.fill_bank_from_salary import (
    FORBIDDEN_FIELDS,
    FillStats,
    _dec,
    _load_snapshot_banks,
    apply_profile_to_employee,
    apply_snapshot_bank,
)


def _emp(**kwargs):
    base = dict(
        employee_code="5290",
        bank_account=None,
        phone=None,
        contract_salary=Decimal("0"),
        probation_salary=Decimal("0"),
        join_date=None,
        contract_signed_at=None,
        pay_channel="ATM",
        birth_date=date(1989, 6, 27),
        id_number="072189010137",
        permanent_address="ẤP 3",
        temporary_address="ẤP 3",
        full_name="TRƯƠNG THỊ NỊ",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_dec_skips_zero_and_junk():
    assert _dec(None) is None
    assert _dec("0") is None
    assert _dec("6075000") == Decimal("6075000")
    assert _dec("abc") is None


def test_load_snapshot_banks_reads_profile(tmp_path):
    emp_dir = tmp_path / "employees"
    emp_dir.mkdir()
    (emp_dir / "5290.json").write_text(
        '{"employee_code":"5290","profile":{"bank_account":"060226852411"}}',
        encoding="utf-8",
    )
    (emp_dir / "bad.json").write_text("{", encoding="utf-8")
    out = _load_snapshot_banks(str(tmp_path))
    assert out == {"5290": "060226852411"}


def test_apply_fills_empty_phone_join_signed():
    emp = _emp()
    stats = FillStats()
    apply_profile_to_employee(
        emp,
        {
            "phone": "0387199937",
            "join_date": date(2015, 3, 5),
            "contract_signed_at": date(2017, 4, 5),
            "bank_account": "060226852411",
            "contract_salary": Decimal("6075000"),
            "pay_channel": "ATM",
        },
        stats,
    )
    assert emp.phone == "0387199937"
    assert emp.join_date == date(2015, 3, 5)
    assert emp.contract_signed_at == date(2017, 4, 5)
    assert emp.bank_account == "060226852411"
    assert emp.contract_salary == Decimal("6075000")
    assert stats.phone == 1 and stats.join == 1 and stats.signed == 1
    assert stats.bank == 1 and stats.sal == 1


def test_apply_does_not_touch_birth_cccd_address_name():
    emp = _emp()
    birth = emp.birth_date
    idn = emp.id_number
    addr = emp.permanent_address
    name = emp.full_name
    stats = FillStats()
    apply_profile_to_employee(
        emp,
        {
            "birth_date": date(1999, 1, 1),
            "id_number": "999",
            "permanent_address": "KHÁC",
            "temporary_address": "KHÁC",
            "full_name": "TÊN SAI",
            "phone": "0900000000",
        },
        stats,
    )
    assert emp.birth_date == birth
    assert emp.id_number == idn
    assert emp.permanent_address == addr
    assert emp.full_name == name
    assert emp.phone == "0900000000"
    assert FORBIDDEN_FIELDS >= {
        "birth_date",
        "id_number",
        "permanent_address",
        "temporary_address",
    }


def test_apply_does_not_overwrite_existing_phone_or_join():
    emp = _emp(phone="0111", join_date=date(2010, 1, 1), contract_signed_at=date(2011, 1, 1))
    stats = FillStats()
    apply_profile_to_employee(
        emp,
        {"phone": "0387199937", "join_date": date(2015, 3, 5), "contract_signed_at": date(2017, 4, 5)},
        stats,
    )
    assert emp.phone == "0111"
    assert emp.join_date == date(2010, 1, 1)
    assert emp.contract_signed_at == date(2011, 1, 1)
    assert stats.phone == 0 and stats.join == 0 and stats.signed == 0


def test_snapshot_bank_only_if_empty():
    empty = _emp()
    filled = _emp(bank_account="111")
    stats = FillStats()
    apply_snapshot_bank(empty, "060226852411", stats)
    apply_snapshot_bank(filled, "060226852411", stats)
    assert empty.bank_account == "060226852411"
    assert filled.bank_account == "111"
    assert stats.bank == 1


def test_pay_channel_cash_when_no_bank():
    emp = _emp(pay_channel="ATM", bank_account=None)
    stats = FillStats()
    apply_profile_to_employee(emp, {"pay_channel": "CASH"}, stats)
    assert emp.pay_channel == "CASH"
    assert stats.pay == 1
