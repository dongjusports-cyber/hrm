import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchBlackBox,
  fetchSyncJobs,
  type BlackBox,
  type SyncJob,
} from "../../shared/api";
import { formatDateTimeDDMMYYYY } from "../../shared/formatDate";
import { ConfigTabNav } from "./ConfigTabNav";

type Tab = "actions" | "exports" | "policy" | "sync";

/** Nhật ký hợp nhất — audit + policy + sync_jobs (5.6). */
export function JournalAdminPage() {
  const [tab, setTab] = useState<Tab>("actions");
  const [data, setData] = useState<BlackBox | null>(null);
  const [jobs, setJobs] = useState<SyncJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [bb, sj] = await Promise.all([fetchBlackBox(100), fetchSyncJobs(40)]);
      setData(bb);
      setJobs(sj.items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải nhật ký.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <div className="config-section-page">
      <ConfigTabNav />
      <div className="module-toolbar">
        <h1>Nhật ký hệ thống</h1>
        <button type="button" className="btn-secondary" onClick={() => void reload()}>
          Làm mới
        </button>
      </div>
      <p className="field-hint">
        Gộp audit_logs, xác nhận policy 3 bước, xuất file và sync_jobs Mitapro (23§23.4).
      </p>
      {error && <p className="banner-warn">{error}</p>}

      <div className="dispute-filters" role="tablist">
        {(
          [
            ["actions", "Hành động"],
            ["exports", "Xuất file"],
            ["policy", "Policy 3 bước"],
            ["sync", "Sync Mitapro"],
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
      ) : tab === "sync" ? (
        <div className="table-scroll">
          <table className="simple-table">
            <thead>
              <tr>
                <th>Thời điểm</th>
                <th>Trạng thái</th>
                <th>Đọc</th>
                <th>Chèn</th>
                <th>Bỏ qua</th>
                <th>Nguồn</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 && (
                <tr>
                  <td colSpan={6} className="module-placeholder">
                    Chưa có sync_jobs.
                  </td>
                </tr>
              )}
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{formatDateTimeDDMMYYYY(j.started_at)}</td>
                  <td>{j.status}</td>
                  <td>{j.records_in}</td>
                  <td>{j.records_inserted}</td>
                  <td>{j.records_skipped}</td>
                  <td>{j.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : tab === "actions" ? (
        <table className="kpi-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Người dùng</th>
              <th>Hành động</th>
              <th>Tóm tắt</th>
            </tr>
          </thead>
          <tbody>
            {data.actions.map((row) => (
              <tr key={row.id}>
                <td>{formatDateTimeDDMMYYYY(row.created_at)}</td>
                <td>{row.actor_username ?? "—"}</td>
                <td>{row.action}</td>
                <td>{row.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : tab === "exports" ? (
        <table className="kpi-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Người dùng</th>
              <th>Loại xuất</th>
              <th>Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            {data.exports.map((row) => (
              <tr key={row.id}>
                <td>{formatDateTimeDDMMYYYY(row.created_at)}</td>
                <td>{row.username ?? row.full_name ?? "—"}</td>
                <td>{row.kind}</td>
                <td>{row.filename}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <table className="kpi-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Gói</th>
              <th>Bước</th>
              <th>Người xác nhận</th>
            </tr>
          </thead>
          <tbody>
            {data.policy_confirms.map((row) => (
              <tr key={row.id}>
                <td>{formatDateTimeDDMMYYYY(row.created_at)}</td>
                <td>{row.package_id}</td>
                <td>{row.confirm_step}</td>
                <td>{row.actor_username ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="field-hint" style={{ marginTop: 16 }}>
        Chi tiết hộp đen đầy đủ: <Link to="/m/config/audit-log">Log / Hộp đen (legacy)</Link>
      </p>
    </div>
  );
}
