/** Query Chấm Công — AI / deep-link mở bảng công CTY · bộ phận · MSNV. */

export type TimesheetMainView = "daily" | "monthly" | "leave";

export type TimesheetUrlState = {
  view: TimesheetMainView | null;
  period: string | null;
  deptCode: string | null;
  departmentId: string | null;
  q: string | null;
  date: string | null;
  print: boolean;
  needs: boolean;
  odd: boolean;
};

const PERIOD_RE = /^\d{4}-\d{2}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function parseTimesheetSearch(search: string): TimesheetUrlState {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const sp = new URLSearchParams(raw);
  const view = sp.get("view");
  const period = sp.get("period")?.trim() || "";
  const date = sp.get("date")?.trim() || "";
  const q = (sp.get("q") || sp.get("emp") || "").trim();
  return {
    view: view === "daily" || view === "monthly" || view === "leave" ? view : null,
    period: PERIOD_RE.test(period) ? period : null,
    deptCode: sp.get("dept")?.trim() || null,
    departmentId: sp.get("department_id")?.trim() || null,
    q: q || null,
    date: DATE_RE.test(date) ? date : null,
    print: sp.get("print") === "1",
    needs: sp.get("needs") === "1" || sp.get("needs") === "true",
    odd: sp.get("odd") === "1" || sp.get("odd") === "true",
  };
}

export function isTimesheetExportHref(href: string | null | undefined): boolean {
  if (!href) return false;
  return href.includes("/attendance/timesheets/") && href.includes("/export");
}
