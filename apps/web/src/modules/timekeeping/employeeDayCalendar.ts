import { formatTimeHHMM } from "../../shared/formatDate";
import type { AttendanceDay } from "../../shared/api";
import { holidayOtMinutes, weekendOtMinutes } from "./otDisplay";

const WEEKDAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

export type CalendarRow = {
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
  leaveCode: string;
  cycleLeave: boolean;
  flag: "ok" | "late" | "early" | "both" | "empty" | "off" | "odd" | "missing" | "leave";
  oddPunch: boolean;
  missingPunch: boolean;
};

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

function isOddPunchDay(day: AttendanceDay | undefined, punches: number): boolean {
  if (!day) return false;
  if (punches === 1) return true;
  if (punches > 0 && (!day.first_in || !day.last_out)) return true;
  return false;
}

function cellTime(iso: string | null | undefined): string {
  return formatTimeHHMM(iso, "");
}

/** Lịch ngày một NV — có leave_code thì không gắn «Thiếu». */
export function buildCalendar(dateFrom: string, dateTo: string, days: AttendanceDay[]): CalendarRow[] {
  const byDate = new Map(days.map((d) => [d.work_date, d]));
  return eachDate(dateFrom, dateTo).map((work_date) => {
    const day = byDate.get(work_date);
    const wd = WEEKDAYS[parseYmd(work_date).getDay()] ?? "";
    const late = day?.late_minutes ?? 0;
    const early = day?.early_minutes ?? 0;
    const punches = day?.punch_count ?? 0;
    const leaveCode = (day?.leave_code || "").trim().toUpperCase();
    const oddPunch = isOddPunchDay(day, punches);
    const hasComplete = Boolean(day?.first_in && day?.last_out);
    const hasPartial = Boolean(day?.first_in || day?.last_out);
    const isOff = day ? !day.is_workday : wd === "CN";
    const isWorkday = !isOff;
    const missingPunch = isWorkday && !hasComplete && !hasPartial && !leaveCode;
    const hasData = hasComplete;
    let flag: CalendarRow["flag"] = "empty";
    if (oddPunch) flag = "odd";
    else if (leaveCode && !hasPartial) flag = "leave";
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
      hours: hasComplete && day?.worked_hours != null ? String(day.worked_hours) : "",
      leaveCode,
      cycleLeave: Boolean(day?.cycle_leave),
      flag,
      oddPunch,
      missingPunch,
    };
  });
}
