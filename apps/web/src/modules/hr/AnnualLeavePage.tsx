import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from "ag-grid-community";
import {
  fetchAnnualLeaveGrid,
  type AnnualLeaveGrid,
  type AnnualLeaveGridRow,
  type AnnualLeaveMonthDays,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";
import { EmployeeProfileSheet } from "./EmployeeProfileSheet";

const MONTHS: { key: keyof AnnualLeaveMonthDays; label: string }[] = [
  { key: "jan", label: "T1" },
  { key: "feb", label: "T2" },
  { key: "mar", label: "T3" },
  { key: "apr", label: "T4" },
  { key: "may", label: "T5" },
  { key: "jun", label: "T6" },
  { key: "jul", label: "T7" },
  { key: "aug", label: "T8" },
  { key: "sep", label: "T9" },
  { key: "oct", label: "T10" },
  { key: "nov", label: "T11" },
  { key: "dec", label: "T12" },
];

function formatDays(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  if (n === 0) return "";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatDaysKeepZero(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("vi-VN", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

/** Nhân Sự → Phép năm — lưới GenuSuite (bản trích Excel, chỉ đọc). */
export function AnnualLeavePage() {
  useHrSubpageEsc({ backTo: "/m/hr" });
  const [grid, setGrid] = useState<AnnualLeaveGrid | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("");
  const [profileEmpId, setProfileEmpId] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const gridApiRef = useRef<GridApi<AnnualLeaveGridRow> | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchAnnualLeaveGrid()
      .then((data) => {
        if (!cancelled) setGrid(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Không tải được lưới phép năm.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const rows = grid?.employees ?? [];
  const departments = useMemo(() => {
    const set = new Set(rows.map((r) => r.department).filter(Boolean));
    return [...set].sort((a, b) => a.localeCompare(b, "vi"));
  }, [rows]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rows.filter((r) => {
      if (dept && r.department !== dept) return false;
      if (!needle) return true;
      return (
        r.employee_code.toLowerCase().includes(needle) ||
        r.full_name.toLowerCase().includes(needle) ||
        r.department.toLowerCase().includes(needle) ||
        r.team.toLowerCase().includes(needle)
      );
    });
  }, [rows, q, dept]);

  const openProfile = useCallback((row: AnnualLeaveGridRow) => {
    if (row.employee_id) {
      setHint(null);
      setProfileEmpId(row.employee_id);
      return;
    }
    setHint(`MSNV ${row.employee_code} chưa có trên máy này — chỉ xem số phép GenuSuite.`);
  }, []);

  const columnDefs = useMemo<ColDef<AnnualLeaveGridRow>[]>(() => {
    const base: ColDef<AnnualLeaveGridRow>[] = [
      {
        field: "employee_code",
        headerName: "MSNV",
        width: 78,
        minWidth: 70,
        pinned: "left",
        cellClass: "hr-cell-open-profile",
      },
      {
        field: "full_name",
        headerName: "Họ tên",
        minWidth: 168,
        width: 200,
        pinned: "left",
        cellClass: "hr-cell-name-link",
      },
      {
        field: "department",
        headerName: "Bộ phận",
        width: 120,
        minWidth: 96,
      },
      {
        field: "team",
        headerName: "Tổ",
        width: 120,
        minWidth: 96,
      },
      {
        field: "join_date",
        headerName: "Ngày vào",
        width: 108,
        minWidth: 108,
        valueFormatter: (p) => formatDateDDMMYYYY(p.value),
      },
      {
        field: "al_days",
        headerName: "Được hưởng",
        headerTooltip: "NV mới 14 ngày/năm; +1 mỗi đủ 5 năm theo ngày vào",
        width: 108,
        minWidth: 96,
        type: "numericColumn",
        valueFormatter: (p) => formatDaysKeepZero(p.value),
      },
      {
        field: "curr_al",
        headerName: "Hiện tại",
        headerTooltip: "Phép đã tích = mốc × tháng đã đóng / 12",
        width: 92,
        minWidth: 84,
        type: "numericColumn",
        valueFormatter: (p) => formatDaysKeepZero(p.value),
      },
      {
        field: "used",
        headerName: "Đã dùng",
        width: 92,
        minWidth: 80,
        type: "numericColumn",
        valueFormatter: (p) => formatDaysKeepZero(p.value),
      },
      {
        field: "curr_remaining",
        headerName: "Còn lại",
        headerTooltip: "Hiện tại − đã dùng",
        width: 92,
        minWidth: 80,
        type: "numericColumn",
        valueFormatter: (p) => formatDaysKeepZero(p.value),
      },
    ];
    for (const m of MONTHS) {
      base.push({
        colId: m.key,
        headerName: m.label,
        width: 52,
        minWidth: 48,
        type: "numericColumn",
        valueGetter: (p) => p.data?.used_by_month?.[m.key] ?? "0",
        valueFormatter: (p) => formatDays(p.value),
      });
    }
    return base;
  }, []);

  function onCellClicked(e: CellClickedEvent<AnnualLeaveGridRow>) {
    const colId = e.column.getColId();
    if ((colId === "full_name" || colId === "employee_code") && e.data) {
      openProfile(e.data);
    }
  }

  return (
    <div className="hr-page">
      <div className="users-head hr-list-head">
        <div className="hr-list-title-row">
          <h1>Phép năm</h1>
          <span className="field-hint">
            {filtered.length} NV · <Link to="/m/hr">← Nhân Sự</Link>
          </span>
        </div>
        <p className="field-hint">
          {grid?.source_label ?? "Đang tải…"}
          {grid && !grid.missing
            ? ` — NV mới được hưởng 14 ngày/năm, +1 mỗi đủ 5 năm (đúng ngày vào). Hiện tại = mốc × tháng đã đóng / 12. Còn lại = hiện tại − đã dùng. Bấm tên để mở hồ sơ.`
            : ""}
        </p>
      </div>

      {error && <p className="banner-warn">{error}</p>}
      {grid?.missing && (
        <p className="banner-warn">
          Chưa có file trích phép năm. Trên máy .123 chạy{" "}
          <code>python -m app.scripts.extract_annual_leave</code> trong <code>apps/api</code>.
        </p>
      )}
      {hint && <p className="field-hint">{hint}</p>}

      <div className="hr-toolbar">
        <input
          className="hr-toolbar-search"
          data-hotkey-search
          placeholder="Tìm MSNV / họ tên / bộ phận…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="hr-toolbar-select"
          value={dept}
          onChange={(e) => setDept(e.target.value)}
          aria-label="Bộ phận"
        >
          <option value="">Tất cả bộ phận</option>
          {departments.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn-ghost-dark btn-compact"
          onClick={() => {
            setQ("");
            setDept("");
          }}
        >
          Đặt lại lọc
        </button>
      </div>

      <div className="ag-theme-quartz hr-grid hr-grid-list">
        <AgGridReact<AnnualLeaveGridRow>
          rowData={filtered}
          columnDefs={columnDefs}
          getRowId={(p) => p.data.employee_code}
          rowHeight={32}
          animateRows={false}
          overlayNoRowsTemplate="<span>Không có dòng phép năm</span>"
          onCellClicked={onCellClicked}
          onGridReady={(e: GridReadyEvent<AnnualLeaveGridRow>) => {
            gridApiRef.current = e.api;
          }}
          defaultColDef={{
            sortable: true,
            resizable: true,
            filter: false,
            suppressHeaderMenuButton: true,
            flex: 0,
          }}
        />
      </div>

      <EmployeeProfileSheet
        employeeId={profileEmpId ?? ""}
        open={profileEmpId !== null}
        onClose={() => setProfileEmpId(null)}
      />
    </div>
  );
}
