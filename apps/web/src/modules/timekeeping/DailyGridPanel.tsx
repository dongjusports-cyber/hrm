import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type {
  CellEditingStoppedEvent,
  CellValueChangedEvent,
  ColDef,
  GridApi,
  IRowNode,
} from "ag-grid-community";
import {
  bulkPatchAttendanceDays,
  fetchAttendanceDaysGrid,
  patchAttendanceDayCell,
  type AttendanceDay,
  type AttendanceDayGridRow,
  type LeaveType,
} from "../../shared/api";
import { AG_GRID_DEFAULT_COL_DEF, AG_GRID_LOCALE_VI, compareHhmmEmptyFirst } from "../../shared/agGridVi";
import { createAgGridColumnPrefs } from "../../shared/agGridColumnPrefs";
import { TK_DAILY_GRID_COLS } from "./gridColumnKeys";
import { formatTimeHHMM } from "../../shared/formatDate";
import { formatLeaveLabel, leaveTypesForPicker } from "../../shared/formatLeave";
import { formatOrgName } from "../../shared/formatOrg";
import { formatOtHours } from "../../shared/formatOtHours";
import { TimeInput24 } from "../../shared/TimeInput24";
import { buildDayTimePatch, parseGridTimeInput, toIsoTime } from "./dailyGridTime";
import { employeeMatchesQuery } from "../../shared/employeeSearch";
import { applyDailyGridSort, isNeedsFirstSortActive } from "./dailyGridSort";
import { holidayOtMinutes, weekendOtMinutes } from "./otDisplay";

type RowWithEdit = AttendanceDayGridRow & {
  _edit_in?: string;
  _edit_out?: string;
  _disp_in?: string;
  _disp_out?: string;
};

function hhmm(iso: string | null | undefined): string {
  return formatTimeHHMM(iso, "");
}

function applyDayToGridRow(row: AttendanceDayGridRow, day: AttendanceDay): AttendanceDayGridRow {
  const late = day.late_minutes ?? 0;
  const early = day.early_minutes ?? 0;
  const punches = day.punch_count ?? 0;
  const leaveCode = (day as AttendanceDayGridRow).leave_code;
  let row_flag: AttendanceDayGridRow["row_flag"] = "ok";
  if (late > 0 && early > 0) row_flag = "both";
  else if (late > 0) row_flag = "late";
  else if (early > 0) row_flag = "early";
  else if ((Boolean(day.first_in) !== Boolean(day.last_out)) || (punches > 0 && punches % 2 === 1))
    row_flag = "odd";
  else if (day.is_workday && punches === 0 && !leaveCode) row_flag = "missing";
  const needs_action =
    late > 0 ||
    early > 0 ||
    Boolean(day.first_in) !== Boolean(day.last_out) ||
    (punches > 0 && punches % 2 === 1) ||
    Boolean(day.is_workday && punches === 0 && !leaveCode);
  const merged: RowWithEdit = {
    ...row,
    ...day,
    needs_action,
    row_flag,
  };
  delete merged._edit_in;
  delete merged._edit_out;
  merged._disp_in = hhmm(merged.first_in);
  merged._disp_out = hhmm(merged.last_out);
  return merged;
}

function withDisplayTimes(row: AttendanceDayGridRow): RowWithEdit {
  return {
    ...row,
    _disp_in: hhmm(row.first_in),
    _disp_out: hhmm(row.last_out),
  };
}

export type DailyGridSummary = {
  total: number;
  needsAction: number;
};

type Props = {
  workDate: string;
  periodLocked: boolean;
  leaves: LeaveType[];
  searchQuery?: string;
  departmentId?: string;
  /** Tăng sau đồng bộ / làm mới từ toolbar — ép tải lại lưới ngày. */
  refreshToken?: number;
  onSummaryChange?: (summary: DailyGridSummary) => void;
  onPickEmployee?: (row: AttendanceDayGridRow) => void;
  /** Sau sửa/xóa giờ — tab tổng hợp tháng lấy timesheet mới. */
  onTimesChanged?: () => void;
};

