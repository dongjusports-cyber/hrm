import { useCallback, useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import {
  bulkDecideLeaveRequests,
  fetchLeaveRequests,
  type LeaveRequestRow,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { formatDeptTeam } from "../../shared/formatOrg";

export function LeaveApprovalPanel() {
  const [rows, setRows] = useState<LeaveRequestRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [skipped, setSkipped] = useState<{ employee_code: string | null; reason: string }[]>([]);
  const [gridApi, setGridApi] = useState<{ getSelectedRows: () => LeaveRequestRow[] } | null>(
    null,
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchLeaveRequests({ status: "submitted" });
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải hàng đợi duyệt phép.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const cols = useMemo<ColDef<LeaveRequestRow>[]>(
    () => [
      {
        field: "employee_code",
        headerName: "MSNV",
        width: 90,
        checkboxSelection: true,
        headerCheckboxSelection: true,
        pinned: "left",
      },
      { field: "full_name", headerName: "Họ tên", flex: 1, minWidth: 130 },
      {
        colId: "dept_team",
        headerName: "Tổ",
        width: 140,
        cellClass: "hr-cell-org",
        valueGetter: (p) =>
          formatDeptTeam(
            p.data?.department_name,
            p.data?.department_code,
            p.data?.team_name,
            p.data?.team_code,
          ) || "—",
      },
      { field: "leave_type_name", headerName: "Loại nghỉ", width: 120 },
      {
        colId: "range",
        headerName: "Từ – đến",
        width: 150,
        valueGetter: (p) =>
          p.data ? `${formatDateDDMMYYYY(p.data.from_date)} → ${formatDateDDMMYYYY(p.data.to_date)}` : "",
      },
      {
        field: "total_days",
        headerName: "Số ngày",
        width: 80,
        valueFormatter: (p) => String(p.value ?? ""),
      },
      {
        field: "annual_leave_remaining",
        headerName: "Phép còn",
        width: 90,
        valueFormatter: (p) =>
          p.data?.leave_type_code === "ALE" && p.value != null ? String(p.value) : "—",
      },
      { field: "reason", headerName: "Lý do", flex: 1, minWidth: 120 },
    ],
    [],
  );

  async function decide(action: "approve" | "reject") {
    const selected = gridApi?.getSelectedRows() ?? [];
    if (selected.length === 0) {
      setError("Chọn ít nhất một đơn trong lưới.");
      return;
    }
    const label = action === "approve" ? "duyệt" : "từ chối";
    if (!window.confirm(`Xác nhận ${label} ${selected.length} đơn nghỉ?`)) return;
    setBusy(true);
    setError(null);
    setOk(null);
    setSkipped([]);
    try {
      const res = await bulkDecideLeaveRequests({
        request_ids: selected.map((r) => r.id),
        action,
        decided_note: note.trim(),
      });
      setOk(res.message);
      if (res.skipped.length) setSkipped(res.skipped);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Duyệt thất bại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="tk-leave-queue">
      <p className="field-hint">
        Hàng đợi đơn chờ duyệt — chọn nhiều dòng rồi Duyệt / Từ chối một lần. Đơn ALE vượt số dư
        phép sẽ bị loại khỏi lô và báo rõ.
      </p>
      <label className="field">
        <span>Ghi chú chung (tùy chọn)</span>
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Lý do duyệt / từ chối" />
      </label>
      <div className="tk-leave-actions">
        <button type="button" className="btn-primary" disabled={busy} onClick={() => void decide("approve")}>
          Duyệt đã chọn
        </button>
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => void decide("reject")}>
          Từ chối đã chọn
        </button>
        <button type="button" className="btn-secondary" disabled={loading} onClick={() => void load()}>
          Tải lại
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
      {ok && <p className="form-ok">{ok}</p>}
      {skipped.length > 0 && (
        <ul className="tk-skipped-list">
          {skipped.map((s, i) => (
            <li key={i}>
              {s.employee_code ?? "?"}: {s.reason}
            </li>
          ))}
        </ul>
      )}
      <div className="ag-theme-quartz hr-grid-wrap" style={{ height: 360, marginTop: "0.75rem" }}>
        {loading ? (
          <p className="field-hint">Đang tải…</p>
        ) : rows.length === 0 ? (
          <p className="field-hint">Không có đơn chờ duyệt.</p>
        ) : (
          <AgGridReact
            rowData={rows}
            columnDefs={cols}
            rowSelection="multiple"
            suppressRowClickSelection
            onGridReady={(e) => setGridApi(e.api)}
            defaultColDef={{ sortable: true, resizable: true, filter: false }}
            animateRows={false}
          />
        )}
      </div>
    </div>
  );
}
