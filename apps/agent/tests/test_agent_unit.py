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
