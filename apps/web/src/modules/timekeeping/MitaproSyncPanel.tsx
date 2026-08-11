import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import {
  fetchIntegrationStatus,
  fetchSyncJobs,
  fetchUnlinkedPunches,
  relinkPunches,
  requestSyncNow,
  requestSyncRange,
  type IntegrationStatus,
  type SyncJob,
  type UnlinkedPunch,
} from "../../shared/api";
import { formatDateTimeDDMMYYYY } from "../../shared/formatDate";
import { labelJobStatus } from "../../shared/viLabels";

function fmtDt(iso: string | null | undefined): string {
  return formatDateTimeDDMMYYYY(iso);
}

type Props = {
  period: string;
  onChanged?: () => void;
};

export function MitaproSyncPanel({ period, onChanged }: Props) {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [jobs, setJobs] = useState<SyncJob[]>([]);
  const [unlinked, setUnlinked] = useState<UnlinkedPunch[]>([]);
  const [unlinkedTotal, setUnlinkedTotal] = useState(0);
  const [rangeFrom, setRangeFrom] = useState(`${period}-01`);
  const [rangeTo, setRangeTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [st, sj, ul] = await Promise.all([
        fetchIntegrationStatus(),
        fetchSyncJobs(80),
        fetchUnlinkedPunches(120),
      ]);
      setStatus(st);
      setJobs(sj.items);
      setUnlinked(ul.items);
      setUnlinkedTotal(ul.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải màn đồng bộ Mitapro.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setRangeFrom(`${period}-01`);
    const [y, m] = period.split("-").map(Number);
    const last = new Date(y, m, 0).getDate();
    setRangeTo(`${period}-${String(last).padStart(2, "0")}`);
  }, [period]);

  const jobCols = useMemo<ColDef<SyncJob>[]>(
    () => [
      {
        field: "started_at",
        headerName: "Bắt đầu",
        width: 150,
        valueFormatter: (p) => fmtDt(p.value),
      },
      {
        field: "finished_at",
        headerName: "Kết thúc",
        width: 150,
        valueFormatter: (p) => fmtDt(p.value),
      },
      {
        field: "status",
        headerName: "Trạng thái",
        width: 110,
        valueFormatter: (p) => labelJobStatus(p.value),
      },
      { field: "records_in", headerName: "Đọc", width: 72 },
      { field: "records_inserted", headerName: "Chèn", width: 72 },
      { field: "records_skipped", headerName: "Bỏ qua", width: 82 },
      {
        colId: "range",
        headerName: "Khoảng",
        width: 190,
        valueGetter: (p) => {
          const f = p.data?.sync_date_from;
          const t = p.data?.sync_date_to;
          if (f && t) return `${f} → ${t}`;
          return "—";
        },
      },
      { field: "message", headerName: "Ghi chú / lỗi", flex: 1, minWidth: 180 },
    ],
    [],
  );

  const punchCols = useMemo<ColDef<UnlinkedPunch>[]>(
    () => [
      { field: "employee_code", headerName: "MSNV", width: 90, pinned: "left" },
      {
        field: "punch_time",
        headerName: "Giờ chấm",
        width: 160,
        valueFormatter: (p) => fmtDt(p.value),
      },
      {
        field: "direction",
        headerName: "Chiều",
        width: 72,
        valueFormatter: (p) => p.value ?? "—",
      },
      {
        field: "ma_cham_cong",
        headerName: "Mã CC",
        width: 100,
        valueFormatter: (p) => p.value ?? "—",
      },
      {
        field: "device_id",
        headerName: "Máy",
        width: 90,
        valueFormatter: (p) => p.value ?? "—",
      },
    ],
    [],
  );

  async function onSyncNow() {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const job = await requestSyncNow();
      setOk(job.message);
      await load();
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không yêu cầu đồng bộ được.");
    } finally {
      setBusy(false);
    }
  }

  async function onSyncRange(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const job = await requestSyncRange(rangeFrom, rangeTo);
      setOk(job.message);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không yêu cầu đồng bộ khoảng ngày được.");
    } finally {
      setBusy(false);
    }
  }

  async function onRelink() {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const r = await relinkPunches();
      setOk(`Đã gắn lại ${r.updated} punch · còn ${r.remaining_unlinked} chưa khớp.`);
      await load();
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không gắn lại punch được.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="tk-sync-panel">
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      {status?.stale_warning && (
        <p className="banner-warn tk-sync-stale">
          Cảnh báo: hơn {status.stale_threshold_hours} giờ không có dữ liệu chấm công mới
          {status.hours_since_data != null ? ` (~${Math.round(status.hours_since_data)}h)` : ""}. Kiểm tra
          Agent Mitapro trên máy công ty.
        </p>
      )}

      <div className="tk-sync-summary">
        <span>
          Agent:{" "}
          <strong className={status?.agent_configured ? "tk-ok" : "tk-warn"}>
            {status?.agent_configured ? "đã cấu hình" : "chưa cấu hình token"}
          </strong>
        </span>
        <span>
          Lần chấm: <strong>{status?.punch_count ?? "—"}</strong>
        </span>
        <span>
          Chưa khớp NV:{" "}
          <strong className={(status?.punch_unlinked_count ?? 0) > 0 ? "tk-warn" : ""}>
            {status?.punch_unlinked_count ?? 0}
          </strong>
        </span>
        <span>Lần chấm gần nhất: {fmtDt(status?.last_punch_at)}</span>
        <button type="button" className="btn-ghost-dark" disabled={busy || loading} onClick={() => void load()}>
          Làm mới
        </button>
      </div>

      <div className="tk-sync-actions">
        <button type="button" className="btn-ghost-dark" disabled={busy} onClick={() => void onSyncNow()}>
          Đồng bộ ngay
        </button>
        <form className="tk-sync-range-form" onSubmit={(e) => void onSyncRange(e)}>
          <label>
            Từ
            <input type="date" value={rangeFrom} onChange={(e) => setRangeFrom(e.target.value)} required />
          </label>
          <label>
            Đến
            <input type="date" value={rangeTo} onChange={(e) => setRangeTo(e.target.value)} required />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            Chạy lại khoảng ngày
          </button>
        </form>
      </div>

      <section className="tk-sync-section">
        <h3 className="tk-sync-title">Nhật ký đồng bộ Mitapro ({jobs.length})</h3>
        <div className="tk-sync-grid ag-theme-quartz">
          <AgGridReact<SyncJob>
            rowData={jobs}
            columnDefs={jobCols}
            getRowId={(p) => p.data.id}
            domLayout="autoHeight"
            defaultColDef={{
              sortable: true,
              resizable: true,
              filter: false,
              suppressHeaderMenuButton: true,
            }}
          />
        </div>
      </section>

      <section className="tk-sync-section">
        <div className="tk-sync-section-head">
          <h3 className="tk-sync-title">
            Punch chưa khớp người ({unlinkedTotal})
          </h3>
          <button type="button" className="btn-ghost-dark" disabled={busy} onClick={() => void onRelink()}>
            Gắn lại theo MSNV
          </button>
        </div>
        <p className="field-hint">
          MSNV không có trong Nhân Sự hoặc chưa khớp mã chấm công — thêm hồ sơ NV rồi bấm Gắn lại.
        </p>
        <div className="tk-sync-grid ag-theme-quartz">
          <AgGridReact<UnlinkedPunch>
            rowData={unlinked}
            columnDefs={punchCols}
            getRowId={(p) => String(p.data.id)}
            domLayout="autoHeight"
            defaultColDef={{
              sortable: true,
              resizable: true,
              filter: false,
              suppressHeaderMenuButton: true,
            }}
          />
        </div>
      </section>

      {loading && <p className="field-hint">Đang tải…</p>}
    </div>
  );

}
