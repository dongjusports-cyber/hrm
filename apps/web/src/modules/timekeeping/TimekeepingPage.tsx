import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, GridApi, IRowNode, RowClickedEvent } from "ag-grid-community";
import {
  fetchAttendanceDays,
  fetchDepartments,
  fetchIntegrationStatus,
  fetchLeaveRequests,
  fetchLeaveTypes,
  fetchPayPeriod,
  fetchTimesheets,
  patchAttendanceDayCell,
  patchAttendanceDayCycle,
  patchAttendanceDayManual,
  rebuildTimesheets,
  type AttendanceDay,
  type AttendanceDayGridRow,
  type Department,
  type IntegrationStatus,
  type LeaveType,
  type PayPeriod,
  type TimesheetMonth,
} from "../../shared/api";
import { formatDepartmentLabel, sortByViName } from "../../shared/formatOrg";
import { AG_GRID_DEFAULT_COL_DEF, AG_GRID_LOCALE_VI } from "../../shared/agGridVi";
import { createAgGridColumnPrefs } from "../../shared/agGridColumnPrefs";
import { formatDateDDMMYYYY, formatTimeHHMM, currentPayPeriod, payPeriodStartDate, payPeriodDateBounds, todayIsoDateVN } from "../../shared/formatDate";
import { FullScreenSheet } from "../../shared/FullScreenSheet";
import { useSheetKeyboard } from "../../shared/formFieldEsc";
import { useEscLayer } from "../../shared/useEscLayer";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";
import { ModuleLayerHeader } from "../../shared/ModuleLayerHeader";
import { formatOtHours } from "../../shared/formatOtHours";
import { holidayOtMinutes, weekendOtMinutes } from "./otDisplay";
import { labelJobStatus, labelPeriodStatus } from "../../shared/viLabels";
import { CycleLeaveListSheet } from "./CycleLeaveListSheet";
import { DailyGridPanel, type DailyGridSummary } from "./DailyGridPanel";
import { employeeMatchesQuery, findEmployeeByQuery } from "../../shared/employeeSearch";
import { ToolbarSearchInput } from "../../shared/ToolbarSearchInput";
import { TimeInput24 } from "../../shared/TimeInput24";
import {
  formatWorkedHours,
  outTimeAfterWorkedHours,
  parseGridTimeInput,
  parseWorkedHoursInput,
  previewShiftWorkedHours,
  toIsoTime,
} from "./dailyGridTime";
import { LeaveApprovalPanel } from "./LeaveApprovalPanel";
import { MitaproSyncPanel } from "./MitaproSyncPanel";
import { OtExternalPreviewSheet } from "./OtExternalPreviewSheet";
import { runSyncWithProgress, type SyncProgressState } from "./syncWithProgress";
import { TK_MONTHLY_GRID_COLS } from "./gridColumnKeys";
import { ToolbarMoreMenu } from "../../shared/ToolbarMoreMenu";
import { disabledTitle } from "../../shared/disabledHint";
import { cacheInvalidate } from "../../shared/clientCache";

type MainView = "daily" | "monthly" | "leave";

const MAIN_VIEW_HINT: Record<MainView, string> = {
  daily: "Kiểm công một ngày: Công · trễ/sớm · tăng ca sổ/ngoài · OT CN/lễ. CN đi làm hiện OT CN, không cộng Công.",
  monthly: "Tổng hợp tháng — một dòng một NV. Cột Công = giờ/8. OT trong (T3/T5) tách khỏi OT ngoài (CN/lễ/ngày khác).",
  leave: "Đơn phép công nhân gửi từ điện thoại — chọn dòng rồi Duyệt / Từ chối.",
};

const TK_HEADER_TIPS = {
  al: "Nghỉ phép năm",
  rem: "Nghỉ theo mã REM",
  otBooks: "OT trong — chỉ T3/T5, 17:00–20:00 (ra sau 17:30; vân tay 17:00–17:30 không tính). Cột AC/AD bảng lương.",
  otExt: "OT ngoài (ATM) — T2/T4/T6/T7, sau 20:00 T3/T5, CN, lễ. Hệ số theo khung giờ, không vào bảng lương chính.",
  otWeekend: "OT Chủ nhật — thuộc OT ngoài (ATM). 8–17 ×2 · 17–22 và 6–8 ×3,5 · 22–6 ×4,1. Không cộng cột Công.",
  otHoliday: "OT ngày lễ — thuộc OT ngoài (ATM). 8–17 ×3 · 17–22 và 6–8 ×4,5 · 22–6 ×5,1. Không cộng cột Công.",
} as const;

type CalendarRow = {
  work_date: string;
  weekday: string;
  day?: AttendanceDay;
  hasData: boolean;
  late: number;
  early: number;
  ot: number;
  otOnBooks: number;
  otExternal: number;
  otWeekend: number;
  otHoliday: number;
  punches: number;
  firstIn: string;
  lastOut: string;
  hours: string;
  cycleLeave: boolean;
  flag: "ok" | "late" | "early" | "both" | "empty" | "off" | "odd" | "missing";
  oddPunch: boolean;
  missingPunch: boolean;
};

function isOddPunchDay(day: AttendanceDay | undefined, punches: number): boolean {
  if (!day) return false;
  if (punches === 1) return true;
  if (punches > 0 && (!day.first_in || !day.last_out)) return true;
  return false;
}

/** Ô trống — HR/AI nhận biết thiếu dữ liệu (không dùng dấu —). */
function cellTime(iso: string | null | undefined): string {
  return formatTimeHHMM(iso, "");
}

function cellMinutes(n: number): string {
  return n > 0 ? String(n) : "";
}

const WEEKDAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

function defaultPeriod(): string {
  return currentPayPeriod();
}

