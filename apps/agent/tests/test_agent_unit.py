"""P2.2 / P6.1 — unit test Agent (không cần SQL Server / API thật)."""

from datetime import datetime, timedelta, timezone

from dj_agent.config import AgentSettings
from dj_agent.sql_reader import MockPunchSource, PunchRow
from dj_agent.state import get_last_sync_at, set_last_sync_at


def test_cloud_requires_https():
    s = AgentSettings(
        dj_api_base_url="http://hrm.example.com",
        dj_agent_token="strong-agent-token-xyz",
        dj_agent_require_https=True,
    )
    errs = s.validate_endpoint()
    assert any("HTTPS" in e for e in errs)


def test_cloud_https_ok():
    s = AgentSettings(
        dj_api_base_url="https://hrm.example.com",
        dj_agent_token="strong-agent-token-xyz",
        dj_agent_require_https=True,
    )
    assert s.validate_endpoint() == []


def test_local_http_allowed_without_require_https():
    s = AgentSettings(
        dj_api_base_url="http://127.0.0.1:8000",
        dj_agent_token="change_me_agent_token",
        dj_agent_require_https=False,
    )
    assert s.validate_endpoint() == []



def test_punch_to_api_dict_adds_vn_tz_when_naive():
    row = PunchRow("5290", datetime(2025, 10, 1, 8, 1), "FP1")
    d = row.to_api_dict()
    assert d["employee_code"] == "5290"
    assert "+07:00" in d["punch_time"]
    assert d["ma_cham_cong"] == "FP1"


def test_mock_source_filters_window():
    tz = timezone(timedelta(hours=7))
    rows = [
        PunchRow("5290", datetime(2025, 10, 1, 8, 0, tzinfo=tz)),
        PunchRow("5290", datetime(2025, 10, 2, 8, 0, tzinfo=tz)),
    ]
    src = MockPunchSource(rows)
    got = src.fetch_punches(
        datetime(2025, 10, 1, 0, 0, tzinfo=tz),
        datetime(2025, 10, 2, 0, 0, tzinfo=tz),
    )
    assert len(got) == 1
    assert got[0].punch_time.day == 1


def test_state_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    when = datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc)
    set_last_sync_at(path, when, extra={"last_inserted": 3})
    loaded = get_last_sync_at(path)
    assert loaded is not None
    assert loaded == when


def test_to_mitapro_naive_converts_utc_to_vn():
    from dj_agent.sql_reader import to_mitapro_naive

    utc = datetime(2026, 8, 17, 2, 28, tzinfo=timezone.utc)
    naive = to_mitapro_naive(utc)
    assert naive.tzinfo is None
    assert naive.hour == 9
    assert naive.minute == 28


def test_compute_window_covers_today_vn(tmp_path):
    from dj_agent.sync_loop import compute_window

    s = AgentSettings(state_file=str(tmp_path / "state.json"), sync_overlap_minutes=30)
    now = datetime(2026, 8, 17, 2, 28, tzinfo=timezone.utc)  # 09:28 VN
    set_last_sync_at(s.state_path, now)
    dt_from, dt_to = compute_window(s, now=now)
    vn = timezone(timedelta(hours=7))
    assert dt_from.astimezone(vn).hour == 0
    assert dt_from.astimezone(vn).date() == now.astimezone(vn).date()
    assert dt_to == now
