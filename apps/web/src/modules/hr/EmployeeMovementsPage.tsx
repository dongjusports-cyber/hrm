import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchEmployees,
  fetchHrMovements,
  type Employee,
  type HrMovement,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";

const TYPE_LABEL: Record<string, string> = {
  assignment: "Chuyển tổ",
  salary: "Lương",
  violation: "Vi phạm",
};

/** Nhân Sự → Biến động HR (23§23.4). */
export function EmployeeMovementsPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [empFilter, setEmpFilter] = useState("");
  const [movements, setMovements] = useState<HrMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchEmployees()
      .then(setEmployees)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    setLoading(true);
    void fetchHrMovements({ employee_id: empFilter || undefined, limit: 300 })
      .then(setMovements)
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Không tải biến động.");
      })
      .finally(() => setLoading(false));
  }, [empFilter]);

  const empOptions = useMemo(
    () =>
      [...employees].sort((a, b) => a.employee_code.localeCompare(b.employee_code, "vi")),
    [employees],
  );

  return (
    <div className="config-section-page">
      <p className="field-hint">
        <Link to="/m/hr">← Nhân Sự</Link>
      </p>
      <h1>Biến động nhân sự</h1>
      <p className="field-hint">
        Hợp nhất chuyển tổ, tăng lương (audit) và vi phạm — mỗi dòng có trước/sau, số quyết định,
        người duyệt (23§23.4).
      </p>
      {error && <p className="banner-warn">{error}</p>}

      <div className="module-toolbar">
        <label className="field">
          <span>Lọc theo nhân viên</span>
          <select value={empFilter} onChange={(e) => setEmpFilter(e.target.value)}>
            <option value="">— Tất cả —</option>
            {empOptions.map((e) => (
              <option key={e.id} value={e.id}>
                {e.employee_code} — {e.full_name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table-scroll">
        <table className="simple-table">
          <thead>
            <tr>
              <th>Ngày</th>
              <th>Loại</th>
              <th>MSNV</th>
              <th>Họ tên</th>
              <th>Nội dung</th>
              <th>Trước</th>
              <th>Sau</th>
              <th>Số QĐ</th>
              <th>Người duyệt</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={9} className="module-placeholder">
                  Đang tải…
                </td>
              </tr>
            )}
            {!loading && movements.length === 0 && (
              <tr>
                <td colSpan={9} className="module-placeholder">
                  Chưa có biến động.
                </td>
              </tr>
            )}
            {movements.map((m) => (
              <tr key={m.id}>
                <td>{formatDateDDMMYYYY(m.occurred_at)}</td>
                <td>{TYPE_LABEL[m.movement_type] ?? m.movement_type}</td>
                <td>{m.employee_code}</td>
                <td>{m.full_name}</td>
                <td>{m.summary}</td>
                <td>{m.value_before ?? "—"}</td>
                <td>{m.value_after ?? "—"}</td>
                <td>{m.decision_no ?? "—"}</td>
                <td>{m.approved_by_name ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
