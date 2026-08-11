import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, RowClickedEvent } from "ag-grid-community";
import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import {
  createAdjustment,
  deleteAdjustment,
  fetchAdjustments,
  fetchAttendanceAnomalies,
  fetchAttendanceDays,
  fetchAttendanceReview,
  fetchIntegrationStatus,
  fetchLeaveTypes,
  fetchPayPeriod,
  fetchTimesheets,
  patchAttendanceDayManual,
  rebuildTimesheets,
  requestSyncNow,
  type AttendanceDay,
  type AttendanceReview,
  type AttendanceReviewIssue,
  type IntegrationStatus,
  type LeaveType,
  type PayPeriod,
  type TimesheetAdjustment,
  type TimesheetMonth,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { labelJobStatus, labelPeriodStatus } from "../../shared/viLabels";
import { LeaveApprovalPanel } from "./LeaveApprovalPanel";
import { DailyGridPanel } from "./DailyGridPanel";
import { MitaproSyncPanel } from "./MitaproSyncPanel";

ModuleRegistry.registerModules([AllCommunityModule]);

type MainView = "timesheet" | "sync";

type SideTab = "days" | "grid" | "adjust" | "review" | "late" | "leave";

type CalendarRow = {
  work_date: string;
  weekday: string;
  day?: AttendanceDay;
  hasData: boolean;
  late: number;
  early: number;
  ot: number;
  punches: number;
  firstIn: string;
  lastOut: string;
  hours: string;
  flag: "ok" | "late" | "early" | "both" | "empty" | "off";
};

const WEEKDAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

function defaultPeriod(): string {
  return "2025-12";
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

function hhmm(iso: string | null | undefined): string {
  if (!iso) return "—";
  const m = iso.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : "—";
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
    const hasData = Boolean(day && (punches > 0 || day.first_in || day.last_out));
    const isOff = day ? day.is_workday === false : wd === "CN" || wd === "T7";
    let flag: CalendarRow["flag"] = "empty";
    if (hasData) {
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
      late,
      early,
      ot: day?.ot_minutes ?? 0,
      punches,
      firstIn: hhmm(day?.first_in),
      lastOut: hhmm(day?.last_out),
      hours: day?.worked_hours != null ? String(day.worked_hours) : "—",
      flag,
    };
  });
}

