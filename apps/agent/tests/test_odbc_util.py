"""Unit test ODBC driver resolution."""

from dj_agent.odbc_util import configured_driver, resolve_odbc_conn_str


def test_resolve_keeps_working_driver(monkeypatch):
    monkeypatch.setattr(
        "dj_agent.odbc_util.installed_drivers",
        lambda: ["ODBC Driver 17 for SQL Server"],
    )
    raw = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=.\\SQLEXPRESS;Database=MITACOSQL;Trusted_Connection=yes;"
    )
    out, picked = resolve_odbc_conn_str(raw)
    assert picked is None
    assert out == raw


def test_resolve_swaps_missing_driver(monkeypatch):
    monkeypatch.setattr(
        "dj_agent.odbc_util.installed_drivers",
        lambda: ["ODBC Driver 18 for SQL Server"],
    )
    raw = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=.\\SQLEXPRESS;Database=MITACOSQL;Trusted_Connection=yes;"
    )
    out, picked = resolve_odbc_conn_str(raw)
    assert picked == "ODBC Driver 18 for SQL Server"
    assert configured_driver(out) == "ODBC Driver 18 for SQL Server"
