import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchViolationBoard,
  type EmployeeViolationBoardItem,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { type HrNavState } from "../../shared/hrNavState";
import { labelEmpStatus } from "../../shared/viLabels";

/** Danh sách NV có biên bản vi phạm — full màn từ ô Nhân Sự. */
export function ViolationsBoardPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<EmployeeViolationBoardItem[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchViolationBoard()
      .then((list) => {
        if (!cancelled) setRows(list);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Không tải được danh sách vi phạm.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(
      (r) =>
        r.employee_code.toLowerCase().includes(needle) ||
        r.full_name.toLowerCase().includes(needle) ||
        (r.department_code || "").toLowerCase().includes(needle),
    );
  }, [rows, q]);

  return (
    <div className="hr-board-page">
      <nav className="breadcrumb">
        <Link to="/">Portal</Link>
        <span aria-hidden> › </span>
        <Link to="/m/hr">Nhân Sự</Link>
        <span aria-hidden> › </span>
        <span>Vi phạm</span>
      </nav>

      <div className="hr-list-head">
        <h1>Vi phạm</h1>
        <p className="field-hint">
          Nhân viên có biên bản — bấm dòng để mở tab Vi phạm trong hồ sơ (chữ lớn, full khung).
        </p>
      </div>

      <div className="hr-toolbar">
        <input
          className="hr-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Tìm MSNV / họ tên / bộ phận"
          aria-label="Tìm nhân viên vi phạm"
        />
        <span className="field-hint">{filtered.length} người</span>
        <Link to="/m/hr" className="btn-ghost-dark">
          ← Nhân Sự
        </Link>
      </div>

      {error && <p className="banner-warn">{error}</p>}

      <ul className="hr-board-list" aria-label="Danh sách nhân viên vi phạm">
        {filtered.length === 0 && !error && (
          <li className="module-placeholder">Chưa có biên bản vi phạm nào.</li>
        )}
        {filtered.map((r) => (
          <li key={r.employee_id}>
            <button
              type="button"
              className="hr-board-row"
              onClick={() =>
                navigate(`/m/hr/employees/${r.employee_id}?tab=violations`, {
                  state: { hrListBack: "/m/hr/violations" } satisfies HrNavState,
                })
              }
            >
              <span className="hr-board-main">
                <strong>
                  {r.employee_code} — {r.full_name}
                </strong>
                <span className="field-hint">
                  {r.department_code || "—"} · {labelEmpStatus(r.status)}
                  {r.last_occurred_at
                    ? ` · gần nhất ${formatDateDDMMYYYY(r.last_occurred_at)}`
                    : ""}
                </span>
              </span>
              <span className="hr-board-badge">{r.violation_count} lần</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