function parseYmd(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatYmd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function eachDate(from: string, to: string): string[] {
  const out: string[] = [];
  const cur = parseYmd(from);
  const end = parseYmd(to);
  while (cur <= end) {
    out.push(formatYmd(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return out;
}

function fmtNum(v: unknown, digits = 2): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toFixed(digits).replace(/\.?0+$/, "");
}

function buildCalendar(
  dateFrom: string,
  dateTo: string,
  days: AttendanceDay[],
): CalendarRow[] {
  const byDate = new Map(days.map((d) => [d.work_date, d]));
  return eachDate(dateFrom, dateTo).map((work_date) => {
    const day = byDate.get(work_date);
    const wd = WEEKDAYS[parseYmd(work_date).getDay()] ?? "";
    const late = day?.late_minutes ?? 0;
    const early = day?.early_minutes ?? 0;
    const punches = day?.punch_count ?? 0;
    const oddPunch = isOddPunchDay(day, punches);
    const hasComplete = Boolean(day?.first_in && day?.last_out);
    const hasPartial = Boolean(day?.first_in || day?.last_out);
    const isOff = day ? !day.is_workday : wd === "CN";
    const isWorkday = !isOff;
    const missingPunch = isWorkday && !hasComplete && !hasPartial;
    const hasData = hasComplete;
    let flag: CalendarRow["flag"] = "empty";
    if (oddPunch) flag = "odd";
    else if (missingPunch) flag = "missing";
    else if (hasComplete) {
      if (late > 0 && early > 0) flag = "both";
      else if (late > 0) flag = "late";
      else if (early > 0) flag = "early";
      else flag = "ok";
    } else if (isOff) {
      flag = "off";
    }
    return {
      work_date,
      weekday: wd,
      day,
      hasData,
      late: missingPunch ? 0 : late,
      early: missingPunch ? 0 : early,
      ot: missingPunch ? 0 : (day?.ot_minutes ?? 0),
      otOnBooks: missingPunch ? 0 : (day?.ot_on_books_minutes ?? 0),
      otExternal: missingPunch ? 0 : (day?.ot_external_minutes ?? 0),
      otWeekend: missingPunch ? 0 : weekendOtMinutes(day ?? {}),
      otHoliday: missingPunch ? 0 : holidayOtMinutes(day ?? {}),
      punches,
      firstIn: cellTime(day?.first_in),
      lastOut: cellTime(day?.last_out),
      hours:
        hasComplete && day?.worked_hours != null ? String(day.worked_hours) : "",
      cycleLeave: Boolean(day?.cycle_leave),
      flag,
      oddPunch,
      missingPunch,
    };
  });
}

export function TimekeepingPage() {
  const [period, setPeriod] = useState(defaultPeriod);
  const [q, setQ] = useState("");
  const typedQRef = useRef("");
  const [searchReset, setSearchReset] = useState(0);
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [pay, setPay] = useState<PayPeriod | null>(null);
  const [rows, setRows] = useState<TimesheetMonth[]>([]);
  const [leaves, setLeaves] = useState<LeaveType[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentId, setDepartmentId] = useState("");
  const [selected, setSelected] = useState<TimesheetMonth | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [empDays, setEmpDays] = useState<AttendanceDay[]>([]);
  const [daysLoading, setDaysLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [fixEmp, setFixEmp] = useState("");
  const [fixDate, setFixDate] = useState(`${defaultPeriod()}-01`);
  const [fixIn, setFixIn] = useState("08:00");
  const [fixOut, setFixOut] = useState("17:00");
  const [fixHours, setFixHours] = useState("8");
  const hoursFocusedRef = useRef(false);
  const [fixNote, setFixNote] = useState("Sửa tay thiếu chấm");
  const [fixCycle, setFixCycle] = useState(false);
  const [gridDate, setGridDate] = useState(() => {
    const p = defaultPeriod();
    const today = todayIsoDateVN();
    return today.slice(0, 7) === p ? today : payPeriodStartDate(p);
  });
  const [dailyGridRefresh, setDailyGridRefresh] = useState(0);
  const [mainView, setMainView] = useState<MainView>("daily");
  const [otExternalOpen, setOtExternalOpen] = useState(false);
  const [cycleListOpen, setCycleListOpen] = useState(false);
  const [syncOpen, setSyncOpen] = useState(false);
  const [dailySummary, setDailySummary] = useState<DailyGridSummary>({ total: 0, needsAction: 0 });
  const [leavePending, setLeavePending] = useState(0);
  const [syncProgress, setSyncProgress] = useState<SyncProgressState | null>(null);
  const monthlyGridApiRef = useRef<GridApi<TimesheetMonth> | null>(null);
  const detailSheetRef = useRef<HTMLDivElement>(null);
  const monthlyColPrefs = useMemo(() => createAgGridColumnPrefs(TK_MONTHLY_GRID_COLS), []);
  const timesheetRowsRef = useRef(rows);
  timesheetRowsRef.current = rows;
  const periodBounds = useMemo(() => {
    if (pay) return { date_from: pay.date_from, date_to: pay.date_to };
    return payPeriodDateBounds(period);
  }, [pay, period]);

  const onTypedSearch = useCallback((value: string) => {
    typedQRef.current = value;
  }, []);

  const loadEmpDays = useCallback(
    async (code: string, dateFrom: string, dateTo: string) => {
      setDaysLoading(true);
      try {
        const list = await fetchAttendanceDays({
          from: dateFrom,
          to: dateTo,
          employee_code: code,
        });
        setEmpDays(list);
      } catch (e) {
        setEmpDays([]);
        setError(e instanceof Error ? e.message : "Không tải được ngày công.");
      } finally {
        setDaysLoading(false);
      }
    },
    [],
  );

  const reload = useCallback(async () => {
    setError(null);
    try {
      const sheetsP = fetchTimesheets(period);
      const pendingP = fetchLeaveRequests({ status: "submitted" }).catch(() => []);
      const [pp, lt] = await Promise.all([fetchPayPeriod(period), fetchLeaveTypes()]);
      setPay(pp);
      const bounds = pp
        ? { date_from: pp.date_from, date_to: pp.date_to }
        : payPeriodDateBounds(period);
      setGridDate((prev) => {
        if (prev >= bounds.date_from && prev <= bounds.date_to) return prev;
        const today = todayIsoDateVN();
        if (today >= bounds.date_from && today <= bounds.date_to) return today;
        return bounds.date_from;
      });
      setLeaves(lt);
      void fetchIntegrationStatus()
        .then(setStatus)
        .catch(() => {});
      void pendingP.then((pendingLeaves) => setLeavePending(pendingLeaves.length));
      void fetchDepartments()
        .then((depts) => setDepartments(sortByViName(depts.filter((d) => d.is_active !== false))))
        .catch(() => {});
      const sheets = await sheetsP;
      setRows(sheets);
      setSelected((prev) => {
        if (!prev) return null;
        return sheets.find((s) => s.id === prev.id) ?? null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được Chấm Công.");
    }
  }, [period]);

  const refreshAfterSync = useCallback(async () => {
    try {
      cacheInvalidate("timesheets:");
      const [st, sheets, pp] = await Promise.all([
        fetchIntegrationStatus(),
        fetchTimesheets(period),
        fetchPayPeriod(period),
      ]);
      setStatus(st);
      setRows(sheets);
      setPay(pp);
      setDailyGridRefresh((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không cập nhật sau đồng bộ.");
    }
  }, [period]);

  useEffect(() => {
    // Kỳ đổi thì tải lại. Quay lại tab keep-alive không GET timesheet cả nhà máy.
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!selected) {
      setEmpDays([]);
      return;
    }
    void loadEmpDays(selected.employee_code, periodBounds.date_from, periodBounds.date_to);
  }, [selected?.employee_code, periodBounds.date_from, periodBounds.date_to, loadEmpDays]);

  async function refreshTimesheetsQuiet(employeeCode?: string) {
    const code = employeeCode?.trim();
    if (code) {
      const one = await fetchTimesheets(period, code);
      const next = one[0];
      if (!next) return;
      setRows((prev) => {
        const i = prev.findIndex(
          (s) => s.id === next.id || s.employee_code === next.employee_code,
        );
        if (i < 0) return [...prev, next];
        const copy = prev.slice();
        copy[i] = next;
        return copy;
      });
      setSelected((prev) => {
        if (!prev) return null;
        if (prev.id === next.id || prev.employee_code === next.employee_code) return next;
        return prev;
      });
      return;
    }
    cacheInvalidate(`timesheets:${period}`);
    const sheets = await fetchTimesheets(period);
    setRows(sheets);
    setSelected((prev) => {
      if (!prev) return null;
      return sheets.find((s) => s.id === prev.id) ?? prev;
    });
  }

  useEffect(() => {
    if (!ok) return;
    const timer = window.setTimeout(() => setOk(null), 3500);
    return () => window.clearTimeout(timer);
  }, [ok]);

  const filtered = useMemo(
    () => rows.filter((r) => employeeMatchesQuery(r, q)),
    [rows, q],
  );

  const pickEmployee = useCallback((row: TimesheetMonth) => {
    setSelected(row);
    setFixEmp(row.employee_code);
    setDetailOpen(true);
    setOk(null);
    setError(null);
  }, []);

  const pickFromDaily = useCallback(
    (gridRow: AttendanceDayGridRow) => {
      const match = timesheetRowsRef.current.find((r) => r.employee_code === gridRow.employee_code);
      if (match) pickEmployee(match);
    },
    [pickEmployee],
  );

  const onDailySummaryChange = useCallback((summary: DailyGridSummary) => {
    setDailySummary(summary);
  }, []);

  const calendar = useMemo(() => {
    if (!selected) return [];
    return buildCalendar(periodBounds.date_from, periodBounds.date_to, empDays);
  }, [periodBounds, selected, empDays]);

  const dayStats = useMemo(() => {
    const lateDays = calendar.filter((d) => d.late > 0).length;
    const earlyDays = calendar.filter((d) => d.early > 0).length;
    const punched = calendar.filter((d) => d.hasData).length;
    return { lateDays, earlyDays, punched, total: calendar.length };
  }, [calendar]);

  const clearSelection = useCallback(() => {
    setDetailOpen(false);
    setSelected(null);
    setEmpDays([]);
    setOk(null);
    setFixCycle(false);
  }, []);

  const closeDetail = useCallback(() => {
    setDetailOpen(false);
  }, []);

  useSheetKeyboard({
    open: detailOpen && !!selected,
    containerRef: detailSheetRef,
    onClose: closeDetail,
  });

  // ESC: lưới tháng còn banner NV đã chọn → bỏ chọn. Lưới ngày không hiện banner — không nuốt ESC (kẹt trang).
  useHrSubpageEsc({ backTo: "/" });
  useEscLayer(
    !!selected && mainView === "monthly" && !detailOpen && !otExternalOpen && !cycleListOpen && !syncOpen,
    () => {
      clearSelection();
    },
  );

  const monthlySearchRef = useRef(q);
  monthlySearchRef.current = q;
  const isMonthlyFilterPresent = useCallback(() => monthlySearchRef.current.trim().length > 0, []);
  const doesMonthlyFilterPass = useCallback((node: IRowNode<TimesheetMonth>) => {
    if (!node.data) return false;
    return employeeMatchesQuery(node.data, monthlySearchRef.current);
  }, []);

  useEffect(() => {
    monthlyGridApiRef.current?.onFilterChanged();
  }, [q]);

  const applySearchSelect = useCallback(
    (needle: string, opts?: { exactOnly?: boolean }) => {
      if (!needle.trim()) return false;
      const match = findEmployeeByQuery(rows, needle, opts);
      if (!match) {
        setError(`Không tìm thấy MSNV / tên khớp «${needle}».`);
        return false;
      }
      pickEmployee(match);
      const api = monthlyGridApiRef.current;
      if (api) {
        let shown = -1;
        api.forEachNodeAfterFilterAndSort((node, index) => {
          if (shown < 0 && node.data?.id === match.id) shown = index;
        });
        if (shown >= 0) api.ensureIndexVisible(shown);
      }
      return true;
    },
    [rows, pickEmployee],
  );

  function onSearchSubmit(e: FormEvent) {
    e.preventDefault();
    const needle = typedQRef.current.trim();
    setQ(needle);
    if (mainView === "monthly") applySearchSelect(needle);
  }

  const columnDefs = useMemo<ColDef<TimesheetMonth>[]>(
    () => [
      {
        colId: "view",
        headerName: "",
        width: 68,
        sortable: false,
        pinned: "left",
        cellRenderer: (p: { data?: TimesheetMonth }) => {
          if (!p.data) return null;
          return (
            <button
              type="button"
              className="tk-row-view-btn"
              onClick={(ev) => {
                ev.stopPropagation();
                pickEmployee(p.data!);
              }}
            >
              Xem
            </button>
          );
        },
      },
      { field: "employee_code", headerName: "MSNV", width: 72, filter: false },
      {
        field: "full_name",
        headerName: "Họ tên",
        flex: 1,
        minWidth: 100,
        filter: false,
      },
      {
        field: "worked_days",
        headerName: "Công",
        width: 68,
        filter: false,
        valueFormatter: (p) => fmtNum(p.value, 2),
      },
      {
        field: "al_days",
        headerName: "Phép năm",
        width: 72,
        filter: false,
        headerTooltip: TK_HEADER_TIPS.al,
        valueFormatter: (p) => fmtNum(p.value, 1),
      },
      {
        field: "rem_days",
        headerName: "Nghỉ REM",
        width: 72,
        filter: false,
        headerTooltip: TK_HEADER_TIPS.rem,
        valueFormatter: (p) => fmtNum(p.value, 1),
      },
      { field: "late_count", headerName: "Trễ", width: 48, filter: false },
      { field: "early_count", headerName: "Sớm", width: 52, filter: false },
      {
        field: "ot_hours_weekday",
        headerName: "Tăng ca sổ",
        width: 76,
        filter: false,
        headerTooltip: TK_HEADER_TIPS.otBooks,
        valueFormatter: (p) => formatOtHours(Number(p.value) * 60),
      },
      {
        field: "ot_hours_external",
        headerName: "Tăng ca ngoài",
        width: 88,
        filter: false,
        headerTooltip: TK_HEADER_TIPS.otExt,
        valueFormatter: (p) => formatOtHours(Number(p.value) * 60),
      },
      {
        field: "ot_hours_weekend",
        headerName: "OT CN",
        width: 72,
        filter: false,
        headerTooltip: TK_HEADER_TIPS.otWeekend,
        valueFormatter: (p) => formatOtHours(Number(p.value) * 60),
      },
      {
        field: "ot_hours_holiday",
        headerName: "OT lễ",
        width: 68,
        filter: false,
        headerTooltip: TK_HEADER_TIPS.otHoliday,
        valueFormatter: (p) => formatOtHours(Number(p.value) * 60),
      },
    ],
    [pickEmployee],
  );

  useEffect(() => {
    const api = monthlyGridApiRef.current;
    if (api) monthlyColPrefs.restore(api);
  }, [columnDefs, monthlyColPrefs]);

  function onRowClicked(e: RowClickedEvent<TimesheetMonth>) {
    if (e.data) pickEmployee(e.data);
  }

  function pickDay(row: CalendarRow) {
    setFixEmp(selected?.employee_code ?? fixEmp);
    setFixDate(row.work_date);
    setFixIn(row.firstIn || "");
    setFixOut(row.lastOut || "");
    setFixNote(row.hasData ? "Sửa tay chỉnh công" : "Bổ sung công tay");
    setFixCycle(row.cycleLeave);
  }

  const hoursPreview = useMemo(() => previewShiftWorkedHours(fixIn, fixOut), [fixIn, fixOut]);

  useEffect(() => {
    if (hoursFocusedRef.current) return;
    setFixHours(hoursPreview == null ? "" : formatWorkedHours(hoursPreview));
  }, [hoursPreview]);

  function applyQuickHours(raw: string) {
    const n = parseWorkedHoursInput(raw);
    if (n == null) return false;
    const inn = parseGridTimeInput(fixIn) || "08:00";
    const out = outTimeAfterWorkedHours(inn, n);
    if (!out) return false;
    if (!parseGridTimeInput(fixIn)) setFixIn(inn);
    setFixOut(out);
    setFixHours(formatWorkedHours(n));
    return true;
  }

  function focusManualField(id: string) {
    window.setTimeout(() => {
      const el = document.getElementById(id);
      if (el instanceof HTMLInputElement) el.focus();
    }, 0);
  }

  async function onSyncNow() {
    setBusy(true);
    setError(null);
    setOk(null);
    setSyncProgress({ active: true, percent: 0, message: "Bắt đầu đồng bộ…", ok: null });
    try {
      const result = await runSyncWithProgress(setSyncProgress);
      if (result.ok) {
        setOk(result.message);
      } else {
        setError(result.message);
      }
      await refreshAfterSync();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Không yêu cầu đồng bộ được.";
      setError(msg);
      setSyncProgress({ active: true, percent: 100, message: msg, ok: false });
    } finally {
      setBusy(false);
      window.setTimeout(() => setSyncProgress(null), 6000);
    }
  }

  async function onRebuild() {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const r = await rebuildTimesheets(period);
      setOk(r.message);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tổng hợp bảng công được.");
    } finally {
      setBusy(false);
    }
  }

  async function onOpenOtExternal() {
    setError(null);
    setOk(null);
    setOtExternalOpen(true);
  }

  function onOtExternalExported(message: string) {
    setOk(message);
    setOtExternalOpen(false);
  }

  async function refreshAfterManualDay(day: AttendanceDay) {
    const daysP = loadEmpDays(day.employee_code, periodBounds.date_from, periodBounds.date_to);
    await Promise.all([daysP, refreshTimesheetsQuiet(day.employee_code)]);
  }

  async function onManualDay(e: FormEvent) {
    e.preventDefault();
    const code = (fixEmp || selected?.employee_code || "").trim();
    const inT = fixIn.trim();
    const outT = fixOut.trim();
    if (inT && !parseGridTimeInput(inT)) {
      setError("Giờ vào phải dạng 07:44 (gõ 744 hoặc 7:44).");
      return;
    }
    if (outT && !parseGridTimeInput(outT)) {
      setError("Giờ ra phải dạng 09:10 (gõ 910 hoặc 9:10).");
      return;
    }
    const inIso = inT ? toIsoTime(fixDate, inT) : null;
    const outIso = outT ? toIsoTime(fixDate, outT) : null;
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      let day: AttendanceDay;
      if (!inIso && !outIso) {
        day = await patchAttendanceDayCell({
          employee_code: code,
          work_date: fixDate,
          clear_times: true,
          note: fixNote,
        });
        setOk(`Đã xóa giờ ${day.employee_code} ngày ${formatDateDDMMYYYY(day.work_date)}.`);
      } else if (!inIso || !outIso) {
        day = await patchAttendanceDayCell({
          employee_code: code,
          work_date: fixDate,
          first_in: inIso ?? undefined,
          last_out: outIso ?? undefined,
          clear_first_in: !inIso,
          clear_last_out: !outIso,
          note: fixNote,
        });
        setOk(`Đã sửa tay ${day.employee_code} ngày ${formatDateDDMMYYYY(day.work_date)}.`);
      } else {
        day = await patchAttendanceDayManual({
          employee_code: code,
          work_date: fixDate,
          first_in: inIso,
          last_out: outIso,
          note: fixNote,
          cycle_leave: fixCycle,
        });
        setOk(`Đã sửa tay ${day.employee_code} ngày ${formatDateDDMMYYYY(day.work_date)}.`);
      }
      await refreshAfterManualDay(day);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không sửa tay được.");
    } finally {
      setBusy(false);
    }
  }

  async function onClearDayTimes() {
    const code = (fixEmp || selected?.employee_code || "").trim();
    if (!code || !fixDate) return;
    if (
      !window.confirm(
        `Xóa giờ vào/ra ngày ${formatDateDDMMYYYY(fixDate)} của ${code}?\nCông, trễ, sớm, tăng ca ngày này về 0.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const day = await patchAttendanceDayCell({
        employee_code: code,
        work_date: fixDate,
        clear_times: true,
        note: fixNote.trim() || "Xóa giờ sai",
      });
      setFixIn("");
      setFixOut("");
      setFixHours("");
      setOk(`Đã xóa giờ ${day.employee_code} ngày ${formatDateDDMMYYYY(day.work_date)}.`);
      await refreshAfterManualDay(day);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa giờ được.");
    } finally {
      setBusy(false);
    }
  }

  async function onToggleCycle(on: boolean) {
    const code = (fixEmp || selected?.employee_code || "").trim();
    if (!code || !fixDate) return;
    setBusy(true);
    setError(null);
    setOk(null);
    setFixCycle(on);
    try {
      const day = await patchAttendanceDayCycle({
        employee_code: code,
        work_date: fixDate,
        cycle_leave: on,
      });
      setFixCycle(Boolean(day.cycle_leave));
      setFixOut(cellTime(day.last_out) || fixOut);
      setOk(
        on
          ? `Đã tích chu kỳ ${day.employee_code} ngày ${formatDateDDMMYYYY(day.work_date)} — giờ ra hết ca, đủ 8 giờ.`
          : `Đã bỏ tích chu kỳ ${day.employee_code} ngày ${formatDateDDMMYYYY(day.work_date)}.`,
      );
      await refreshAfterManualDay(day);
    } catch (err) {
      setFixCycle(!on);
      setError(err instanceof Error ? err.message : "Không tích chu kỳ được.");
    } finally {
      setBusy(false);
    }
  }

  const last = status?.last_job;
  const agentOk = last?.status === "success" || (!last && (status?.punch_count ?? 0) >= 0);

  function renderEmployeeDaysDetail() {
    if (!selected) return null;
    return (
      <div ref={detailSheetRef} className="tk-emp-sheet fs-sheet-form-shell">
        {/* Bảng ngày = vùng chính; form sửa tay = thanh gọn dưới (không chiếm nửa màn). */}
        <div className="tk-days-layout tk-days-layout--work">
          <div className="tk-day-scroll tk-day-scroll-full">
            <table className="tk-day-table">
              <thead>
                <tr>
                  <th>Ngày</th>
                  <th>Vào</th>
                  <th>Ra</th>
                  <th>Giờ</th>
                  <th>Trễ</th>
                  <th>Sớm</th>
                  <th title="Tăng ca trên sổ lương chính (Th3/Th5, trước 20h)">Tăng ca sổ</th>
                  <th title="Tăng ca trả ATM riêng">Tăng ca ngoài</th>
                  <th title="Tăng ca Chủ nhật — không cộng Công">OT CN</th>
                  <th title="Tăng ca ngày lễ — không cộng Công">OT lễ</th>
                  <th title="Cảnh báo">!</th>
                </tr>
              </thead>
              <tbody>
                {calendar.map((row) => (
                  <tr
                    key={row.work_date}
                    className={`tk-day-row flag-${row.flag}${
                      fixDate === row.work_date ? " is-pick" : ""
                    }`}
                    onClick={() => pickDay(row)}
                    title="Bấm để sửa giờ ngày này"
                  >
                    <td>
                      <span className="tk-day-date">{formatDateDDMMYYYY(row.work_date)}</span>
                      <span className="tk-day-wd">{row.weekday}</span>
                    </td>
                    <td
                      className={!row.firstIn ? "tk-cell-empty" : ""}
                      onClick={(e) => {
                        e.stopPropagation();
                        pickDay(row);
                        focusManualField("tk-manual-in");
                      }}
                    >
                      {row.firstIn}
                    </td>
                    <td
                      className={!row.lastOut ? "tk-cell-empty" : ""}
                      title={!row.lastOut ? "Bấm để nhập giờ ra" : undefined}
                      onClick={(e) => {
                        e.stopPropagation();
                        pickDay(row);
                        focusManualField("tk-manual-out");
                      }}
                    >
                      {row.lastOut}
                    </td>
                    <td
                      className={!row.hours ? "tk-cell-empty" : ""}
                      title="Bấm để nhập nhanh số giờ công"
                      onClick={(e) => {
                        e.stopPropagation();
                        pickDay(row);
                        focusManualField("tk-manual-hours");
                      }}
                    >
                      {row.hours}
                    </td>
                    <td className={row.late > 0 ? "tk-num-warn" : !row.late ? "tk-cell-empty" : ""}>
                      {cellMinutes(row.late)}
                    </td>
                    <td className={row.early > 0 ? "tk-num-warn" : !row.early ? "tk-cell-empty" : ""}>
                      {cellMinutes(row.early)}
                    </td>
                    <td className={!row.otOnBooks ? "tk-cell-empty" : ""}>
                      {formatOtHours(row.otOnBooks)}
                    </td>
                    <td className={!row.otExternal ? "tk-cell-empty tk-ot-ext" : "tk-ot-ext"}>
                      {formatOtHours(row.otExternal)}
                    </td>
                    <td className={!row.otWeekend ? "tk-cell-empty" : ""}>
                      {formatOtHours(row.otWeekend)}
                    </td>
                    <td className={!row.otHoliday ? "tk-cell-empty" : ""}>
                      {formatOtHours(row.otHoliday)}
                    </td>
                    <td className="tk-day-flag-cell">
                      {row.cycleLeave ? (
                        <span className="tk-cycle-hint" title="Chu kỳ — giờ ra hết ca, đủ 8 giờ">
                          CK
                        </span>
                      ) : row.oddPunch ? (
                        <span
                          className="tk-odd-hint"
                          title="Thiếu vào hoặc thiếu ra — hệ thống đã ghi nhận mốc có. HR gọi NV lập biên bản (quên bấm / về sớm / đi trễ)."
                        >
                          Lẻ
                        </span>
                      ) : row.missingPunch ? (
                        <span className="tk-miss-hint" title="Chưa chấm công — HR gọi NV kiểm tra, lập biên bản nếu cần">
                          Thiếu
                        </span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!daysLoading && dayStats.punched === 0 && (
              <p className="field-hint tk-day-empty-hint">
                Chưa có chấm từng ngày. Bấm một dòng → nhập Vào/Ra ở thanh dưới → Lưu giờ.
              </p>
            )}
          </div>

          <form className="tk-manual-bar" onSubmit={(e) => void onManualDay(e)}>
            <div className="tk-manual-bar-top">
              <span className="tk-manual-bar-stats" title="Tóm tắt tháng đang xem">
                {dayStats.punched}/{dayStats.total} có chấm · trễ {dayStats.lateDays} · sớm{" "}
                {dayStats.earlyDays}
                {daysLoading ? " · …" : ""}
              </span>
              <div className="tk-manual-bar-status" role="status" aria-live="polite">
                {error ? (
                  <p className="banner-warn">{error}</p>
                ) : ok ? (
                  <p className="banner-ok">{ok}</p>
                ) : null}
              </div>
            </div>
            <label className="field">
              <span>Ngày</span>
              <input
                type="date"
                value={fixDate}
                onChange={(e) => setFixDate(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Vào</span>
              <TimeInput24
                id="tk-manual-in"
                value={fixIn}
                onChange={setFixIn}
                placeholder="07:44"
                aria-label="Giờ vào"
              />
            </label>
            <label className="field">
              <span>Ra</span>
              <TimeInput24
                id="tk-manual-out"
                value={fixOut}
                onChange={setFixOut}
                placeholder="09:10"
                aria-label="Giờ ra"
              />
            </label>
            <label className="field tk-manual-hours-field">
              <span>Giờ công</span>
              <span className="tk-manual-hours-quick">
                <input
                  id="tk-manual-hours"
                  type="text"
                  inputMode="decimal"
                  value={fixHours}
                  placeholder="1,17"
                  aria-label="Nhập nhanh số giờ công"
                  title="Gõ số giờ (vd. 1,17 hoặc 8) rồi Enter — hệ thống điền giờ ra theo ca 08:00–17:00 trừ trưa"
                  onFocus={() => {
                    hoursFocusedRef.current = true;
                  }}
                  onChange={(e) => setFixHours(e.target.value)}
                  onBlur={(e) => {
                    hoursFocusedRef.current = false;
                    const raw = e.currentTarget.value;
                    if (!applyQuickHours(raw) && hoursPreview != null) {
                      setFixHours(formatWorkedHours(hoursPreview));
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      applyQuickHours(e.currentTarget.value);
                      hoursFocusedRef.current = false;
                      e.currentTarget.blur();
                    }
                  }}
                />
                <button
                  type="button"
                  className="tk-hours-chip"
                  disabled={busy}
                  onClick={() => applyQuickHours("4")}
                  title="4 giờ công (sáng 08:00–12:00)"
                >
                  4h
                </button>
                <button
                  type="button"
                  className="tk-hours-chip"
                  disabled={busy}
                  onClick={() => applyQuickHours("8")}
                  title="Đủ 8 giờ công (08:00–17:00 trừ trưa)"
                >
                  8h
                </button>
              </span>
            </label>
            <label className="field tk-manual-bar-note">
              <span>Ghi chú</span>
              <input
                value={fixNote}
                onChange={(e) => setFixNote(e.target.value)}
                placeholder="Tuỳ chọn"
              />
            </label>
            <label className="tk-cycle-check" title="Tích: giờ ra sớm thành hết ca (17:00), đủ 8 giờ">
              <input
                type="checkbox"
                checked={fixCycle}
                disabled={busy}
                onChange={(e) => void onToggleCycle(e.target.checked)}
              />
              Chu kỳ
            </label>
            <button
              type="button"
              className="btn-secondary"
              disabled={busy}
              onClick={() => void onClearDayTimes()}
              title="Xóa giờ vào/ra ngày đang chọn (giờ sai)"
            >
              Xóa giờ
            </button>
            <button type="submit" className="btn-primary" disabled={busy} title={`${fixEmp || selected.employee_code} · ${fixDate}`}>
              Lưu giờ
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="module-page tk-page">
      <ModuleLayerHeader
        layers={[
          { label: "← Portal", to: "/" },
          { label: "Chấm Công", current: true },
        ]}
      />

      <main className="module-body module-body-wide tk-main">
        <form className="tk-toolbar" onSubmit={onSearchSubmit}>
          <label className="period-picker period-picker-compact">
            Kỳ
            <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} />
          </label>
          {mainView === "daily" ? (
            <label className="period-picker period-picker-compact">
              Ngày công
              <input
                type="date"
                value={gridDate}
                min={periodBounds.date_from}
                max={periodBounds.date_to}
                onChange={(e) => setGridDate(e.target.value)}
              />
            </label>
          ) : null}
          {mainView === "daily" ? (
            <label className="period-picker period-picker-compact">
              Bộ phận
              <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
                <option value="">Tất cả</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {formatDepartmentLabel(d)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <ToolbarSearchInput
            wrapClassName="tk-search tk-search-compact"
            placeholder="MSNV hoặc họ tên…"
            resetToken={searchReset}
            onQuery={setQ}
            onTyped={onTypedSearch}
            onSubmit={(needle) => {
              setQ(needle);
              if (mainView === "monthly") applySearchSelect(needle);
            }}
          />
          {mainView === "monthly" ? (
            <button
              type="button"
              className="btn-ghost-dark btn-compact"
              disabled={busy || !q.trim()}
              title={disabledTitle(!q.trim(), "Nhập MSNV hoặc họ tên trước")}
              onClick={() => applySearchSelect(typedQRef.current.trim() || q)}
            >
              Xem tháng
            </button>
          ) : null}
          {q.trim() ? (
            <button
              type="button"
              className="btn-ghost-dark btn-compact"
              onClick={() => {
                setSearchReset((n) => n + 1);
                setQ("");
                clearSelection();
              }}
            >
              Xóa lọc
            </button>
          ) : null}
          <button
            type="button"
            className="btn-primary btn-compact"
            disabled={busy}
            onClick={() => void onSyncNow()}
          >
            Đồng bộ
          </button>
          <button
            type="button"
            className="btn-ghost-dark btn-compact"
            disabled={busy}
            onClick={() => {
              void reload();
              setDailyGridRefresh((n) => n + 1);
            }}
          >
            Làm mới
          </button>
          <ToolbarMoreMenu disabled={busy}>
            <button type="button" className="toolbar-more-item" onClick={() => void onRebuild()}>
              Tổng hợp công
            </button>
            <button type="button" className="toolbar-more-item" onClick={() => setSyncOpen(true)}>
              Nhật ký đồng bộ
            </button>
            <button
              type="button"
              className="toolbar-more-item"
              title="Xem và xuất tăng ca trả riêng"
              onClick={() => void onOpenOtExternal()}
            >
              Tăng ca ngoài
            </button>
          </ToolbarMoreMenu>
          <button
            type="button"
            className="btn-ghost-dark btn-compact"
            disabled={busy}
            onClick={() => setCycleListOpen(true)}
          >
            Danh sách chu kỳ
          </button>
        </form>

        {syncProgress?.active ? (
          <div
            className={`tk-sync-progress${syncProgress.ok === false ? " is-fail" : syncProgress.ok ? " is-ok" : ""}`}
            role="status"
            aria-live="polite"
          >
            <div className="tk-sync-progress-head">
              <span>{syncProgress.message}</span>
              <strong>{syncProgress.percent}%</strong>
            </div>
            <div className="tk-sync-progress-track" aria-hidden>
              <div className="tk-sync-progress-bar" style={{ width: `${syncProgress.percent}%` }} />
            </div>
          </div>
        ) : null}

        <div className="tk-status-bar" aria-live="polite">
          <span className="tk-meta">
            {pay ? (
              mainView === "daily" ? (
                <>
                  {dailySummary.total} nhân viên ·{" "}
                  <strong className={dailySummary.needsAction ? "tk-warn" : "tk-ok"}>
                    {dailySummary.needsAction} cần xử lý
                  </strong>
                  {" · "}
                  mẫu số {pay.salary_divisor} · <strong>{labelPeriodStatus(pay.status)}</strong>
                </>
              ) : mainView === "leave" ? (
                <>
                  {leavePending} đơn phép chờ duyệt
                </>
              ) : (
                <>
                  {filtered.length}/{rows.length} nhân viên · mẫu số {pay.salary_divisor} ·{" "}
                  <strong>{labelPeriodStatus(pay.status)}</strong>
                </>
              )
            ) : (
              "Chưa có kỳ lương — bấm Tổng hợp công"
            )}
          </span>
          <span className="tk-status-sync" title={status?.detail ?? "Cấu hình máy đồng bộ trong Cấu Hình"}>
            Đồng bộ:{" "}
            <strong className={agentOk ? "tk-ok" : "tk-warn"}>
              {last ? labelJobStatus(last.status) : "chưa có"}
            </strong>
            {last ? ` · thêm ${last.records_inserted}/trùng ${last.records_skipped}` : ""}
            {status ? ` · ${status.punch_count} lần chấm` : ""}
          </span>
        </div>

        <div className="tk-view-head">
          <div className="tk-view-tabs" role="tablist">
            {(
              [
                ["daily", "Kiểm theo ngày"],
                ["monthly", "Tổng hợp tháng"],
                ["leave", leavePending ? `Duyệt phép (${leavePending})` : "Duyệt phép"],
              ] as const
            ).map(([view, label]) => (
              <button
                key={view}
                type="button"
                role="tab"
                title={MAIN_VIEW_HINT[view]}
                className={mainView === view ? "is-on" : ""}
                onClick={() => setMainView(view)}
              >
                {label}
              </button>
            ))}
          </div>
          {selected && mainView === "monthly" && !detailOpen && (
            <div className="tk-active-emp tk-active-emp--inline">
              <strong>
                {selected.employee_code} · {selected.full_name}
              </strong>
              <span className="tk-active-stats">
                {`Công ${selected.worked_days} · phép ${selected.al_days} · trễ ${selected.late_count} · OT CN ${fmtNum(selected.ot_hours_weekend, 2)}h`}
              </span>
              <div className="tk-active-actions">
                <button type="button" className="btn-primary btn-sm" onClick={() => setDetailOpen(true)}>
                  Chi tiết ngày
                </button>
                <button type="button" className="btn-ghost-dark btn-sm" onClick={clearSelection}>
                  Bỏ
                </button>
              </div>
            </div>
          )}
        </div>

        {mainView === "daily" ? (
          <div className="tk-stack tk-stack-panel">
            <DailyGridPanel
              workDate={gridDate}
              periodLocked={pay?.status === "locked"}
              leaves={leaves}
              searchQuery={q}
              departmentId={departmentId}
              refreshToken={dailyGridRefresh}
              onSummaryChange={onDailySummaryChange}
              onPickEmployee={pickFromDaily}
              onTimesChanged={(code) => {
                void refreshTimesheetsQuiet(code);
              }}
            />
          </div>
        ) : mainView === "leave" ? (
          <div className="tk-stack tk-stack-panel">
            <LeaveApprovalPanel
              onChanged={() => {
                void fetchLeaveRequests({ status: "submitted" })
                  .then((list) => setLeavePending(list.length))
                  .catch(() => {});
                setDailyGridRefresh((n) => n + 1);
              }}
            />
          </div>
        ) : (
          <div className="tk-stack">
            <section className="tk-grid-section tk-grid-primary">
              <div className="tk-grid-wrap ag-theme-quartz">
                <AgGridReact<TimesheetMonth>
                  rowData={rows}
                  columnDefs={columnDefs}
                  localeText={AG_GRID_LOCALE_VI}
                  getRowId={(p) => p.data.id}
                  animateRows={false}
                  suppressHorizontalScroll
                  isExternalFilterPresent={isMonthlyFilterPresent}
                  doesExternalFilterPass={doesMonthlyFilterPass}
                  onRowClicked={onRowClicked}
                  onGridReady={(e) => {
                    monthlyGridApiRef.current = e.api;
                    if (!monthlyColPrefs.restore(e.api)) {
                      e.api.sizeColumnsToFit();
                    }
                    e.api.onFilterChanged();
                  }}
                  {...monthlyColPrefs.handlers}
                  getRowClass={(p) =>
                    p.data?.id === selected?.id ? "hr-row-selected" : undefined
                  }
                  defaultColDef={{
                    ...AG_GRID_DEFAULT_COL_DEF,
                    sortable: true,
                    resizable: true,
                    filter: false,
                    suppressHeaderMenuButton: false,
                  }}
                />
              </div>
            </section>
          </div>
        )}
      </main>

      <FullScreenSheet
        open={detailOpen && !!selected}
        title={
          selected
            ? `${selected.employee_code} · ${selected.full_name}`
            : "Chi tiết ngày công"
        }
        subtitle={
          selected
            ? `Kỳ ${period} · công ${selected.worked_days} · phép ${selected.al_days} · trễ ${selected.late_count} · sớm ${selected.early_count} · sổ ${fmtNum(selected.ot_hours_weekday, 2)}h · ngoài ${fmtNum(selected.ot_hours_external, 2)}h · OT CN ${fmtNum(selected.ot_hours_weekend, 2)}h · OT lễ ${fmtNum(selected.ot_hours_holiday, 2)}h`
            : undefined
        }
        onClose={closeDetail}
        closeOnEsc={false}
        inFrameScroll
        bodyClassName="fs-sheet-body-shell"
      >
        {renderEmployeeDaysDetail()}
      </FullScreenSheet>

      <FullScreenSheet
        open={syncOpen}
        title="Nhật ký đồng bộ chấm công"
        onClose={() => setSyncOpen(false)}
        bodyClassName="fs-sheet-body-shell"
      >
        <MitaproSyncPanel period={period} onChanged={() => void refreshAfterSync()} />
      </FullScreenSheet>

      <OtExternalPreviewSheet
        open={otExternalOpen}
        period={period}
        onClose={() => setOtExternalOpen(false)}
        onExported={onOtExternalExported}
      />
      <CycleLeaveListSheet
        open={cycleListOpen}
        period={period}
        onClose={() => setCycleListOpen(false)}
        onExported={(message) => {
          setOk(message);
          setCycleListOpen(false);
        }}
      />
      {(error || ok) &&
        !detailOpen &&
        createPortal(
          <div className="tk-float-toast" role="status" aria-live="polite">
            {error && <p className="banner-warn fs-sheet-banner">{error}</p>}
            {ok && <p className="banner-ok fs-sheet-banner">{ok}</p>}
          </div>,
          document.body,
        )}
    </div>
  );
}
