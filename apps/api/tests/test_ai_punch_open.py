"""Lọc / mở DS chấm lẻ hôm qua."""

from datetime import datetime, timedelta

from app.core.config import get_settings
from app.modules.ai.fast_reply import detect_ops_kind, wants_punch_review
from app.modules.ai.punch_open import parse_punch_window, punch_review_href
from app.modules.attendance.engine import VN_TZ


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_detect_odd_yesterday_command():
    q = "lọc và mở ds nhân viên lẻ hôm qua để tôi chấm công"
    assert wants_punch_review(q) is True
    assert detect_ops_kind(q) == "punch_review"
    win = parse_punch_window(q)
    today = datetime.now(tz=VN_TZ).date()
    assert win.single_day is True
    assert win.wants_open is True
    assert win.date_from == today - timedelta(days=1)
    href = punch_review_href(win)
    assert "view=daily" in href
    assert f"date={win.date_from.isoformat()}" in href
    assert "odd=1" in href


def test_parse_punch_window_month_default():
    win = parse_punch_window("Ai chấm lẻ tháng này")
    assert win.single_day is False
    assert "odd=" not in punch_review_href(win)


def test_parse_punch_window_hom_kia_and_iso():
    today = datetime.now(tz=VN_TZ).date()
    kia = parse_punch_window("chấm lẻ hôm kia")
    assert kia.date_from == today - timedelta(days=2)
    assert kia.single_day is True
    iso = parse_punch_window("ds lẻ 2026-08-19")
    assert iso.date_from.isoformat() == "2026-08-19"
    assert "odd=1" in punch_review_href(iso)
    vn = parse_punch_window("nhân viên lẻ 19/08")
    assert vn.date_from.month == 8 and vn.date_from.day == 19


def test_ai_assist_open_odd_yesterday(client):
    today = datetime.now(tz=VN_TZ).date()
    yesterday = today - timedelta(days=1)
    iso = yesterday.isoformat()
    push = client.post(
        "/api/integrations/mitapro/push",
        headers={"X-Agent-Token": get_settings().agent_token},
        json={"punches": [{"employee_code": "5290", "punch_time": f"{iso}T08:00:00+07:00"}]},
    )
    assert push.status_code == 200, push.text
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "lọc và mở ds nhân viên lẻ hôm qua để tôi chấm công"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "punch_review"
    assert body["model_name"] == "direct"
    assert "5290" in body["answer"]
    assert "không tự" in body["answer"].lower() or "không bịa" in body["answer"].lower()
    hrefs = [s.get("href") or "" for s in body.get("suggestions") or []]
    assert any(iso in h and "odd=1" in h and "view=daily" in h for h in hrefs)


def test_ai_assist_month_punch_review_no_odd_query(client):
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "Ai chấm lẻ tháng này"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "punch_review"
    hrefs = [s.get("href") or "" for s in body.get("suggestions") or []]
    assert hrefs
    assert all("odd=" not in h for h in hrefs)
    msgs = [s.get("message") or "" for s in body.get("suggestions") or []]
    assert any("hôm qua" in m for m in msgs)
