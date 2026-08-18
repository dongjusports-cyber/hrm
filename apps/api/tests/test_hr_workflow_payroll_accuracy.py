"""Quy trình HR kín — hiển thị + công thức lương + phiếu.

Tạo/xoá NV, thôi việc–tái tuyển, gán/sửa phép, thai sản/nuôi con,
chấm/sửa công, tính lương thấy đổi số, phát hành phiếu.
"""

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.modules.payroll.money import money_vnd

VN = timezone(timedelta(hours=7))
SALARY = Decimal("5200000")  # / 26 = 200_000 đúng đồng


def _hr(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _iso(d: date, hh: int, mm: int) -> str:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=VN).isoformat()


def _weekdays(year: int, month: int, *, exclude: set[date], n: int) -> list[date]:
    last = monthrange(year, month)[1]
    out: list[date] = []
    for day in range(1, last + 1):
        d = date(year, month, day)
        if d.isoweekday() == 7 or d in exclude:
            continue
        out.append(d)
        if len(out) >= n:
            break
    return out


def _create(client, headers, code: str, *, join: date) -> dict:
    res = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": f"QA Quy trình {code}",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": str(SALARY),
            "probation_salary": "0",
            "pay_channel": "CASH",
            "join_date": join.isoformat(),
            "contract_signed_at": join.isoformat(),
            "status": "active",
            "si_enrolled": True,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def _patch_times(client, headers, code: str, d: date, hout: int, mout: int = 0):
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": code,
            "work_date": d.isoformat(),
            "first_in": _iso(d, 8, 0),
            "last_out": _iso(d, hout, mout),
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def _patch_leave(client, headers, code: str, d: date, leave_code: str):
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={"employee_code": code, "work_date": d.isoformat(), "leave_code": leave_code},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _slip(body: dict, code: str) -> dict:
    return next(p for p in body["payslips"] if p["employee_code"] == code)


def _expected_net(*, wd_days: Decimal, leave_days: Decimal, divisor: Decimal) -> dict[str, Decimal]:
    """WD + nghỉ 100% + chuyên cần/đi lại chia theo tử số (WT + phép)."""
    daily = SALARY / divisor
    wd = money_vnd(daily * wd_days)
    leave = money_vnd(daily * leave_days)
    num = wd_days + leave_days
    attend = money_vnd(Decimal("600000") / divisor * num)
    transport = money_vnd(Decimal("800000") / divisor * num)
    gross = wd + leave + attend + transport
    bhxh = money_vnd(SALARY * Decimal("0.08"))
    bhyt = money_vnd(SALARY * Decimal("0.015"))
    bhtn = money_vnd(SALARY * Decimal("0.01"))
    union = Decimal("44100")
    net = gross - bhxh - bhyt - bhtn - union
    return {
        "wd": wd,
        "leave": leave,
        "attend": attend,
        "transport": transport,
        "gross": gross,
        "bhxh": bhxh,
        "bhyt": bhyt,
        "bhtn": bhtn,
        "union": union,
        "net": net,
    }


