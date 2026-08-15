"""Ngưỡng chuyên cần mới (22§22.3, 2026-08-15): trễ 2/5, sớm 2/5.

Sửa CẢ HAI nguồn tham số:
- policy_packages.payload.attendance_penalties (Engine lương đọc — ảnh hưởng tiền)
- attendance_bonus_rules (chỉ API hiển thị)

late_half: 3 → 2, early_zero: 4 → 5. Giữ early_half=2, late_zero=5.

JSON vs JSONB: test chạy SQLite (PayloadType = JSON().with_variant(JSONB(), "postgresql")).
jsonb_set chỉ chạy Postgres → bọc theo dialect; nhánh khác đọc–sửa–ghi bằng Python.
"""

import json

from alembic import op

revision = "20260815_0050"
down_revision = "20260812_0049"
branch_labels = None
depends_on = None


def _rewrite_payload_generic(new_late_half: int, new_early_zero: int) -> None:
    """Đọc–sửa–ghi payload cho dialect không hỗ trợ jsonb_set (vd. SQLite)."""
    bind = op.get_bind()
    rows = bind.exec_driver_sql(
        "SELECT id, payload FROM policy_packages WHERE is_active = 1"
    ).fetchall()
    for row in rows:
        pkg_id, payload = row[0], row[1]
        data = json.loads(payload) if isinstance(payload, (str, bytes)) else dict(payload)
        pen = dict(data.get("attendance_penalties") or {})
        pen["late_half"] = new_late_half
        pen["early_zero"] = new_early_zero
        data["attendance_penalties"] = pen
        bind.exec_driver_sql(
            "UPDATE policy_packages SET payload = ? WHERE id = ?",
            (json.dumps(data), pkg_id),
        )


def _apply(new_late_half: int, new_early_zero: int) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # payload là kiểu `json` (tạo bằng sa.JSON() ở migration 0002) → phải ép
        # sang jsonb cho jsonb_set rồi ép trả lại json khi ghi.
        op.execute(
            f"""
            UPDATE policy_packages
            SET payload = jsonb_set(
                jsonb_set(payload::jsonb, '{{attendance_penalties,late_half}}', '{new_late_half}'),
                '{{attendance_penalties,early_zero}}', '{new_early_zero}'
            )::json
            WHERE is_active = true
            """
        )
    else:
        _rewrite_payload_generic(new_late_half, new_early_zero)

    op.execute(
        f"""
        UPDATE attendance_bonus_rules
        SET late_count_half = {new_late_half}, early_count_zero = {new_early_zero}
        WHERE effective_to IS NULL
        """
    )


def upgrade() -> None:
    _apply(new_late_half=2, new_early_zero=5)


def downgrade() -> None:
    _apply(new_late_half=3, new_early_zero=4)
