"""OT: ngưỡng 17:15 → 17:30 (nghỉ cơm); phút OT vẫn từ 17:00.

Revision ID: 20260818_0055
Revises: 20260818_0054
"""

from __future__ import annotations

import json

from alembic import op

revision = "20260818_0055"
down_revision = "20260818_0054"
branch_labels = None
depends_on = None

NOTE_NEW = (
    "Bấm 17h00–17h30 không tính vân tay / không OT. "
    "Bấm ra sau 17h30 mới có OT; số phút vẫn tính từ 17h00 (vd. ra 20h00 = 3 giờ). "
    "Th3+Th5: 17h–20h sổ; sau 20h → ngoài."
)
NOTE_OLD = (
    "Bấm ra sau 17h15 mới có OT; số phút OT tính từ 17h00. "
    "Th3+Th5: 17h-20h sổ; sau 20h → ngoài."
)


def _apply(on_books_after: str, grace: int, note: str) -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    rows = bind.exec_driver_sql("SELECT id, payload FROM policy_packages").fetchall()
    for pkg_id, payload in rows:
        if payload is None:
            continue
        data = json.loads(payload) if isinstance(payload, (str, bytes)) else dict(payload)
        ot = dict(data.get("ot_split") or {})
        ot["on_books_after"] = on_books_after
        ot["ot_grace_minutes"] = grace
        ot["ignore_punches_from"] = "17:00"
        ot["ignore_punches_until"] = "17:30"
        ot["note"] = note
        data["ot_split"] = ot
        dumped = json.dumps(data, ensure_ascii=False)
        if dialect == "postgresql":
            bind.exec_driver_sql(
                "UPDATE policy_packages SET payload = CAST(%s AS json) WHERE id = %s",
                (dumped, pkg_id),
            )
        else:
            bind.exec_driver_sql(
                "UPDATE policy_packages SET payload = ? WHERE id = ?",
                (dumped, pkg_id),
            )


def upgrade() -> None:
    _apply("17:30", 30, NOTE_NEW)


def downgrade() -> None:
    _apply("17:15", 15, NOTE_OLD)
