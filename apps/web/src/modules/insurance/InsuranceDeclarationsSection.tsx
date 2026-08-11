import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  downloadInsuranceDeclarationBatch,
  fetchInsuranceDeclarations,
  markInsuranceDeclarationsSubmitted,
  proposeInsuranceDeclarations,
  type InsuranceDeclaration,
} from "../../shared/api";
import { formatDateTimeDDMMYYYY } from "../../shared/formatDate";

function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** Khai báo BHXH — đề xuất + tick xuất lô (5.5). */
export function InsuranceDeclarationsSection() {
  const [month, setMonth] = useState(currentMonth);
  const [rows, setRows] = useState<InsuranceDeclaration[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const list = await fetchInsuranceDeclarations({ effective_month: month });
      setRows(list);
      setSelected(new Set(list.filter((r) => r.status === "draft").map((r) => r.id)));
      setError(null);
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : "Không tải khai báo BHXH.");
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    void reload();
  }, [reload]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function onPropose() {
    setLoading(true);
    setOk(null);
    try {
      const res = await proposeInsuranceDeclarations(month);
      setOk(`Đã đề xuất ${res.created_count} dòng mới.`);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Đề xuất thất bại.");
    } finally {
      setLoading(false);
    }
  }

  async function onExport() {
    const ids = [...selected];
    if (!ids.length) {
      setError("Chọn ít nhất một dòng để xuất.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await downloadInsuranceDeclarationBatch(month, ids);
      setOk("Đã tải file CSV.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Xuất lô thất bại.");
    } finally {
      setLoading(false);
    }
  }

  async function onMarkSubmitted() {
    const ids = [...selected];
    if (!ids.length) return;
    setLoading(true);
    try {
      const res = await markInsuranceDeclarationsSubmitted({
        effective_month: month,
        declaration_ids: ids,
      });
      setOk(res.message);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Đánh dấu nộp thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="ins-decl-section users-form-card">
      <div className="module-toolbar">
        <h2>Hồ sơ bảo hiểm — khai báo tháng</h2>
        <label className="period-picker">
          Tháng hiệu lực
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
        </label>
      </div>
      <p className="field-hint">
        Hệ thống đề xuất danh sách báo tăng/giảm/đổi lương — tick chọn rồi xuất một lô (23§23.4).
      </p>
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}
      <div className="module-toolbar">
        <button type="button" className="btn-primary" disabled={loading} onClick={() => void onPropose()}>
          Đề xuất tháng
        </button>
        <button type="button" className="btn-ghost-dark" disabled={loading} onClick={() => void onExport()}>
          Xuất CSV đã chọn
        </button>
        <button type="button" className="btn-ghost-dark" disabled={loading} onClick={() => void onMarkSubmitted()}>
          Đánh dấu đã nộp
        </button>
        <Link to="/m/hr" className="btn-ghost-dark">
          ← Nhân sự
        </Link>
      </div>
      {loading && rows.length === 0 ? (
        <p className="field-hint">Đang tải…</p>
      ) : (
        <div className="table-scroll">
          <table className="simple-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={rows.length > 0 && selected.size === rows.length}
                    onChange={(e) =>
                      setSelected(e.target.checked ? new Set(rows.map((r) => r.id)) : new Set())
                    }
                  />
                </th>
                <th>MSNV</th>
                <th>Họ tên</th>
                <th>Loại</th>
                <th>Lương cũ</th>
                <th>Lương mới</th>
                <th>Trạng thái</th>
                <th>Tạo lúc</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="module-placeholder">
                    Chưa có khai báo — bấm «Đề xuất tháng».
                  </td>
                </tr>
              )}
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(r.id)}
                      disabled={r.status === "submitted"}
                      onChange={() => toggle(r.id)}
                    />
                  </td>
                  <td>{r.employee_code}</td>
                  <td>{r.full_name}</td>
                  <td>{r.declaration_type_label}</td>
                  <td>{Number(r.old_salary).toLocaleString("vi-VN")}</td>
                  <td>{Number(r.new_salary).toLocaleString("vi-VN")}</td>
                  <td>{r.status}</td>
                  <td>{formatDateTimeDDMMYYYY(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
