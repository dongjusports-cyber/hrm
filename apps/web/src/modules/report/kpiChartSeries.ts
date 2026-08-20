import type { KpiMonthTeamsData } from "../../shared/api";
import { formatOrgName } from "../../shared/formatOrg";

export type ChartDay = {
  workDate: string;
  dayNum: number;
  isWorkday: boolean;
  headcount: number;
  present: number;
  otHours: number;
};

export type ChartTeamOt = {
  teamId: string;
  label: string;
  hours: number;
};

export type ChartCategory = {
  category: string;
  label: string;
  attendants: number;
  otHours: number;
  headcount: number;
};

const CAT_ORDER = ["direct", "prod_indirect", "admin_indirect"] as const;
const CAT_LABEL: Record<(typeof CAT_ORDER)[number], string> = {
  direct: "Trực tiếp",
  prod_indirect: "Gián tiếp SX",
  admin_indirect: "Gián tiếp VP",
};

export function asNum(v: string | number | null | undefined): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

/** Làm tròn trục Y cho biểu đồ (1 / 2 / 5 × 10^n). */
export function niceMax(n: number): number {
  if (n <= 0) return 1;
  const exp = 10 ** Math.floor(Math.log10(n));
  const f = n / exp;
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10;
  return nice * exp;
}

export function monthLabel(period: string): string {
  const [y, m] = period.split("-");
  if (!y || !m) return period;
  return `${m}/${y}`;
}

export function companyDays(data: KpiMonthTeamsData): ChartDay[] {
  if (data.days?.length) {
    return data.days.map((d) => ({
      workDate: d.work_date,
      dayNum: Number(d.work_date.slice(-2)),
      isWorkday: d.is_workday,
      headcount: d.headcount,
      present: d.present,
      otHours: asNum(d.ot_hours),
    }));
  }
  const byDate = new Map<string, ChartDay>();
  for (const team of data.teams) {
    for (const cell of team.days ?? []) {
      const cur = byDate.get(cell.work_date) ?? {
        workDate: cell.work_date,
        dayNum: Number(cell.work_date.slice(-2)),
        isWorkday: cell.is_workday,
        headcount: data.headcount,
        present: 0,
        otHours: 0,
      };
      cur.present += cell.present;
      cur.otHours += asNum(cell.ot_hours);
      byDate.set(cell.work_date, cur);
    }
  }
  return [...byDate.values()].sort((a, b) => a.workDate.localeCompare(b.workDate));
}

export function teamOtBars(data: KpiMonthTeamsData, limit = 15): ChartTeamOt[] {
  const rows = data.teams
    .map((t) => ({
      teamId: t.team_id,
      label: formatOrgName(t.team_name) || t.team_code || t.team_id,
      hours: asNum(t.ot_hours),
    }))
    .filter((r) => r.hours > 0)
    .sort((a, b) => b.hours - a.hours || a.label.localeCompare(b.label, "vi"));
  if (rows.length <= limit) return rows;
  const head = rows.slice(0, limit);
  const rest = rows.slice(limit).reduce((s, r) => s + r.hours, 0);
  return [...head, { teamId: "_other", label: "Khác", hours: rest }];
}

export function categoryBars(data: KpiMonthTeamsData): ChartCategory[] {
  const map = new Map<string, ChartCategory>();
  for (const key of CAT_ORDER) {
    map.set(key, {
      category: key,
      label: CAT_LABEL[key],
      attendants: 0,
      otHours: 0,
      headcount: 0,
    });
  }
  for (const team of data.teams) {
    const key = CAT_ORDER.includes(team.category as (typeof CAT_ORDER)[number])
      ? team.category
      : "direct";
    const row = map.get(key);
    if (!row) continue;
    row.attendants += asNum(team.attendants);
    row.otHours += asNum(team.ot_hours);
    row.headcount += team.headcount;
  }
  return CAT_ORDER.map((key) => map.get(key)!);
}
