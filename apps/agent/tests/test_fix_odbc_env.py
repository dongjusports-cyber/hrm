"""Test fix_odbc_env with SQLEXPRESS backslashes in connection string."""

from fix_odbc_env import _replace_mitapro_odbc_line


def test_replace_odbc_line_with_backslash_server():
    text = "MITAPRO_ODBC=Driver={ODBC Driver 17 for SQL Server};Server=.\\SQLEXPRESS;\n"
    resolved = "Driver={ODBC Driver 18 for SQL Server};Server=.\\SQLEXPRESS;Database=MITACOSQL;"
    out = _replace_mitapro_odbc_line(text, resolved)
    assert "MITAPRO_ODBC=" in out
    assert "ODBC Driver 18" in out
    assert ".\\SQLEXPRESS" in out