function DailyGridPanelInner({
  workDate,
  periodLocked,
  leaves,
  searchQuery = "",
  departmentId = "",
  refreshToken = 0,
  onSummaryChange,
  onPickEmployee,
  onTimesChanged,
}: Props) {
  const [rows, setRows] = useState<AttendanceDayGridRow[]>([]);
  const [needsOnly, setNeedsOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [gridApi, setGridApi] = useState<GridApi<AttendanceDayGridRow> | null>(null);
  const [needsFirstOn, setNeedsFirstOn] = useState(false);
  const didInitialSortRef = useRef(false);
  const rowsRef = useRef(rows);
  rowsRef.current = rows;
  const filterKeyRef = useRef(`${workDate}|${needsOnly}|${departmentId}`);
  const [bulkLeave, setBulkLeave] = useState("ALE");
  const [bulkIn, setBulkIn] = useState("08:00");
  const [bulkOut, setBulkOut] = useState("17:00");
  const [skipped, setSkipped] = useState<{ employee_code: string | null; reason: string }[]>([]);

  const pickerLeaves = useMemo(() => leaveTypesForPicker(leaves), [leaves]);
  const colPrefs = useMemo(() => createAgGridColumnPrefs(TK_DAILY_GRID_COLS), []);

  const load = useCallback(async () => {
    const nextFilter = `${workDate}|${needsOnly}|${departmentId}`;
    const filterChanged = filterKeyRef.current !== nextFilter;
    filterKeyRef.current = nextFilter;
    const isInitial = rowsRef.current.length === 0 || filterChanged;
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const list = await fetchAttendanceDaysGrid({
        date: workDate,
        needs_action_only: needsOnly,
        department_id: departmentId || undefined,
      });
      setRows(list.map(withDisplayTimes));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải lưới ngày công.");
    } finally {
      setLoading(false);
    }
  }, [workDate, needsOnly, departmentId, refreshToken]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const searchRef = useRef(searchQuery);
  searchRef.current = searchQuery;

  const isExternalFilterPresent = useCallback(() => searchRef.current.trim().length > 0, []);
  const doesExternalFilterPass = useCallback((node: IRowNode<AttendanceDayGridRow>) => {
    if (!node.data) return false;
    return employeeMatchesQuery(node.data, searchRef.current);
  }, []);

  useEffect(() => {
    gridApi?.onFilterChanged();
  }, [searchQuery, gridApi]);

  const initialLoading = loading && rows.length === 0;
  const refreshing = loading && rows.length > 0;

  const summary = useMemo((): DailyGridSummary => {
    const matched = rows.filter((r) => employeeMatchesQuery(r, searchQuery));
    return {
      total: matched.length,
      needsAction: matched.filter((r) => r.needs_action).length,
    };
  }, [rows, searchQuery]);

  useEffect(() => {
    if (!onSummaryChange) return;
    if (initialLoading) return;
    onSummaryChange(summary);
  }, [summary, onSummaryChange, initialLoading]);

  const cols = useMemo<ColDef<AttendanceDayGridRow>[]>(
    () => [
      {
        colId: "sel",
        headerName: "",
        width: 44,
        pinned: "left",
        checkboxSelection: true,
        headerCheckboxSelection: true,
        sortable: false,
        resizable: false,
        suppressHeaderMenuButton: true,
        editable: false,
        cellClass: "tk-grid-sel-cell",
        headerClass: "tk-grid-sel-header",
      },
      {
        colId: "needs_action",
        field: "needs_action",
        headerName: "Cần xử lý",
        hide: true,
        sortable: true,
        suppressColumnsToolPanel: true,
      },
      {
        field: "employee_code",
        headerName: "MSNV",
        width: 72,
        pinned: "left",
        editable: false,
      },
      {
        field: "full_name",
        headerName: "Họ tên",
        flex: 1,
        minWidth: 120,
        editable: false,
        cellClass: onPickEmployee ? "tk-cell-pick-name" : undefined,
      },
      {
        colId: "department_name",
        headerName: "Bộ phận",
        width: 108,
        editable: false,
        valueGetter: (p) =>
          formatOrgName(p.data?.department_name) ||
          formatOrgName(p.data?.department_code) ||
          "",
      },
      {
        colId: "team_name",
        headerName: "Tổ",
        width: 96,
        editable: false,
        valueGetter: (p) =>
          formatOrgName(p.data?.team_name) || formatOrgName(p.data?.team_code) || "",
      },
      {
        colId: "first_in",
        headerName: "Vào",
        width: 76,
        editable: !periodLocked,
        sort: "asc",
        sortIndex: 0,
        comparator: compareHhmmEmptyFirst,
        headerTooltip: "Bấm tiêu đề để xếp A→Z — ô trống (chưa chấm) lên đầu",
        cellClass: "tk-cell-time-center",
        headerClass: "tk-header-time-center",
        valueGetter: (p) => {
          const d = p.data as RowWithEdit | undefined;
          if (d?._edit_in != null) {
            const raw = String(d._edit_in).trim();
            if (raw === "") return "";
            return parseGridTimeInput(raw) ?? raw;
          }
          return d?._disp_in ?? hhmm(d?.first_in);
        },
        valueSetter: (p) => {
          if (!p.data) return false;
          (p.data as RowWithEdit)._edit_in = p.newValue;
          return true;
        },
        cellEditor: "agTextCellEditor",
      },
      {
        colId: "last_out",
        headerName: "Ra",
        width: 76,
        editable: !periodLocked,
        comparator: compareHhmmEmptyFirst,
        headerTooltip: "Bấm tiêu đề để xếp A→Z — ô trống (chưa chấm) lên đầu",
        cellClass: "tk-cell-time-center",
        headerClass: "tk-header-time-center",
        valueGetter: (p) => {
          const d = p.data as RowWithEdit | undefined;
          if (d?._edit_out != null) {
            const raw = String(d._edit_out).trim();
            if (raw === "") return "";
            return parseGridTimeInput(raw) ?? raw;
          }
          return d?._disp_out ?? hhmm(d?.last_out);
        },
        valueSetter: (p) => {
          if (!p.data) return false;
          (p.data as RowWithEdit)._edit_out = p.newValue;
          return true;
        },
        cellEditor: "agTextCellEditor",
      },
      {
        field: "worked_hours",
        headerName: "Công",
        width: 64,
        editable: false,
        valueFormatter: (p) =>
          p.value != null && Number(p.value) > 0 ? Number(p.value).toFixed(2) : "",
      },
      {
        field: "late_minutes",
        headerName: "Trễ",
        width: 52,
        editable: false,
        headerTooltip: "Đi trễ — bấm vào sau 08:00 (phút). Thai sản/nuôi con không đổi luật này.",
        valueFormatter: (p) => (Number(p.value) > 0 ? String(p.value) : ""),
      },
      {
        field: "early_minutes",
        headerName: "Sớm",
        width: 52,
        editable: false,
        headerTooltip: "Về sớm — bấm ra trước hết ca (phút). Thai sản/nuôi con về đúng giờ được phép thì 0.",
        valueFormatter: (p) => (Number(p.value) > 0 ? String(p.value) : ""),
      },
      {
        field: "ot_minutes",
        headerName: "Tăng ca sổ",
        width: 76,
        editable: false,
        headerTooltip: "OT trong — chỉ T3/T5, 17:00–20:00 (ra sau 17:30; vân tay 17:00–17:30 không tính).",
        valueGetter: (p) => p.data?.ot_on_books_minutes ?? 0,
        valueFormatter: (p) => formatOtHours(Number(p.value)),
      },
      {
        colId: "ot_external",
        headerName: "Tăng ca ngoài",
        width: 88,
        editable: false,
        headerTooltip: "OT ngoài (ATM) — T2/T4/T6/T7, sau 20:00 T3/T5, CN, lễ. Hệ số theo khung giờ (1,5/2,1 ngày thường · CN 2/3,5/4,1 · lễ 3/4,5/5,1). Không vào bảng lương chính.",
        valueGetter: (p) => p.data?.ot_external_minutes ?? 0,
        valueFormatter: (p) => formatOtHours(Number(p.value)),
      },
      {
        colId: "ot_weekend",
        headerName: "OT CN",
        width: 72,
        editable: false,
        headerTooltip: "OT Chủ nhật — thuộc OT ngoài (ATM). 8–17 ×2 · 17–22 và 6–8 ×3,5 · 22–6 ×4,1. Không cộng cột Công.",
        valueGetter: (p) => (p.data ? weekendOtMinutes(p.data) : 0),
        valueFormatter: (p) => formatOtHours(Number(p.value)),
      },
      {
        colId: "ot_holiday",
        headerName: "OT lễ",
        width: 64,
        editable: false,
        headerTooltip: "OT ngày lễ — thuộc OT ngoài (ATM). 8–17 ×3 · 17–22 và 6–8 ×4,5 · 22–6 ×5,1. Không cộng cột Công.",
        valueGetter: (p) => (p.data ? holidayOtMinutes(p.data) : 0),
        valueFormatter: (p) => formatOtHours(Number(p.value)),
      },
      {
        field: "leave_code",
        headerName: "Nghỉ",
        width: 120,
        editable: !periodLocked,
        valueFormatter: (p) => formatLeaveLabel(p.value as string | null, leaves),
      },
      {
        field: "note",
        headerName: "Ghi chú",
        flex: 0.8,
        minWidth: 100,
        editable: !periodLocked,
      },
    ],
    [periodLocked, onPickEmployee, leaves],
  );

  function sortNeedsFirst() {
    if (!gridApi) return;
    applyDailyGridSort(gridApi, "needs_first");
  }

  async function applyCellPatch(
    row: AttendanceDayGridRow,
    patchBody: Parameters<typeof patchAttendanceDayCell>[0],
  ) {
    const code = row.employee_code;
    const day = await patchAttendanceDayCell(patchBody);
    const merged = applyDayToGridRow(row, day);
    setRows((prev) => prev.map((r) => (r.employee_code === code ? merged : r)));
    gridApi?.applyTransaction({ update: [merged] });
    setToast(`Đã lưu ${code}`);
    onTimesChanged?.();
  }

  async function saveTimeCell(row: AttendanceDayGridRow, col: "first_in" | "last_out", editedRaw: string) {
    if (periodLocked) return;
    const typed = String(editedRaw ?? "").trim();
    const existing = col === "first_in" ? hhmm(row.first_in) : hhmm(row.last_out);
    if (!typed && !existing) return;
    const parsed = parseGridTimeInput(typed);
    if (typed && parsed && parsed === existing) return;
    const patch = buildDayTimePatch({
      workDate,
      col,
      editedRaw: typed,
      existingInHHmm: hhmm(row.first_in),
      existingOutHHmm: hhmm(row.last_out),
    });
    if (!patch.ok) {
      setError(patch.error);
      return;
    }
    try {
      setError(null);
      const body: Parameters<typeof patchAttendanceDayCell>[0] = {
        employee_code: row.employee_code,
        work_date: workDate,
      };
      if (patch.clear_times) {
        body.clear_times = true;
      } else {
        if (patch.clear_first_in) body.clear_first_in = true;
        if (patch.clear_last_out) body.clear_last_out = true;
        if (patch.first_in) body.first_in = patch.first_in;
        if (patch.last_out) body.last_out = patch.last_out;
      }
      await applyCellPatch(row, body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu ô thất bại.");
      await load();
    }
  }

  async function onCellChanged(e: CellValueChangedEvent<AttendanceDayGridRow>) {
    if (periodLocked || !e.data) return;
    const col = e.colDef.field ?? e.colDef.colId;
    if (col === "first_in" || col === "last_out") return;
    if (col !== "leave_code" && col !== "note") return;
    try {
      const patchBody: Parameters<typeof patchAttendanceDayCell>[0] = {
        employee_code: e.data.employee_code,
        work_date: workDate,
      };
      if (col === "leave_code") patchBody.leave_code = String(e.newValue ?? "");
      if (col === "note") patchBody.note = String(e.newValue ?? "");
      await applyCellPatch(e.data, patchBody);
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
    setToast(null);
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
      setToast(res.message);
      if (res.skipped.length) setSkipped(res.skipped);
      if (!preview) {
        await load();
        onTimesChanged?.();
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
          const fi = toIsoTime(workDate, parseGridTimeInput(inT) ?? inT);
          const lo = toIsoTime(workDate, parseGridTimeInput(outT) ?? outT);
          if (!fi || !lo) continue;
          await patchAttendanceDayCell({
            employee_code: code,
            work_date: workDate,
            first_in: fi,
            last_out: lo,
          });
        }
        setToast(`Đã dán ${lines.length} dòng (MSNV · Vào · Ra).`);
        await load();
        onTimesChanged?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Dán từ bảng tính thất bại.");
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
          Chỉ người cần xử lý
        </label>
        <button
          type="button"
          className={`btn-ghost-dark btn-sm${needsFirstOn ? " is-on" : ""}`}
          disabled={!gridApi}
          onClick={sortNeedsFirst}
        >
          {needsFirstOn ? "Đang xếp: cần xử lý" : "Xếp cần xử lý lên đầu"}
        </button>
        {periodLocked && <span className="form-error">Kỳ đã khóa — chỉ xem.</span>}
      </div>

      {!periodLocked && (
        <div className="tk-bulk-bar">
          <select value={bulkLeave} onChange={(e) => setBulkLeave(e.target.value)}>
            {pickerLeaves.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
          <button type="button" disabled={busy} onClick={() => void runBulk("set_leave", false)}>
            Gán nghỉ đã chọn
          </button>
          <TimeInput24 value={bulkIn} onChange={setBulkIn} aria-label="Giờ vào hàng loạt" />
          <TimeInput24 value={bulkOut} onChange={setBulkOut} aria-label="Giờ ra hàng loạt" />
          <button type="button" disabled={busy} onClick={() => void runBulk("set_times", false)}>
            Đặt giờ đã chọn
          </button>
          <button type="button" disabled={busy} onClick={() => void runBulk("clear_note", false)}>
            Xóa ghi chú
          </button>
        </div>
      )}

      {error && <p className="form-error">{error}</p>}
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
        className="ag-theme-quartz tk-daily-grid-wrap"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "F2" && gridApi) {
            const focused = gridApi.getFocusedCell();
            if (focused) gridApi.startEditingCell({ rowIndex: focused.rowIndex, colKey: focused.column });
          }
        }}
      >
        <AgGridReact
          rowData={rows}
          columnDefs={cols}
          getRowId={(p) => p.data.employee_code}
          localeText={AG_GRID_LOCALE_VI}
          headerHeight={32}
          rowHeight={36}
          animateRows={false}
          rowSelection="multiple"
          suppressRowClickSelection
          singleClickEdit
          stopEditingWhenCellsLoseFocus
          isExternalFilterPresent={isExternalFilterPresent}
          doesExternalFilterPass={doesExternalFilterPass}
          onGridReady={(p) => {
            setGridApi(p.api);
            const restored = colPrefs.restore(p.api);
            if (!restored && !didInitialSortRef.current) {
              applyDailyGridSort(p.api, "default");
            }
            didInitialSortRef.current = true;
            setNeedsFirstOn(isNeedsFirstSortActive(p.api.getColumnState()));
            p.api.onFilterChanged();
          }}
          onSortChanged={(p) => {
            setNeedsFirstOn(isNeedsFirstSortActive(p.api.getColumnState()));
          }}
          {...colPrefs.handlers}
          onCellDoubleClicked={(e) => {
            if (e.colDef.field === "full_name" && e.data && onPickEmployee) {
              onPickEmployee(e.data);
            }
          }}
          onCellValueChanged={(e) => void onCellChanged(e)}
          onCellEditingStopped={(e: CellEditingStoppedEvent<AttendanceDayGridRow>) => {
            const col = e.colDef.colId;
            if (col !== "first_in" && col !== "last_out") return;
            if (!e.data) return;
            if (e.valueChanged === false) return;
            const pending =
              col === "first_in"
                ? (e.data as RowWithEdit)._edit_in
                : (e.data as RowWithEdit)._edit_out;
            const typed = String(pending ?? e.newValue ?? "").trim();
            void saveTimeCell(e.data, col, typed);
          }}
          getRowClass={(p) => {
            const f = p.data?.row_flag;
            if (f && f !== "ok" && f !== "off") return `tk-grid-flag-${f}`;
            return undefined;
          }}
          defaultColDef={{
            ...AG_GRID_DEFAULT_COL_DEF,
            sortable: true,
            resizable: true,
            filter: false,
            suppressHeaderMenuButton: false,
          }}
        />
        {(initialLoading || refreshing) && (
          <div className="tk-daily-refresh-overlay" aria-hidden="true">
            <span className="field-hint">{initialLoading ? "Đang tải…" : "Đang cập nhật…"}</span>
          </div>
        )}
        {toast && (
          <div className="tk-daily-toast-host" role="status" aria-live="polite">
            <p className="form-ok fs-sheet-banner">{toast}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export const DailyGridPanel = memo(DailyGridPanelInner);
DailyGridPanel.displayName = "DailyGridPanel";