export function TimekeepingPage() {
  const [period, setPeriod] = useState(defaultPeriod);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [pay, setPay] = useState<PayPeriod | null>(null);
  const [rows, setRows] = useState<TimesheetMonth[]>([]);
  const [leaves, setLeaves] = useState<LeaveType[]>([]);
  const [adjustments, setAdjustments] = useState<TimesheetAdjustment[]>([]);
  const [anomalies, setAnomalies] = useState<AttendanceDay[]>([]);
  const [review, setReview] = useState<AttendanceReview | null>(null);
  const [selected, setSelected] = useState<TimesheetMonth | null>(null);
  const [empDays, setEmpDays] = useState<AttendanceDay[]>([]);
  const [daysLoading, setDaysLoading] = useState(false);
  const [sideTab, setSideTab] = useState<SideTab>("days");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [kind, setKind] = useState<"leave" | "ot">("leave");
  const [empCode, setEmpCode] = useState("");
  const [leaveCode, setLeaveCode] = useState("ALE");
  const [days, setDays] = useState("1");
  const [otType, setOtType] = useState("weekday");
  const [otHours, setOtHours] = useState("2");
  const [note, setNote] = useState("");

  const [fixEmp, setFixEmp] = useState("");
  const [fixDate, setFixDate] = useState(`${defaultPeriod()}-01`);
  const [fixIn, setFixIn] = useState("08:00");
  const [fixOut, setFixOut] = useState("17:00");
  const [fixNote, setFixNote] = useState("Sửa tay thiếu chấm");
  const [gridDate, setGridDate] = useState(`${defaultPeriod()}-01`);
  const [mainView, setMainView] = useState<MainView>("timesheet");

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
      const [st, pp, sheets, lt, adj, rev] = await Promise.all([
        fetchIntegrationStatus(),
        fetchPayPeriod(period),
        fetchTimesheets(period),
        fetchLeaveTypes(),
        fetchAdjustments(period),
        fetchAttendanceReview(period),
      ]);
      setStatus(st);
      setPay(pp);
      setGridDate((prev) => {
        if (prev >= pp.date_from && prev <= pp.date_to) return prev;
        return pp.date_from;
      });
      setRows(sheets);
      setLeaves(lt);
      setAdjustments(adj);
      setReview(rev);
      setLeaveCode((prev) => (lt.some((x) => x.code === prev) ? prev : lt[0]?.code ?? prev));
      const anomaliesRows = await fetchAttendanceAnomalies(pp.date_from, pp.date_to);
      setAnomalies(anomaliesRows);
      setSelected((prev) => {
        if (!prev) return null;
        return sheets.find((s) => s.id === prev.id) ?? null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được Chấm Công.");
    }
  }, [period]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!selected || !pay) {
      setEmpDays([]);
      return;
    }
    void loadEmpDays(selected.employee_code, pay.date_from, pay.date_to);
  }, [selected, pay, loadEmpDays]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(
      (r) =>
        r.employee_code.toLowerCase().includes(needle) ||
        (r.full_name ?? "").toLowerCase().includes(needle),
    );
  }, [rows, q]);

  const empAdjustments = useMemo(() => {
    const code = (selected?.employee_code || empCode).trim();
    if (!code) return adjustments.slice(0, 20);
    return adjustments.filter((a) => a.employee_code === code);
  }, [adjustments, selected, empCode]);

  const calendar = useMemo(() => {
    if (!pay || !selected) return [];
    return buildCalendar(pay.date_from, pay.date_to, empDays);
  }, [pay, selected, empDays]);

  const dayStats = useMemo(() => {
    const lateDays = calendar.filter((d) => d.late > 0).length;
    const earlyDays = calendar.filter((d) => d.early > 0).length;
    const punched = calendar.filter((d) => d.hasData).length;
    return { lateDays, earlyDays, punched, total: calendar.length };
  }, [calendar]);

  const columnDefs = useMemo<ColDef<TimesheetMonth>[]>(
    () => [
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
        headerName: "AL",
        width: 52,
        filter: false,
        valueFormatter: (p) => fmtNum(p.value, 1),
      },
      {
        field: "rem_days",
        headerName: "REM",
        width: 56,
        filter: false,
        valueFormatter: (p) => fmtNum(p.value, 1),
      },
      { field: "late_count", headerName: "Trễ", width: 48, filter: false },
      { field: "early_count", headerName: "Sớm", width: 52, filter: false },
      {
        field: "ot_hours_weekday",
        headerName: "OT",
        width: 56,
        filter: false,
        valueFormatter: (p) => fmtNum(p.value, 1),
      },
    ],
    [],
  );

  function pickEmployee(row: TimesheetMonth) {
    setSelected(row);
    setEmpCode(row.employee_code);
    setFixEmp(row.employee_code);
    setSideTab("days");
    setOk(null);
  }

  function onRowClicked(e: RowClickedEvent<TimesheetMonth>) {
    if (e.data) pickEmployee(e.data);
  }

  function pickDay(row: CalendarRow) {
    setFixEmp(selected?.employee_code ?? empCode);
    setFixDate(row.work_date);
    if (row.firstIn !== "—") setFixIn(row.firstIn);
    if (row.lastOut !== "—") setFixOut(row.lastOut);
    setFixNote(row.hasData ? "Sửa tay chỉnh công" : "Bổ sung công tay");
  }

  async function onSyncNow() {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const job = await requestSyncNow();
      setOk(job.message);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không yêu cầu đồng bộ được.");
    } finally {
      setBusy(false);
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

  async function onAdjust(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const body =
        kind === "leave"
          ? {
              period,
              employee_code: empCode.trim(),
              kind: "leave",
              leave_code: leaveCode,
              days,
              note,
            }
          : {
              period,
              employee_code: empCode.trim(),
              kind: "ot",
              ot_type: otType,
              ot_hours: otHours,
              note,
            };
      const created = await createAdjustment(body);
      setOk(
        kind === "leave"
          ? `Đã ghi nghỉ ${created.leave_code} cho ${created.employee_code}.`
          : `Đã ghi OT ${created.ot_hours}h cho ${created.employee_code}.`,
      );
      setNote("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu điều chỉnh được.");
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteAdj(id: string) {
    setBusy(true);
    setError(null);
    try {
      await deleteAdjustment(id);
      setOk("Đã xóa điều chỉnh.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    } finally {
      setBusy(false);
    }
  }

  async function onManualDay(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const day = await patchAttendanceDayManual({
        employee_code: fixEmp.trim(),
        work_date: fixDate,
        first_in: `${fixDate}T${fixIn}:00+07:00`,
        last_out: `${fixDate}T${fixOut}:00+07:00`,
        note: fixNote,
      });
      setOk(`Đã sửa tay ${day.employee_code} ngày ${formatDateDDMMYYYY(day.work_date)}.`);
      await reload();
      if (pay) {
        await loadEmpDays(day.employee_code, pay.date_from, pay.date_to);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không sửa tay được.");
    } finally {
      setBusy(false);
    }
  }

  const last = status?.last_job;
  const agentOk = last?.status === "success" || (!last && (status?.punch_count ?? 0) >= 0);

  return (
    <div className="module-page tk-page">
      <header className="module-header">
        <Link to="/" className="btn-back">
          ← Portal
        </Link>
        <nav className="breadcrumb">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <span>Chấm Công</span>
        </nav>
      </header>

      <main className="module-body module-body-wide tk-main">
        {error && <p className="banner-warn">{error}</p>}
        {ok && <p className="banner-ok">{ok}</p>}

        <div className="tk-toolbar">
          <label className="period-picker">
            Kỳ
            <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} />
          </label>
          <label className="tk-search">
            <span className="sr-only">Tìm MSNV / họ tên</span>
            <input
              placeholder="Tìm MSNV hoặc họ tên…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              autoFocus
            />
          </label>
          <span className="tk-meta">
            {pay ? (
              <>
                {filtered.length}/{rows.length} NV · mẫu số {pay.salary_divisor} ·{" "}
                <strong>{labelPeriodStatus(pay.status)}</strong>
              </>
            ) : (
              "Đang tải…"
            )}
          </span>
          <button type="button" className="btn-ghost-dark" disabled={busy} onClick={() => void reload()}>
            Làm mới
          </button>
          <button type="button" className="btn-ghost-dark" disabled={busy} onClick={() => void onSyncNow()}>
            Đồng bộ công
          </button>
          <button type="button" className="btn-primary" disabled={busy} onClick={() => void onRebuild()}>
            Tổng hợp công
          </button>
        </div>

        <div className="tk-view-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            className={mainView === "timesheet" ? "is-on" : ""}
            onClick={() => setMainView("timesheet")}
          >
            Tổng hợp tháng
          </button>
          <button
            type="button"
            role="tab"
            className={mainView === "sync" ? "is-on" : ""}
            onClick={() => setMainView("sync")}
          >
            Đồng bộ Mitapro
          </button>
        </div>

        {mainView === "sync" ? (
          <MitaproSyncPanel period={period} onChanged={() => void reload()} />
        ) : (
          <>
        <p className="tk-agent-line" title={status?.detail ?? ""}>
          Đồng bộ:{" "}
          <strong className={agentOk ? "tk-ok" : "tk-warn"}>
            {last ? labelJobStatus(last.status) : "chưa có đồng bộ"}
          </strong>
          {last ? ` · +${last.records_inserted}/trùng ${last.records_skipped}` : ""}
          {status ? ` · ${status.punch_count} lần chấm` : ""}
          <span className="field-hint"> — cấu hình Agent chi tiết ở Cấu Hình (Admin)</span>
        </p>

        <div className={`tk-split${selected ? " has-detail" : ""}`}>
          <section className="tk-grid-wrap ag-theme-quartz">
            <AgGridReact<TimesheetMonth>
              rowData={filtered}
              columnDefs={columnDefs}
              getRowId={(p) => p.data.id}
              animateRows
              suppressHorizontalScroll
              onRowClicked={onRowClicked}
              onGridSizeChanged={(e) => e.api.sizeColumnsToFit()}
              onFirstDataRendered={(e) => e.api.sizeColumnsToFit()}
              getRowClass={(p) =>
                p.data?.id === selected?.id ? "hr-row-selected" : undefined
              }
              defaultColDef={{
                sortable: true,
                resizable: true,
                filter: false,
                suppressHeaderMenuButton: true,
              }}
            />
          </section>

          <aside className="tk-side">
            <div className="tk-side-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                className={sideTab === "days" ? "is-on" : ""}
                onClick={() => setSideTab("days")}
              >
                Ngày công
              </button>
              <button
                type="button"
                role="tab"
                className={sideTab === "grid" ? "is-on" : ""}
                onClick={() => setSideTab("grid")}
              >
                Bảng ngày
              </button>
              <button
                type="button"
                role="tab"
                className={sideTab === "adjust" ? "is-on" : ""}
                onClick={() => setSideTab("adjust")}
              >
                Điều chỉnh
              </button>
              <button
                type="button"
                role="tab"
                className={sideTab === "review" ? "is-on" : ""}
                onClick={() => setSideTab("review")}
              >
                Rà soát{review ? ` (${review.issue_count})` : ""}
              </button>
              <button
                type="button"
                role="tab"
                className={sideTab === "leave" ? "is-on" : ""}
                onClick={() => setSideTab("leave")}
              >
                Duyệt phép
              </button>
              <button
                type="button"
                role="tab"
                className={sideTab === "late" ? "is-on" : ""}
                onClick={() => setSideTab("late")}
              >
                Trễ/sớm
              </button>
            </div>

            {sideTab === "days" && (
              <div className="users-form-card tk-panel">
                {!selected ? (
                  <p className="module-placeholder">
                    Lọc MSNV (vd 1519) rồi bấm vào nhân viên để xem công từng ngày trong tháng và sửa tay khi cần.
                  </p>
                ) : (
                  <>
                    <div className="tk-selected">
                      <strong>
                        {selected.employee_code} · {selected.full_name}
                      </strong>
                      <span>
                        Tổng tháng: công {selected.worked_days} · AL {selected.al_days} · REM{" "}
                        {selected.rem_days} · trễ {selected.late_count} · sớm {selected.early_count} ·
                        OT {selected.ot_hours_weekday}h
                      </span>
                      <span className="field-hint">
                        Chi tiết ngày: {dayStats.punched}/{dayStats.total} có chấm · trễ{" "}
                        {dayStats.lateDays} ngày · sớm {dayStats.earlyDays} ngày
                        {daysLoading ? " · đang tải…" : ""}
                      </span>
                    </div>

                    <form className="tk-manual-form tk-manual-sticky" onSubmit={(e) => void onManualDay(e)}>
                      <p className="tk-manual-title">Sửa công tay</p>
                      <div className="tk-manual-grid">
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
                          <input
                            type="time"
                            value={fixIn}
                            onChange={(e) => setFixIn(e.target.value)}
                            required
                          />
                        </label>
                        <label className="field">
                          <span>Ra</span>
                          <input
                            type="time"
                            value={fixOut}
                            onChange={(e) => setFixOut(e.target.value)}
                            required
                          />
                        </label>
                      </div>
                      <label className="field">
                        <span>Ghi chú</span>
                        <input value={fixNote} onChange={(e) => setFixNote(e.target.value)} />
                      </label>
                      <button type="submit" className="btn-primary" disabled={busy}>
                        Lưu giờ tay ({fixEmp || selected.employee_code} · {fixDate})
                      </button>
                    </form>

                    <div className="tk-day-scroll">
                      <table className="tk-day-table">
                        <thead>
                          <tr>
                            <th>Ngày</th>
                            <th>Vào</th>
                            <th>Ra</th>
                            <th>Giờ</th>
                            <th>Trễ</th>
                            <th>Sớm</th>
                            <th>OT′</th>
                            <th></th>
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
                            >
                              <td>
                                <span className="tk-day-date">{formatDateDDMMYYYY(row.work_date)}</span>
                                <span className="tk-day-wd">{row.weekday}</span>
                              </td>
                              <td>{row.firstIn}</td>
                              <td>{row.lastOut}</td>
                              <td>{row.hours}</td>
                              <td className={row.late > 0 ? "tk-num-warn" : ""}>
                                {row.late || "—"}
                              </td>
                              <td className={row.early > 0 ? "tk-num-warn" : ""}>
                                {row.early || "—"}
                              </td>
                              <td>{row.ot || "—"}</td>
                              <td>
                                <button
                                  type="button"
                                  className="link-btn"
                                  onClick={(ev) => {
                                    ev.stopPropagation();
                                    pickDay(row);
                                  }}
                                >
                                  Chọn
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {!daysLoading && dayStats.punched === 0 && (
                        <p className="field-hint tk-day-empty-hint">
                          Chưa có chấm từng ngày (dữ liệu Excel chỉ có tổng tháng). Chọn một ngày ở
                          bảng → nhập giờ vào/ra phía trên → Lưu.
                        </p>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}

            {sideTab === "grid" && pay && (
              <div className="users-form-card tk-panel">
                <label className="field">
                  <span>Ngày công</span>
                  <input
                    type="date"
                    value={gridDate}
                    min={pay.date_from}
                    max={pay.date_to}
                    onChange={(e) => setGridDate(e.target.value)}
                  />
                </label>
                <DailyGridPanel
                  workDate={gridDate}
                  periodLocked={pay.status === "locked"}
                  leaves={leaves}
                  onChanged={() => void reload()}
                />
              </div>
            )}

            {sideTab === "adjust" && (
              <div className="users-form-card tk-panel">
                {selected ? (
                  <div className="tk-selected">
                    <strong>
                      {selected.employee_code} · {selected.full_name}
                    </strong>
                    <span>
                      Công {selected.worked_days} · AL {selected.al_days} · OT{" "}
                      {selected.ot_hours_weekday}
                    </span>
                  </div>
                ) : (
                  <p className="module-placeholder">
                    Chọn nhân viên hoặc nhập MSNV để ghi nghỉ / OT cả tháng.
                  </p>
                )}

                <form onSubmit={(e) => void onAdjust(e)}>
                  <label className="field">
                    <span>MSNV</span>
                    <input
                      value={empCode}
                      onChange={(e) => setEmpCode(e.target.value)}
                      list="tk-emp-codes"
                      required
                      placeholder="VD 5290"
                    />
                    <datalist id="tk-emp-codes">
                      {filtered.slice(0, 50).map((r) => (
                        <option key={r.id} value={r.employee_code}>
                          {r.full_name}
                        </option>
                      ))}
                    </datalist>
                  </label>
                  <label className="field">
                    <span>Loại</span>
                    <select
                      value={kind}
                      onChange={(e) => setKind(e.target.value as "leave" | "ot")}
                    >
                      <option value="leave">Nghỉ phép</option>
                      <option value="ot">Giờ OT</option>
                    </select>
                  </label>
                  {kind === "leave" ? (
                    <>
                      <label className="field">
                        <span>Mã nghỉ</span>
                        <select
                          value={leaveCode}
                          onChange={(e) => setLeaveCode(e.target.value)}
                        >
                          {leaves.map((l) => (
                            <option key={l.code} value={l.code}>
                              {l.code} — {l.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="field">
                        <span>Số ngày</span>
                        <input value={days} onChange={(e) => setDays(e.target.value)} required />
                      </label>
                    </>
                  ) : (
                    <>
                      <label className="field">
                        <span>Loại OT</span>
                        <select value={otType} onChange={(e) => setOtType(e.target.value)}>
                          <option value="weekday">Ngày thường</option>
                          <option value="weekend">Cuối tuần</option>
                          <option value="holiday">Lễ</option>
                        </select>
                      </label>
                      <label className="field">
                        <span>Số giờ</span>
                        <input
                          value={otHours}
                          onChange={(e) => setOtHours(e.target.value)}
                          required
                        />
                      </label>
                    </>
                  )}
                  <label className="field">
                    <span>Ghi chú</span>
                    <input value={note} onChange={(e) => setNote(e.target.value)} />
                  </label>
                  <button type="submit" className="btn-primary" disabled={busy}>
                    Lưu điều chỉnh
                  </button>
                </form>

                {empAdjustments.length > 0 && (
                  <ul className="tk-adj-list">
                    {empAdjustments.map((a) => (
                      <li key={a.id}>
                        <span>
                          {a.employee_code}:{" "}
                          {a.kind === "leave"
                            ? `${a.leave_code} ${a.days}n`
                            : `OT ${a.ot_hours}h`}
                        </span>
                        <button
                          type="button"
                          className="link-btn danger"
                          disabled={busy}
                          onClick={() => void onDeleteAdj(a.id)}
                        >
                          Xóa
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {sideTab === "review" && (
              <div className="users-form-card tk-panel">
                <p className="field-hint">
                  Thiếu / lẻ lần chấm. Tổng: <strong>{review?.issue_count ?? 0}</strong>
                </p>
                <form onSubmit={(e) => void onManualDay(e)}>
                  <label className="field">
                    <span>MSNV</span>
                    <input value={fixEmp} onChange={(e) => setFixEmp(e.target.value)} required />
                  </label>
                  <label className="field">
                    <span>Ngày</span>
                    <input
                      type="date"
                      value={fixDate}
                      onChange={(e) => setFixDate(e.target.value)}
                      required
                    />
                  </label>
                  <div className="tk-time-row">
                    <label className="field">
                      <span>Vào</span>
                      <input
                        type="time"
                        value={fixIn}
                        onChange={(e) => setFixIn(e.target.value)}
                        required
                      />
                    </label>
                    <label className="field">
                      <span>Ra</span>
                      <input
                        type="time"
                        value={fixOut}
                        onChange={(e) => setFixOut(e.target.value)}
                        required
                      />
                    </label>
                  </div>
                  <button type="submit" className="btn-primary" disabled={busy}>
                    Lưu giờ tay
                  </button>
                </form>
                <div className="tk-issue-scroll">
                  {(review?.issues ?? []).slice(0, 40).map((iss: AttendanceReviewIssue, idx) => (
                    <button
                      key={`${iss.employee_code}-${iss.work_date ?? "x"}-${idx}`}
                      type="button"
                      className="tk-issue"
                      onClick={() => {
                        setFixEmp(iss.employee_code);
                        if (iss.work_date) setFixDate(iss.work_date);
                        setEmpCode(iss.employee_code);
                        const row = rows.find((r) => r.employee_code === iss.employee_code);
                        if (row) {
                          setSelected(row);
                          setSideTab("days");
                        }
                      }}
                    >
                      <strong>{iss.employee_code}</strong> {iss.work_date ? formatDateDDMMYYYY(iss.work_date) : ""} — {iss.message}
                    </button>
                  ))}
                  {!review?.issues.length && (
                    <p className="module-placeholder">Không có cảnh báo kỳ này.</p>
                  )}
                </div>
              </div>
            )}

            {sideTab === "leave" && (
              <div className="users-form-card tk-panel">
                <LeaveApprovalPanel />
              </div>
            )}

            {sideTab === "late" && (
              <div className="users-form-card tk-panel">
                <div className="tk-issue-scroll">
                  {anomalies.length === 0 ? (
                    <p className="module-placeholder">Không có trễ/sớm trong kỳ.</p>
                  ) : (
                    anomalies
                      .filter((d) => {
                        const needle = q.trim().toLowerCase();
                        if (!needle) return true;
                        return (
                          d.employee_code.toLowerCase().includes(needle) ||
                          (d.full_name ?? "").toLowerCase().includes(needle)
                        );
                      })
                      .slice(0, 60)
                      .map((d) => (
                        <button
                          key={d.id}
                          type="button"
                          className="tk-issue"
                          onClick={() => {
                            setEmpCode(d.employee_code);
                            setFixEmp(d.employee_code);
                            setFixDate(d.work_date);
                            const row = rows.find((r) => r.employee_code === d.employee_code);
                            if (row) setSelected(row);
                            setSideTab("days");
                          }}
                        >
                          <strong>{d.employee_code}</strong> {formatDateDDMMYYYY(d.work_date)} — trễ {d.late_minutes}′ /
                          sớm {d.early_minutes}′
                        </button>
                      ))
                  )}
                </div>
              </div>
            )}
          </aside>
        </div>
          </>
        )}
      </main>
    </div>
  );
}
