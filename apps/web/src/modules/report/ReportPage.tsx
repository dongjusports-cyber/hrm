import { useCallback, useEffect, useMemo, useState } from "react";
import {
  downloadKpiDayExport,
  downloadKpiMonthExport,
  fetchKpiDay,
  fetchKpiDayPeople,
  fetchKpiMonthPeople,
  fetchKpiMonthTeams,
  type KpiDayData,
  type KpiDayPerson,
  type KpiMonthPerson,
  type KpiMonthTeamsData,
  type KpiTeamDayRow,
  type KpiTeamMonthRow,
} from "../../shared/api";
import { currentPayPeriod, formatTimeHHMM, todayIsoDateVN } from "../../shared/formatDate";
import { formatOrgName } from "../../shared/formatOrg";
import { FullScreenSheet } from "../../shared/FullScreenSheet";
import { ModuleLayerHeader } from "../../shared/ModuleLayerHeader";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";

const KPI_FROM = "2026-08-01";

function fmtPct(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return `${Number(v).toLocaleString("vi-VN")}%`;
}

function fmtNum(v: string | number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  if (digits === 0) return n.toLocaleString("vi-VN");
  return n.toLocaleString("vi-VN", { minimumFractionDigits: 0, maximumFractionDigits: digits });
}

function yesterdayOrKpiFrom(): string {
  const today = todayIsoDateVN();
  const [y, m, d] = today.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() - 1);
  const iso = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
  return iso < KPI_FROM ? KPI_FROM : iso;
}

type Mode = "day" | "month";

