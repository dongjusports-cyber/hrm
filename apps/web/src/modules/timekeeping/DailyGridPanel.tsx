import { useCallback, useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { CellValueChangedEvent, ColDef, GridApi } from "ag-grid-community";
import {
  bulkPatchAttendanceDays,
  fetchAttendanceDaysGrid,
  patchAttendanceDayCell,
  type AttendanceDayGridRow,
  type LeaveType,
} from "../../shared/api";

function hhmm(iso: string | null | undefined): string {
  if (!iso) return "";
  const m = iso.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : "";
}

function toIsoTime(workDate: string, hhmmVal: string): string | null {
  if (!hhmmVal || !/^\d{2}:\d{2}$/.test(hhmmVal)) return null;
  return `${workDate}T${hhmmVal}:00+07:00`;
}

type Props = {
  workDate: string;
  periodLocked: boolean;
  leaves: LeaveType[];
  onChanged?: () => void;
};

export function DailyGridPanel({ workDate, periodLocked, leaves, onChanged }: Props) {
  const [rows, setRows] = useState<AttendanceDayGridRow[]>([]);
  const [needsOnly, setNeedsOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [gridApi, setGridApi] = useState<GridApi<AttendanceDayGridRow> | null>(null);
  const [bulkLeave, setBulkLeave] = useState("ALE");
  const [bulkIn, setBulkIn] = useState("08:00");
  const [bulkOut, setBulkOut] = useState("17:00");
  const [skipped, setSkipped] = useState<{ employee_code: string | null; reason: string }[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchAttendanceDaysGrid({
        date: workDate,
        needs_action_only: needsOnly,
      });
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải lưới ngày công.");
    } finally {
      setLoading(false);
    }
  }, [workDate, needsOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  const cols = useMemo<ColDef<AttendanceDayGridRow>[]>(
    () => [
      {
        field: "employee_code",
        headerName: "MSNV",
        width: 82,
        pinned: "left",
        checkboxSelection: true,
        headerCheckboxSelection: true,
        editable: false,
      },
      { field: "full_name", headerName: "Họ tên", flex: 1, minWidth: 120, editable: false },
      {
        field: "team_code",
        headerName: "Tổ",
        width: 72,
        editable: false,
        valueFormatter: (p) => p.value ?? "—",
      },
      {
        field: "work_shift_id",
        headerName: "Ca",
        width: 64,
        editable: false,
        valueFormatter: (p) => p.value ?? "—",
      },
      {
        colId: "first_in",
        headerName: "Vào",
        width: 72,
        editable: !periodLocked,
        valueGetter: (p) => hhmm(p.data?.first_in),
        valueSetter: (p) => {
          if (!p.data) return false;
          (p.data as AttendanceDayGridRow & { _edit_in?: string })._edit_in = p.newValue;
          return true;
        },
      },
      {
        colId: "last_out",
        headerName: "Ra",
        width: 72,
        editable: !periodLocked,
        valueGetter: (p) => hhmm(p.data?.last_out),
        valueSetter: (p) => {
          if (!p.data) return false;
          (p.data as AttendanceDayGridRow & { _edit_out?: string })._edit_out = p.newValue;
          return true;
        },
      },
      {
        field: "worked_hours",
        headerName: "Công",
        width: 64,
        editable: false,
        valueFormatter: (p) => (p.value != null ? Number(p.value).toFixed(2) : "—"),
      },
      {
        field: "ot_minutes",
        headerName: "OT′",
        width: 56,
        editable: false,
      },
      {
        field: "holiday_hours",
        headerName: "Lễ",
        width: 52,
        editable: false,
        valueFormatter: (p) => (Number(p.value) > 0 ? String(p.value) : "—"),
      },
      {
        field: "leave_code",
        headerName: "Mã nghỉ",
        width: 80,
        editable: !periodLocked,
      },
      {
        field: "note",
        headerName: "Ghi chú",
        flex: 0.8,
        minWidth: 100,
        editable: !periodLocked,
      },
    ],
    [periodLocked],
  );

  async function onCellChanged(e: CellValueChangedEvent<AttendanceDayGridRow>) {
    if (periodLocked || !e.data) return;
    const code = e.data.employee_code;
    const col = e.colDef.field ?? e.colDef.colId;
    try {
      if (col === "leave_code" || col === "note") {
        await patchAttendanceDayCell({
          employee_code: code,
          work_date: workDate,
          leave_code: col === "leave_code" ? String(e.newValue ?? "") : undefined,
          note: col === "note" ? String(e.newValue ?? "") : undefined,
        });
      } else if (col === "first_in" || col === "last_out") {
        const row = e.data;
        const inT = toIsoTime(workDate, hhmm(row.first_in) || String(e.newValue ?? ""));
        const outT = toIsoTime(workDate, hhmm(row.last_out) || String(e.newValue ?? ""));
        if (col === "first_in" && e.newValue) {
          const fi = toIsoTime(workDate, String(e.newValue));
          const lo = toIsoTime(workDate, hhmm(row.last_out));
          if (fi && lo) {
            await patchAttendanceDayCell({
              employee_code: code,
              work_date: workDate,
              first_in: fi,
              last_out: lo,
            });
          }
        } else if (col === "last_out" && e.newValue) {
          const fi = toIsoTime(workDate, hhmm(row.first_in));
          const lo = toIsoTime(workDate, String(e.newValue));
          if (fi && lo) {
            await patchAttendanceDayCell({
              employee_code: code,
              work_date: workDate,
              first_in: fi,
              last_out: lo,
            });
          }
        }
      }
      setOk(`Đã lưu ${code}`);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu ô thất bại.");
      await load();
    }
  }

  function selectedCodes(): string[] {
    return (gridApi?.getSelectedRows() ?? []).map((r) => r.employee_code);
  }

  async function runBulk(action: "set_leave" | "set_times" | "clear_note", preview: boolean) {
    const codes = selectedCodes();
    if (!codes.length) {
      setError("Chọn ít nhất một dòng.");
      return;
    }
    setBusy(true);
    setError(null);
    setOk(null);
    setSkipped([]);
    try {
      const body: Parameters<typeof bulkPatchAttendanceDays>[0] = {
        work_date: workDate,
        employee_codes: codes,
        action,
        preview,
      };
      if (action === "set_leave") body.leave_code = bulkLeave;
      if (action === "set_times") {
        body.first_in_time = bulkIn;
        body.last_out_time = bulkOut;
      }
      const res = await bulkPatchAttendanceDays(body);
      setOk(res.message);
      if (res.skipped.length) setSkipped(res.skipped);
      if (!preview) {
        await load();
        onChanged?.();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Thao tác hàng loạt thất bại.");
    } finally {
      setBusy(false);
    }
  }

  function onPaste(e: React.ClipboardEvent) {
    if (periodLocked) return;
    const text = e.clipboardData.getData("text/plain");
    if (!text.includes("\t") && !text.includes("\n")) return;
    e.preventDefault();
    void (async () => {
      const lines = text
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean);
      setBusy(true);
      setError(null);
      try {
        for (const line of lines) {
          const parts = line.split("\t");
          const code = parts[0]?.trim();
          const inT = parts[1]?.trim();
          const outT = parts[2]?.trim();
          if (!code || !inT || !outT) continue;
          const fi = toIsoTime(workDate, inT.length === 5 ? inT : inT.slice(0, 5));
          const lo = toIsoTime(workDate, outT.length === 5 ? outT : outT.slice(0, 5));
          if (!fi || !lo) continue;
          await patchAttendanceDayCell({
            employee_code: code,
            work_date: workDate,
            first_in: fi,
            last_out: lo,
          });
        }
        setOk(`Đã dán ${lines.length} dòng (MSNV · Vào · Ra).`);
        await load();
        onChanged?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Dán Excel thất bại.");
      } finally {
        setBusy(false);
      }
    })();
  }

  return (
    <div className="tk-daily-grid" onPaste={onPaste}>
      <div className="tk-daily-toolbar">
        <label className="tk-chip-toggle">
          <input
            type="checkbox"
            checked={needsOnly}
            onChange={(e) => setNeedsOnly(e.target.checked)}
          />
          Chỉ hiện cần xử lý
        </label>
        <span className="field-hint">
          F2 / Enter sửa ô · Dán khối Excel: MSNV [tab] Vào [tab] Ra
        </span>
        {periodLocked && <span className="form-error">Kỳ đã khóa — chỉ xem.</span>}
      </div>

      {!periodLocked && (
        <div className="tk-bulk-bar">
          <select value={bulkLeave} onChange={(e) => setBulkLeave(e.target.value)}>
            {leaves.map((l) => (
              <option key={l.code} value={l.code}>
                {l.code}
              </option>
            ))}
          </select>
          <button type="button" disabled={busy} onClick={() => void runBulk("set_leave", true)}>
            Xem trước gán nghỉ
          </button>
          <button type="button" disabled={busy} onClick={() => void runBulk("set_leave", false)}>
            Gán nghỉ
          </button>
          <input type="time" value={bulkIn} onChange={(e) => setBulkIn(e.target.value)} />
          <input type="time" value={bulkOut} onChange={(e) => setBulkOut(e.target.value)} />
          <button type="button" disabled={busy} onClick={() => void runBulk("set_times", false)}>
            Đặt giờ Vào/Ra
          </button>
          <button type="button" disabled={busy} onClick={() => void runBulk("clear_note", false)}>
            Xóa ghi chú
          </button>
        </div>
      )}

      {error && <p className="form-error">{error}</p>}
      {ok && <p className="form-ok">{ok}</p>}
      {skipped.length > 0 && (
        <ul className="tk-skipped-list">
          {skipped.map((s, i) => (
            <li key={i}>
              {s.employee_code}: {s.reason}
            </li>
          ))}
        </ul>
      )}

      <div
        className="ag-theme-quartz hr-grid-wrap"
        style={{ height: 420, marginTop: "0.5rem" }}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "F2" && gridApi) {
            const focused = gridApi.getFocusedCell();
            if (focused) gridApi.startEditingCell({ rowIndex: focused.rowIndex, colKey: focused.column });
          }
        }}
      >
        {loading ? (
          <p className="field-hint">Đang tải…</p>
        ) : (
          <AgGridReact
            rowData={rows}
            columnDefs={cols}
            rowSelection="multiple"
            suppressRowClickSelection
            onGridReady={(p) => setGridApi(p.api)}
            onCellValueChanged={(e) => void onCellChanged(e)}
            getRowClass={(p) => {
              const f = p.data?.row_flag;
              if (f && f !== "ok" && f !== "off") return `tk-grid-flag-${f}`;
              return undefined;
            }}
            defaultColDef={{ sortable: true, resizable: true, filter: false }}
          />
        )}
      </div>
    </div>
  );
}