def test_hr_closed_loop_display_and_payslip_math(client):
    headers = _hr(client)
    today = date.today()
    wt_day = today if today.isoweekday() != 7 else today + timedelta(days=1)
    period = f"{wt_day.year:04d}-{wt_day.month:02d}"
    join = date(wt_day.year, wt_day.month, 1)
    d_work, d_leave, d_extra = _weekdays(wt_day.year, wt_day.month, exclude={wt_day}, n=3)

    # --- Thêm NV ---
    emp = _create(client, headers, "9411", join=join)
    emp_id = emp["id"]
    listed = client.get("/api/employees", headers=headers, params={"status": "active"})
    assert listed.status_code == 200
    assert "9411" in {e["employee_code"] for e in listed.json()}

    # --- Xoá NV: không có DELETE hồ sơ — thôi việc là đường gỡ khỏi đang làm ---
    gone = client.delete(f"/api/employees/{emp_id}", headers=headers)
    assert gone.status_code in (404, 405, 422)
    other = _create(client, headers, "9412", join=join)
    res_del = client.post(
        f"/api/employees/{other['id']}/resignations",
        headers=headers,
        json={"resign_type_code": "DPR", "last_working_date": d_work.isoformat(), "finalize": True},
    )
    assert res_del.status_code == 201, res_del.text
    resigned = client.get("/api/employees", headers=headers, params={"status": "resigned"}).json()
    assert "9412" in {e["employee_code"] for e in resigned}
    active = client.get("/api/employees", headers=headers, params={"status": "active"}).json()
    assert "9412" not in {e["employee_code"] for e in active}

    # --- Gán / sửa phép ---
    ale = _patch_leave(client, headers, "9411", d_leave, "ALE")
    assert ale["leave_code"] == "ALE"
    fle = _patch_leave(client, headers, "9411", d_leave, "FLE")
    assert fle["leave_code"] == "FLE"
    ale2 = _patch_leave(client, headers, "9411", d_leave, "ALE")
    assert ale2["leave_code"] == "ALE"
    sheets = client.get("/api/attendance/timesheets", headers=headers, params={"period": period})
    assert sheets.status_code == 200, sheets.text
    ts_row = next(r for r in sheets.json() if r["employee_code"] == "9411")
    assert float(ts_row["al_days"]) == 1.0

    # --- Chấm công đủ ngày, rồi ra sớm chưa có chế độ ---
    full = _patch_times(client, headers, "9411", d_work, 17)
    assert Decimal(str(full["worked_hours"])) == Decimal("8")
    assert full["early_minutes"] == 0
    early = _patch_times(client, headers, "9411", wt_day, 16)
    assert Decimal(str(early["worked_hours"])) == Decimal("7")
    assert early["early_minutes"] == 60

    # --- Gán thai sản sau khi đã chấm tay → phải cộng 1h, không còn về sớm ---
    preg = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": wt_day.isoformat(),
            "date_to": (wt_day + timedelta(days=30)).isoformat(),
            "note": "QA thai sản",
        },
    )
    assert preg.status_code == 201, preg.text
    after_preg = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": wt_day.isoformat(), "to": wt_day.isoformat(), "employee_code": "9411"},
    )
    assert after_preg.status_code == 200, after_preg.text
    day_wt = after_preg.json()[0]
    assert Decimal(str(day_wt["worked_hours"])) == Decimal("8"), day_wt
    assert day_wt["early_minutes"] == 0
    assert client.get(f"/api/employees/{emp_id}", headers=headers).json()["wt_regime_active"] is True

    # --- Tính lương lần 1: 2 ngày công (đủ + thai sản) + 1 ALE ---
    calc1 = client.post(f"/api/payroll/periods/{period}/calculate", headers=headers)
    assert calc1.status_code == 200, calc1.text
    s1 = _slip(calc1.json(), "9411")
    divisor = Decimal(str(s1["salary_divisor"]))
    exp1 = _expected_net(wd_days=Decimal("2"), leave_days=Decimal("1"), divisor=divisor)
    assert Decimal(str(s1["worked_days"])) == Decimal("2")
    assert Decimal(str(s1["al_days"])) == Decimal("1")
    assert Decimal(str(s1["wd_salary"])) == exp1["wd"]
    assert Decimal(str(s1["gross"])) == exp1["gross"]
    assert Decimal(str(s1["bhxh"])) == exp1["bhxh"]
    assert Decimal(str(s1["bhyt"])) == exp1["bhyt"]
    assert Decimal(str(s1["bhtn"])) == exp1["bhtn"]
    assert Decimal(str(s1["union_fee"])) == exp1["union"]
    assert Decimal(str(s1["net"])) == exp1["net"]
    net1 = Decimal(str(s1["net"]))

    detail1 = client.get(f"/api/payroll/payslips/{s1['id']}/detail", headers=headers)
    assert detail1.status_code == 200, detail1.text
    d1 = detail1.json()
    work_codes = {ln["component_code"] for ln in d1["work_lines"]}
    assert "WD" in work_codes
    assert "ALE" in work_codes
    wd_line = next(ln for ln in d1["work_lines"] if ln["component_code"] == "WD")
    assert Decimal(str(wd_line["quantity"])) == Decimal("2")
    assert Decimal(str(wd_line["amount"])) == exp1["wd"]
    ale_line = next(ln for ln in d1["work_lines"] if ln["component_code"] == "ALE")
    assert Decimal(str(ale_line["quantity"])) == Decimal("1")
    assert Decimal(str(ale_line["amount"])) == exp1["leave"]
    ded_codes = {ln["component_code"] for ln in d1["deduction_lines"]}
    assert {"BHXH", "BHYT", "BHTN", "UNION"} <= ded_codes
    allow_codes = {ln["component_code"] for ln in d1["allowance_lines"]}
    assert "ATTEND" in allow_codes
    assert "TRANSPORT" in allow_codes
    assert Decimal(str(d1["payslip"]["gross"])) == exp1["gross"]
    assert Decimal(str(d1["payslip"]["net"])) == exp1["net"]
    assert Decimal(str(d1["payslip"]["worked_days"])) == Decimal("2")
    assert Decimal(str(d1["payslip"]["al_days"])) == Decimal("1")

    # --- Sửa công: thêm 1 ngày đủ → lương tăng ---
    _patch_times(client, headers, "9411", d_extra, 17)
    calc2 = client.post(f"/api/payroll/periods/{period}/calculate", headers=headers)
    assert calc2.status_code == 200, calc2.text
    s2 = _slip(calc2.json(), "9411")
    exp2 = _expected_net(wd_days=Decimal("3"), leave_days=Decimal("1"), divisor=divisor)
    assert Decimal(str(s2["worked_days"])) == Decimal("3")
    assert Decimal(str(s2["wd_salary"])) == exp2["wd"]
    assert Decimal(str(s2["net"])) == exp2["net"]
    assert Decimal(str(s2["net"])) > net1

    # --- Đổi phép ALE → FLE: cột AL = 0, phiếu dòng FLE 100% ---
    _patch_leave(client, headers, "9411", d_leave, "FLE")
    calc3 = client.post(f"/api/payroll/periods/{period}/calculate", headers=headers)
    assert calc3.status_code == 200, calc3.text
    s3 = _slip(calc3.json(), "9411")
    assert Decimal(str(s3["al_days"])) == Decimal("0")
    detail3 = client.get(f"/api/payroll/payslips/{s3['id']}/detail", headers=headers).json()
    codes3 = {ln["component_code"] for ln in detail3["work_lines"]}
    assert "FLE" in codes3
    assert "ALE" not in codes3
    fle_line = next(ln for ln in detail3["work_lines"] if ln["component_code"] == "FLE")
    assert Decimal(str(fle_line["amount"])) == exp2["leave"]

    # --- Nuôi con: chấm dứt thai sản, gán CHILD 2h, ra 15:00 vẫn 8h ---
    ended = client.post(
        f"/api/employees/{emp_id}/wt-regimes/{preg.json()['id']}/end",
        headers=headers,
    )
    assert ended.status_code == 200, ended.text
    child = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "CHILD",
            "hours_early": 2,
            "date_from": wt_day.isoformat(),
            "date_to": (wt_day + timedelta(days=20)).isoformat(),
            "note": "QA nuôi con nhỏ",
        },
    )
    assert child.status_code == 201, child.text
    child_day = _patch_times(client, headers, "9411", wt_day, 15)
    assert Decimal(str(child_day["worked_hours"])) == Decimal("8")
    assert child_day["early_minutes"] == 0

    calc4 = client.post(f"/api/payroll/periods/{period}/calculate", headers=headers)
    assert calc4.status_code == 200, calc4.text
    s4 = _slip(calc4.json(), "9411")
    assert Decimal(str(s4["worked_days"])) == Decimal("3")
    assert Decimal(str(s4["net"])) == exp2["net"]

    # --- Phát hành ---
    pub = client.post(f"/api/payroll/periods/{period}/publish", headers=headers)
    assert pub.status_code == 200, pub.text
    listed_slips = client.get("/api/payroll/payslips", headers=headers, params={"period": period})
    assert listed_slips.status_code == 200
    row = next(p for p in listed_slips.json() if p["employee_code"] == "9411")
    assert row["status"] in ("published", "confirmed")
    assert Decimal(str(row["net"])) == exp2["net"]

    # --- Thôi việc + tái tuyển ---
    last_day = date(wt_day.year, wt_day.month, monthrange(wt_day.year, wt_day.month)[1])
    bye = client.post(
        f"/api/employees/{emp_id}/resignations",
        headers=headers,
        json={"resign_type_code": "AFL", "last_working_date": last_day.isoformat(), "finalize": True},
    )
    assert bye.status_code == 201, bye.text
    me = client.get(f"/api/employees/{emp_id}", headers=headers).json()
    assert me["status"] == "resigned"
    team = client.get("/api/teams", headers=headers).json()[0]
    nxt = last_day + timedelta(days=1)
    rehire = client.post(
        f"/api/employees/{emp_id}/rehire",
        headers=headers,
        json={
            "rehire_date": nxt.isoformat(),
            "rehire_mode": "fresh_start",
            "team_id": team["id"],
            "status": "active",
            "contract_salary": "5400000",
        },
    )
    assert rehire.status_code == 200, rehire.text
    hired = rehire.json()["employee"]
    assert hired["status"] == "active"
    assert Decimal(str(hired["contract_salary"])) == Decimal("5400000")


