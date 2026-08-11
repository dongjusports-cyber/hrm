import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchIntegrationStatus,
  fetchSyncJobs,
  requestSyncNow,
  type IntegrationStatus,
  type SyncJob,
} from "../../shared/api";
import { formatDateTimeDDMMYYYY } from "../../shared/formatDate";
import { ConfigTabNav } from "./ConfigTabNav";

/** Máy & tích hợp — Mitapro, QR công nhân (5.6). */
export function IntegrationAdminPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [jobs, setJobs] = useState<SyncJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const [st, j] = await Promise.all([fetchIntegrationStatus(), fetchSyncJobs(30)]);
    setStatus(st);
    setJobs(j.items);
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof Error ? e.message : "Không tải tích hợp."));
  }, []);

  return (
    <div className="config-section-page">
      <ConfigTabNav />
      <h1>Máy &amp; tích hợp</h1>
      <p className="field-hint">
        Chuỗi Mitapro · chu kỳ sync · máy chấm công · cổng QR công nhân (23§23.4).
      </p>
      {error && <p className="banner-warn">{error}</p>}
      {status && (
        <div className="kpi-cards">
          <article className="kpi-card">
            <p>Agent Mitapro</p>
            <strong>{status.agent_configured ? "Đã cấu hình" : "Chưa cấu hình"}</strong>
          </article>
          <article className="kpi-card">
            <p>Lần sync OK gần nhất</p>
            <strong>
              {status.last_success_at ? formatDateTimeDDMMYYYY(status.last_success_at) : "—"}
            </strong>
          </article>
          <article className="kpi-card">
            <p>Punch chưa khớp NV</p>
            <strong>{status.punch_unlinked_count}</strong>
          </article>
          <article className="kpi-card">
            <p>Cảnh báo dữ liệu cũ</p>
            <strong>{status.stale_warning ? "Có" : "Không"}</strong>
          </article>
        </div>
      )}
      {status?.detail && <p className="field-hint">{status.detail}</p>}
      <div className="module-toolbar">
        <Link to="/m/timekeeping" className="btn-primary">
          Mở Chấm Công · Mitapro
        </Link>
        <Link to="/admin/qr-code" className="btn-ghost-dark">
          Mã QR công nhân
        </Link>
        <button
          type="button"
          className="btn-ghost-dark"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            void requestSyncNow()
              .then(() => reload())
              .catch((e) => setError(e instanceof Error ? e.message : "Sync thất bại."))
              .finally(() => setBusy(false));
          }}
        >
          Chạy sync ngay
        </button>
        <button type="button" className="btn-ghost-dark" onClick={() => navigate("/m/config/journal")}>
          Xem nhật ký sync
        </button>
      </div>
      <h2>Lịch sử sync_jobs</h2>
      <div className="table-scroll">
        <table className="simple-table">
          <thead>
            <tr>
              <th>Thời điểm</th>
              <th>Trạng thái</th>
              <th>Đọc</th>
              <th>Chèn</th>
              <th>Bỏ qua</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={5} className="module-placeholder">
                  Chưa có job — bấm «Chạy sync ngay» hoặc mở Chấm Công.
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
