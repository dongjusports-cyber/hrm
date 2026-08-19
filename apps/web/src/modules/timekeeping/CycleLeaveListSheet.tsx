import { useCallback, useEffect, useState } from "react";
import {
  exportCycleLeaveExcel,
  fetchCycleLeaveList,
  type CycleLeaveRow,
} from "../../shared/api";
import { companyExcelFilename } from "../../shared/excelFilename";
import { formatDateDDMMYYYY, formatTimeHHMM } from "../../shared/formatDate";
import { FullScreenSheet } from "../../shared/FullScreenSheet";

type Props = {
  open: boolean;
  period: string;
  onClose: () => void;
  onExported?: (message: string) => void;
};

function fmtHours(v: unknown): string {
  const n = Number(v);
  if (v == null || v === "" || Number.isNaN(n)) return "—";
  return n.toFixed(2).replace(/\.?0+$/, "");
}

export function CycleLeaveListSheet({ open, period, onClose, onExported }: Props) {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<CycleLeaveRow[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await fetchCycleLeaveList(period));
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : "Không tải danh sách chu kỳ được.");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    if (!open) return;
    void load();
  }, [open, load]);

  async function onExport() {
    setExporting(true);
    setError(null);
    try {
      const blob = await exportCycleLeaveExcel(period);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = companyExcelFilename("Chu kỳ", { period });
      a.click();
      URL.revokeObjectURL(url);
      onExported?.(`Đã xuất danh sách chu kỳ ${period}: ${rows.length} lượt.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xuất Excel được.");
    } finally {
      setExporting(false);
    }
  }

  const busy = loading || exporting;

  return (
    <FullScreenSheet
      open={open}
      title={`Danh sách chu kỳ · kỳ ${period}`}
      subtitle="NV HR đã tích trong kỳ — xuất Excel báo cáo cấp trên"
      onClose={onClose}
      actions={
        <button
          type="button"
          className="btn-primary"
          disabled={busy || rows.length === 0}
          onClick={() => void onExport()}
        >
          {exporting ? "Đang xuất…" : "Xuất Excel"}
        </button>
      }
      inFrameScroll
      bodyClassName="fs-sheet-body-shell"
    >
      <div className="tk-cycle-list">
        {error && <p className="banner-warn">{error}</p>}
        {loading && rows.length === 0 ? (
          <p className="fs-sheet-loading">Đang tải danh sách chu kỳ…</p>
        ) : (
          <>
            <p className="field-hint">{rows.length} lượt đã tích.</p>
            <table className="tk-day-table">
              <thead>
                <tr>
                  <th>MSNV</th>
                  <th>Họ tên</th>
                  <th>Ngày về</th>
                  <th>Vào</th>
                  <th>Ra</th>
                  <th>Giờ công</th>
                  <th>Ghi chú</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="tk-cell-empty">
                      Chưa có NV tích chu kỳ trong kỳ này.
                    </td>
                  </tr>
                ) : (
                  rows.map((r) => (
                    <tr key={`${r.employee_code}-${r.work_date}`}>
                      <td>{r.employee_code}</td>
                      <td>{r.full_name}</td>
                      <td>{formatDateDDMMYYYY(r.work_date)}</td>
                      <td>{formatTimeHHMM(r.first_in, "—")}</td>
                      <td>{formatTimeHHMM(r.last_out, "—")}</td>
                      <td>{fmtHours(r.worked_hours)}</td>
                      <td>{r.note || "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </>
        )}
      </div>
    </FullScreenSheet>
  );
}
