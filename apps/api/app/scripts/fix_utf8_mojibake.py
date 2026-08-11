"""Sửa chữ Việt bị lỗi encoding (UTF-8 hiển thị như WIN1252) sau restore backup UTF-16.

Chạy một lần trên máy nhà:
  docker compose exec api python -m app.scripts.fix_utf8_mojibake
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.database import SessionLocal, engine

# (bảng, cột) — chỉ cột text hiển thị UI / hồ sơ
TEXT_COLUMNS: list[tuple[str, str]] = [
    ("users", "full_name"),
    ("portal_tabs", "title"),
    ("portal_tabs", "description"),
    ("employees", "full_name"),
    ("employees", "position_title"),
    ("employees", "permanent_address"),
    ("employees", "temporary_address"),
    ("departments", "name"),
    ("departments", "name_local"),
    ("teams", "name"),
    ("teams", "name_local"),
    ("positions", "name"),
    ("positions", "name_local"),
    ("jobs", "name"),
    ("jobs", "name_local"),
    ("leave_types", "name"),
    ("pay_components", "name"),
    ("lookup_values", "name"),
    ("lookup_values", "name_local"),
    ("work_shifts", "name"),
    ("policy_packages", "name"),
    ("ai_alerts", "title"),
    ("ai_alerts", "body"),
]


def main() -> None:
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION fix_mojibake(t text) RETURNS text AS $$
                BEGIN
                  IF t IS NULL OR t = '' THEN
                    RETURN t;
                  END IF;
                  RETURN convert_from(convert_to(t, 'WIN1252'), 'UTF8');
                EXCEPTION WHEN OTHERS THEN
                  RETURN t;
                END;
                $$ LANGUAGE plpgsql IMMUTABLE;
                """
            )
        )
        conn.commit()

        total = 0
        for table, column in TEXT_COLUMNS:
            sql = text(
                f"""
                UPDATE {table}
                SET {column} = fix_mojibake({column})
                WHERE {column} IS NOT NULL
                  AND {column} <> fix_mojibake({column})
                """
            )
            result = conn.execute(sql)
            conn.commit()
            n = result.rowcount or 0
            if n:
                print(f"  {table}.{column}: {n} dong")
                total += n

        conn.execute(text("DROP FUNCTION IF EXISTS fix_mojibake(text)"))
        conn.commit()

    print(f"Xong — da sua {total} o text.")


if __name__ == "__main__":
    main()