/** Báo cáo KPI giám đốc — theo tổ, ngày / tháng, xuất Excel lưu. */
export function ReportPage() {
  useHrSubpageEsc({ backTo: "/" });
  const [mode, setMode] = useState<Mode>("day");
  const [workDate, setWorkDate] = useState(yesterdayOrKpiFrom);
  const [period, setPeriod] = useState(() => {
    const p = currentPayPeriod();
    return p < "2026-08" ? "2026-08" : p;
  });
  const [day, setDay] = useState<KpiDayData | null>(null);
  const [month, setMonth] = useState<KpiMonthTeamsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetTitle, setSheetTitle] = useState("");
  const [dayPeople, setDayPeople] = useState<KpiDayPerson[] | null>(null);
  const [monthPeople, setMonthPeople] = useState<KpiMonthPerson[] | null>(null);
  const [peopleBusy, setPeopleBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      if (mode === "day") {
        setDay(await fetchKpiDay(workDate));
        setMonth(null);
      } else {
        setMonth(await fetchKpiMonthTeams(period));
        setDay(null);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải KPI.");
      setDay(null);
      setMonth(null);
    } finally {
      setLoading(false);
    }
  }, [mode, workDate, period]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onExport() {
    setExporting(true);
    try {
      if (mode === "day") await downloadKpiDayExport(workDate);
      else await downloadKpiMonthExport(period);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xuất Excel.");
    } finally {
      setExporting(false);
    }
  }

  async function openDayTeam(row: KpiTeamDayRow) {
    setSheetTitle(`${formatOrgName(row.team_name)} · ${workDate.split("-").reverse().join("/")}`);
    setMonthPeople(null);
    setDayPeople(null);
    setSheetOpen(true);
    setPeopleBusy(true);
    try {
      setDayPeople(await fetchKpiDayPeople(workDate, row.team_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải danh sách người.");
      setSheetOpen(false);
    } finally {
      setPeopleBusy(false);
    }
  }

  async function openMonthTeam(row: KpiTeamMonthRow) {
    setSheetTitle(`${formatOrgName(row.team_name)} · tháng ${period}`);
    setDayPeople(null);
    setMonthPeople(null);
    setSheetOpen(true);
    setPeopleBusy(true);
    try {
      setMonthPeople(await fetchKpiMonthPeople(period, row.team_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải danh sách người.");
      setSheetOpen(false);
    } finally {
      setPeopleBusy(false);
    }
  }

  const hint = useMemo(() => {
    if (mode === "day" && day) return day.formula_note;
    if (mode === "month" && month) return month.formula_note;
    return "Nguồn vân tay từ tháng 8/2026. OT gồm sổ, ngoài, CN, lễ.";
  }, [mode, day, month]);

  return (
    <div className="module-page">
      <ModuleLayerHeader
        layers={[
          { label: "← Portal", to: "/" },
          { label: "Báo Cáo / KPI", current: true },
        ]}
      />
      <main className="module-body">
        <div className="module-toolbar">
          <h1>KPI giám đốc</h1>
          <div className="toolbar-right">
            <div className="tk-view-tabs" role="tablist" aria-label="Ngày hoặc tháng">
              <button
                type="button"
                role="tab"
                className={mode === "day" ? "is-on" : ""}
                aria-selected={mode === "day"}
                onClick={() => setMode("day")}
              >
                Ngày
              </button>
              <button
                type="button"
                role="tab"
                className={mode === "month" ? "is-on" : ""}
                aria-selected={mode === "month"}
                onClick={() => setMode("month")}
              >
                Tháng
              </button>
            </div>
            {mode === "day" ? (
              <label className="period-picker">
                Ngày
                <input
                  type="date"
                  min={KPI_FROM}
                  value={workDate}
                  onChange={(e) => setWorkDate(e.target.value || KPI_FROM)}
                />
              </label>
            ) : (
              <label className="period-picker">
                Kỳ
                <input
                  type="month"
                  min="2026-08"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value || "2026-08")}
                />
              </label>
            )}
            <button type="button" className="btn-secondary" disabled={exporting || loading} onClick={() => void onExport()}>
              {exporting ? "Đang xuất…" : mode === "day" ? "Xuất Excel ngày" : "Xuất Excel tháng"}
            </button>
          </div>
        </div>
        <p className="field-hint">{hint}</p>
        {error && <p className="banner-warn">{error}</p>}
        {loading ? (
          <p className="field-hint">Đang tải…</p>
        ) : mode === "day" && day ? (
          <DayView data={day} onOpenTeam={openDayTeam} />
        ) : mode === "month" && month ? (
          <MonthView data={month} onOpenTeam={openMonthTeam} />
        ) : (
          <p className="field-hint">Không có dữ liệu.</p>
        )}
      </main>

      <FullScreenSheet
        open={sheetOpen}
        title={sheetTitle}
        subtitle="Bấm ESC hoặc Đóng để về bảng tổ"
        onClose={() => setSheetOpen(false)}
      >
        {peopleBusy ? (
          <p className="field-hint">Đang tải…</p>
        ) : dayPeople ? (
          <PeopleDayTable rows={dayPeople} />
        ) : monthPeople ? (
          <PeopleMonthTable rows={monthPeople} />
        ) : null}
      </FullScreenSheet>
    </div>
  );
}

function DayView({
  data,
  onOpenTeam,
}: {
  data: KpiDayData;
  onOpenTeam: (row: KpiTeamDayRow) => void;
}) {
  return (
    <>
      <div className="kpi-cards">
        <article className="kpi-card">
          <p>Có mặt / HC</p>
          <strong>
            {data.present}/{data.headcount}
          </strong>
          <small>Vắng {data.absent}</small>
        </article>
        <article className="kpi-card">
          <p>Tổ tăng ca</p>
          <strong>{data.teams_with_ot}</strong>
          <small>{data.ot_people} người</small>
        </article>
        <article className="kpi-card">
          <p>Giờ OT</p>
          <strong>{fmtNum(data.ot_hours)}</strong>
          <small>Sổ + ngoài + CN + lễ</small>
        </article>
        <article className="kpi-card">
          <p>Thiếu chấm / trễ</p>
          <strong>
            {data.missing_punch} / {data.late_people}
          </strong>
          <small>{data.is_workday ? "Ngày công" : "Ngày nghỉ (CN/lễ)"}</small>
        </article>
      </div>
      <section className="kpi-section">
        <h2>Theo tổ — bấm dòng để xem từng người</h2>
        <div className="kpi-table-wrap">
          <table className="kpi-table kpi-table-click">
            <thead>
              <tr>
                <th>Bộ phận</th>
                <th>Tổ</th>
                <th>Loại</th>
                <th>HC</th>
                <th>Có mặt</th>
                <th>Vắng</th>
                <th>Thiếu chấm</th>
                <th>Trễ</th>
                <th>Người OT</th>
                <th>Giờ OT</th>
                <th>OT/người</th>
              </tr>
            </thead>
            <tbody>
              {data.teams.map((t) => (
                <tr key={t.team_id} onClick={() => onOpenTeam(t)}>
                  <td>{formatOrgName(t.department_name)}</td>
                  <td>{formatOrgName(t.team_name)}</td>
                  <td>{t.category_label}</td>
                  <td>{t.headcount}</td>
                  <td>{t.present}</td>
                  <td>{t.absent || ""}</td>
                  <td className={t.missing_punch ? "kpi-warn" : ""}>{t.missing_punch || ""}</td>
                  <td>{t.late_people || ""}</td>
                  <td>{t.ot_people || ""}</td>
                  <td>{t.ot_people ? fmtNum(t.ot_hours) : ""}</td>
                  <td>{t.ot_people ? fmtNum(t.ot_hours_per_person) : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function MonthView({
  data,
  onOpenTeam,
}: {
  data: KpiMonthTeamsData;
  onOpenTeam: (row: KpiTeamMonthRow) => void;
}) {
  return (
    <>
      <div className="kpi-cards">
        <article className="kpi-card">
          <p>Chuyên cần</p>
          <strong>{fmtPct(data.attendance_rate_pct)}</strong>
          <small>
            {fmtNum(data.attendants, 0)} ngày có mặt / HC {data.headcount} × B3 {fmtNum(data.param_b3, 0)}
          </small>
        </article>
        <article className="kpi-card">
          <p>Giờ OT</p>
          <strong>{fmtNum(data.ot_hours)}</strong>
          <small>{data.ot_people} người</small>
        </article>
        <article className="kpi-card">
          <p>Tỷ lệ OT</p>
          <strong>{fmtPct(data.ot_share_pct)}</strong>
          <small>Chia sẻ (file sếp) · công suất {fmtPct(data.ot_capacity_pct)}</small>
        </article>
        <article className="kpi-card">
          <p>Nghỉ việc</p>
          <strong>{fmtPct(data.turnover_rate_pct)}</strong>
          <small>
            Tuyển {data.recruit} · Nghỉ {data.resign}
          </small>
        </article>
      </div>
      <section className="kpi-section">
        <h2>Theo tổ — chi tiết từng ngày nằm trong file Excel tháng</h2>
        <div className="kpi-table-wrap">
          <table className="kpi-table kpi-table-click">
            <thead>
              <tr>
                <th>Bộ phận</th>
                <th>Tổ</th>
                <th>Loại</th>
                <th>HC</th>
                <th>Ngày có mặt</th>
                <th>Chuyên cần</th>
                <th>Giờ OT</th>
                <th>Người OT</th>
                <th>OT chia sẻ</th>
                <th>Tuyển / nghỉ</th>
              </tr>
            </thead>
            <tbody>
              {data.teams.map((t) => (
                <tr key={t.team_id} onClick={() => onOpenTeam(t)}>
                  <td>{formatOrgName(t.department_name)}</td>
                  <td>{formatOrgName(t.team_name)}</td>
                  <td>{t.category_label}</td>
                  <td>{t.headcount}</td>
                  <td>{fmtNum(t.attendants, 0)}</td>
                  <td>{fmtPct(t.attendance_rate_pct)}</td>
                  <td>{Number(t.ot_hours) > 0 ? fmtNum(t.ot_hours) : ""}</td>
                  <td>{t.ot_people || ""}</td>
                  <td>{fmtPct(t.ot_share_pct)}</td>
                  <td>
                    {t.recruit}/{t.resign}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function PeopleDayTable({ rows }: { rows: KpiDayPerson[] }) {
  return (
    <div className="kpi-table-wrap">
      <table className="kpi-table">
        <thead>
          <tr>
            <th>MSNV</th>
            <th>Họ tên</th>
            <th>Có mặt</th>
            <th>Vào</th>
            <th>Ra</th>
            <th>Công</th>
            <th>OT sổ</th>
            <th>OT ngoài</th>
            <th>OT tổng</th>
            <th>Trễ</th>
            <th>Nghỉ</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.employee_code}>
              <td>{p.employee_code}</td>
              <td>{p.full_name}</td>
              <td>{p.present ? "Có" : ""}</td>
              <td>{formatTimeHHMM(p.first_in, "")}</td>
              <td>{formatTimeHHMM(p.last_out, "")}</td>
              <td>{Number(p.worked_hours) > 0 ? fmtNum(p.worked_hours) : ""}</td>
              <td>{Number(p.ot_on_books_hours) > 0 ? fmtNum(p.ot_on_books_hours) : ""}</td>
              <td>{Number(p.ot_external_hours) > 0 ? fmtNum(p.ot_external_hours) : ""}</td>
              <td>{Number(p.ot_hours) > 0 ? fmtNum(p.ot_hours) : ""}</td>
              <td>{p.late_minutes || ""}</td>
              <td>{p.leave_code || ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 ? <p className="field-hint">Không có nhân viên tổ này.</p> : null}
    </div>
  );
}

function PeopleMonthTable({ rows }: { rows: KpiMonthPerson[] }) {
  return (
    <div className="kpi-table-wrap">
      <table className="kpi-table">
        <thead>
          <tr>
            <th>MSNV</th>
            <th>Họ tên</th>
            <th>Ngày có mặt</th>
            <th>Ngày trễ</th>
            <th>Giờ OT</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.employee_code}>
              <td>{p.employee_code}</td>
              <td>{p.full_name}</td>
              <td>{p.present_days}</td>
              <td>{p.late_days || ""}</td>
              <td>{Number(p.ot_hours) > 0 ? fmtNum(p.ot_hours) : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
