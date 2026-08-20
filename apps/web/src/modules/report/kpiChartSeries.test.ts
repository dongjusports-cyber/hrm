import { describe, expect, it } from "vitest";
import type { KpiMonthTeamsData } from "../../shared/api";
import { categoryBars, companyDays, niceMax, teamOtBars } from "./kpiChartSeries";

function month(partial: Partial<KpiMonthTeamsData> & Pick<KpiMonthTeamsData, "teams">): KpiMonthTeamsData {
  return {
    period: "2026-08",
    official_work_days: 26,
    param_b3: 26,
    headcount: 10,
    attendants: 100,
    attendance_rate_pct: 80,
    ot_hours: 12,
    ot_people: 3,
    ot_share_pct: 5,
    ot_capacity_pct: 2,
    recruit: 0,
    resign: 0,
    turnover_rate_pct: 0,
    formula_note: "",
    ...partial,
  };
}

describe("kpiChartSeries", () => {
  it("niceMax làm tròn trục", () => {
    expect(niceMax(0)).toBe(1);
    expect(niceMax(3)).toBe(5);
    expect(niceMax(12)).toBe(20);
  });

  it("companyDays ưu tiên days công ty", () => {
    const days = companyDays(
      month({
        teams: [],
        days: [
          {
            work_date: "2026-08-18",
            is_workday: true,
            headcount: 10,
            present: 9,
            absent: 1,
            ot_hours: "3.00",
            ot_people: 1,
          },
        ],
      }),
    );
    expect(days).toEqual([
      {
        workDate: "2026-08-18",
        dayNum: 18,
        isWorkday: true,
        headcount: 10,
        present: 9,
        otHours: 3,
      },
    ]);
  });

  it("teamOtBars xếp OT giảm dần và gộp Khác", () => {
    const rows = teamOtBars(
      month({
        teams: [
          team("a", "Tổ A", 1),
          team("b", "Tổ B", 8),
          team("c", "Tổ C", 0),
          team("d", "Tổ D", 3),
        ],
      }),
      2,
    );
    expect(rows.map((r) => r.label)).toEqual(["Tổ B", "Tổ D", "Khác"]);
    expect(rows[2]?.hours).toBe(1);
  });

  it("categoryBars cộng theo loại KPI", () => {
    const cats = categoryBars(
      month({
        teams: [
          team("a", "SX", 10, { category: "direct", attendants: 20, headcount: 8 }),
          team("b", "Kho", 2, { category: "prod_indirect", attendants: 5, headcount: 2 }),
          team("c", "VP", 1, { category: "admin_indirect", attendants: 4, headcount: 1 }),
        ],
      }),
    );
    expect(cats.map((c) => [c.label, c.otHours, c.attendants])).toEqual([
      ["Trực tiếp", 10, 20],
      ["Gián tiếp SX", 2, 5],
      ["Gián tiếp VP", 1, 4],
    ]);
  });
});

function team(
  id: string,
  name: string,
  ot: number,
  extra?: { category?: string; attendants?: number; headcount?: number },
): KpiMonthTeamsData["teams"][number] {
  return {
    team_id: id,
    team_code: id,
    team_name: name,
    department_code: "D",
    department_name: "Dept",
    category: extra?.category ?? "direct",
    category_label: extra?.category ?? "Trực tiếp",
    headcount: extra?.headcount ?? 1,
    begin_hc: 1,
    recruit: 0,
    resign: 0,
    end_hc: 1,
    attendants: extra?.attendants ?? 0,
    attendance_rate_pct: 0,
    ot_hours: ot,
    ot_people: ot > 0 ? 1 : 0,
    ot_share_pct: 0,
    ot_capacity_pct: 0,
    turnover_rate_pct: 0,
  };
}
