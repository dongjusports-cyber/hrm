import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchBlackBox, type BlackBox } from "../../shared/api";
import { formatDateTimeDDMMYYYY } from "../../shared/formatDate";

type Tab = "actions" | "exports" | "policy";

/** Cấu Hình → Log / Hộp đen (Admin). Không hiện số lương chi tiết. */
export function AuditLogPage() {
  const [tab, setTab] = useState<Tab>("actions");
  const [data, setData] = useState<BlackBox | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fetchBlackBox(100));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải hộp đen.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <div className="config-section-page">
      <p className="field-hint">
        <Link to="/m/config">← Cấu Hình</Link>
      </p>
      <div className="module-toolbar">
        <h1>Log / Hộp đen</h1>
        <button type="button" className="btn-secondary" onClick={() => void reload()}>
          Làm mới
        </button>
      </div>
      <p className="field-hint">
        {data?.note ??
          "Nhật ký hành động Admin/HR, xuất file, xác nhận policy. Không lưu mật khẩu / API key / lương từng đồng."}
      </p>
      <p className="field-hint">
        Backup DB: chạy <code>ops/backup.ps1</code> (Windows) hoặc <code>ops/backup.sh</code> — xem{" "}
        <code>ops/README.md</code>.
      </p>
      {error && <p className="banner-warn">{error}</p>}

      <div className="dispute-filters" role="tablist">
        {(
          [
            ["actions", "Hành động"],
            ["exports", "Xuất file"],
            ["policy", "Policy 3 bước"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            className={tab === key ? "btn-primary" : "btn-secondary"}
            aria-selected={tab === key}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading || !data ? (
        <p className="field-hint">Đang tải…</p>
      ) : tab === "actions" ? (
        <table className="kpi-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Người dùng</th>
              <th>Hành động</th>
              <th>Đối tượng</th>
              <th>Tóm tắt</th>
            </tr>
          </thead>
          <tbody>
            {data.actions.length === 0 ? (
              <tr>
                <td colSpan={5}>Chưa có log hành động.</td>
              </tr>
            ) : (
              data.actions.map((a) => (
                <tr key={a.id}>
                  <td>
                    {a.created_at
                      ? formatDateTimeDDMMYYYY(a.created_at)
                      : "—"}
                  </td>
                  <td>{a.actor_username ?? "—"}</td>
                  <td>
                    <code>{a.action}</code>
                  </td>
                  <td>
                    {a.entity_type}
                    {a.entity_id ? `:${a.entity_id}` : ""}
                  </td>
                  <td>{a.summary}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      ) : tab === "exports" ? (
        <table className="kpi-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Người dùng</th>
              <th>Loại</th>
              <th>Kỳ</th>
              <th>Số dòng</th>
              <th>File</th>
            </tr>
          </thead>
          <tbody>
            {data.exports.length === 0 ? (
              <tr>
                <td colSpan={6}>Chưa có lần xuất file.</td>
              </tr>
            ) : (
              data.exports.map((e) => (
                <tr key={e.id}>
                  <td>
                    {e.created_at
                      ? formatDateTimeDDMMYYYY(e.created_at)
                      : "—"}
                  </td>
                  <td>{e.full_name ?? e.username ?? "—"}</td>
                  <td>
                    <code>{e.kind}</code>
                  </td>
                  <td>{e.period ?? "—"}</td>
                  <td>{e.row_count}</td>
                  <td>{e.filename}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      ) : (
        <table className="kpi-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Người dùng</th>
              <th>Gói</th>
              <th>Bước</th>
              <th>Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            {data.policy_confirms.length === 0 ? (
              <tr>
                <td colSpan={5}>Chưa có lần xác nhận policy 3 bước.</td>
              </tr>
            ) : (
              data.policy_confirms.map((p) => (
                <tr key={p.id}>
                  <td>
                    {p.created_at
                      ? formatDateTimeDDMMYYYY(p.created_at)
                      : "—"}
                  </td>
                  <td>{p.actor_username ?? "—"}</td>
                  <td>
                    <code>{p.package_id.slice(0, 8)}…</code>
                  </td>
                  <td>{p.confirm_step}</td>
                  <td>{p.note}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
