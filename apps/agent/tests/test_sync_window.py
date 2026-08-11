"""Agent — pending job dùng sync_date_from/to."""

from dj_agent.config import AgentSettings
from dj_agent.sync_loop import _window_from_job


def test_window_from_job_parses_dates():
    job = {"sync_date_from": "2025-10-01", "sync_date_to": "2025-10-07"}
    settings = AgentSettings()
    dt_from, dt_to = _window_from_job(job, settings)
    assert dt_from is not None
    assert dt_to is not None
    assert dt_from.day == 1
    assert dt_to.day == 7
    assert dt_from.tzinfo is not None


def test_window_from_job_empty_when_missing():
    settings = AgentSettings()
    assert _window_from_job({}, settings) == (None, None)
    assert _window_from_job({"sync_date_from": "2025-10-01"}, settings) == (None, None)
