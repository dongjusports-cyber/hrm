import { describe, expect, it } from "vitest";
import type { AttendanceDay } from "../../shared/api";
import { buildCalendar } from "./employeeDayCalendar";

function day(partial: Partial<AttendanceDay> & Pick<AttendanceDay, "work_date">): AttendanceDay {
  return {
    id: partial.work_date,
    employee_code: "1648",
    full_name: "Test",
    late_minutes: 0,
    early_minutes: 0,
    ot_minutes: 0,
    punch_count: 0,
    is_workday: true,
    ...partial,
  };
}

describe("buildCalendar leave vs Thiếu", () => {
  it("ngày phép không gắn missing / Thiếu", () => {
    const rows = buildCalendar("2026-08-11", "2026-08-13", [
      day({ work_date: "2026-08-11", leave_code: "ALE" }),
      day({ work_date: "2026-08-12", leave_code: "ALE" }),
      day({
        work_date: "2026-08-13",
        first_in: "2026-08-13T00:55:00Z",
        last_out: "2026-08-13T09:05:00Z",
        punch_count: 2,
        worked_hours: 8,
      }),
    ]);
    expect(rows[0]?.leaveCode).toBe("ALE");
    expect(rows[0]?.missingPunch).toBe(false);
    expect(rows[0]?.flag).toBe("leave");
    expect(rows[1]?.flag).toBe("leave");
    expect(rows[2]?.flag).toBe("ok");
    expect(rows[2]?.leaveCode).toBe("");
  });

  it("ngày công trống không mã nghỉ → Thiếu", () => {
    const rows = buildCalendar("2026-08-10", "2026-08-10", []);
    expect(rows[0]?.flag).toBe("missing");
    expect(rows[0]?.missingPunch).toBe(true);
    expect(rows[0]?.leaveCode).toBe("");
  });
});