def test_payslip_no_wd_line_when_only_annual_leave(client):
    """Chỉ phép năm, không ngày công — phiếu không gán SL phép vào dòng WD."""
    headers = _hr(client)
    today = date.today()
    period = f"{today.year:04d}-{today.month:02d}"
    join = date(today.year, today.month, 1)
    _create(client, headers, "9413", join=join)
    leave_day = _weekdays(today.year, today.month, exclude=set(), n=1)[0]
    _patch_leave(client, headers, "9413", leave_day, "ALE")
    calc = client.post(f"/api/payroll/periods/{period}/calculate", headers=headers)
    assert calc.status_code == 200, calc.text
    s = _slip(calc.json(), "9413")
    assert Decimal(str(s["worked_days"])) == Decimal("0")
    assert Decimal(str(s["al_days"])) == Decimal("1")
    assert Decimal(str(s["wd_salary"])) == Decimal("0")
    detail = client.get(f"/api/payroll/payslips/{s['id']}/detail", headers=headers).json()
    wd_lines = [ln for ln in detail["work_lines"] if ln["component_code"] == "WD"]
    assert wd_lines == []
    ale = next(ln for ln in detail["work_lines"] if ln["component_code"] == "ALE")
    assert Decimal(str(ale["quantity"])) == Decimal("1")
    assert Decimal(str(ale["amount"])) > 0
