"""Go-live 10.9 — import Excel phụ cấp (rộng / dài)."""

from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_list_allowance_types(client):
    res = client.get("/api/payroll/allowances/types", headers=_hr_headers(client))
    assert res.status_code == 200, res.text
    codes = {r["code"] for r in res.json()}
    assert {"ATTEND", "TRANSPORT", "TOXIC", "POSITION"} <= codes


def test_import_wide_and_list(client):
    headers = _hr_headers(client)
    content = _xlsx(
        [
            ["employee_code", "ATTEND", "TRANSPORT", "TOXIC"],
            ["5290", 230000, 760000, 100000],
            ["5321", 230000, "", 50000],
        ]
    )
    res = client.post(
        "/api/payroll/allowances/import",
        headers=headers,
        files={
            "file": (
                "pc.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created"] >= 4
    assert body["skipped_empty"] >= 1

    listed = client.get(
        "/api/payroll/allowances?employee_code=5290", headers=headers
    )
    assert listed.status_code == 200
    by = {a["allowance_code"]: Decimal(str(a["amount"])) for a in listed.json()}
    assert by["ATTEND"] == Decimal("230000")
    assert by["TRANSPORT"] == Decimal("760000")
    assert by["TOXIC"] == Decimal("100000")


def test_import_long_upsert(client):
    headers = _hr_headers(client)
    content = _xlsx(
        [
            ["employee_code", "allowance_code", "amount"],
            ["5290", "PCCC", "150000"],
            ["5290", "PCCC", "160000"],
        ]
    )
    res = client.post(
        "/api/payroll/allowances/import",
        headers=headers,
        files={
            "file": (
                "pc_long.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created"] + body["updated"] >= 2

    listed = client.get(
        "/api/payroll/allowances?employee_code=5290", headers=headers
    ).json()
    pccc = next(a for a in listed if a["allowance_code"] == "PCCC")
    assert Decimal(str(pccc["amount"])) == Decimal("160000")


def test_import_unknown_employee_reports_error(client):
    headers = _hr_headers(client)
    content = _xlsx(
        [
            ["employee_code", "ATTEND"],
            ["NOPE99", 100000],
        ]
    )
    res = client.post(
        "/api/payroll/allowances/import",
        headers=headers,
        files={
            "file": (
                "bad.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert res.status_code == 200
    assert any("NOPE99" in e for e in res.json()["errors"])
