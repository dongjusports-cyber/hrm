import { isTimesheetExportHref, parseTimesheetSearch } from "./timesheetUrl";

describe("parseTimesheetSearch", () => {
  it("đọc view, kỳ, bộ phận, MSNV", () => {
    const s = parseTimesheetSearch(
      "?view=monthly&period=2026-08&dept=SW1&q=5290",
    );
    expect(s.view).toBe("monthly");
    expect(s.period).toBe("2026-08");
    expect(s.deptCode).toBe("SW1");
    expect(s.q).toBe("5290");
    expect(s.print).toBe(false);
  });

  it("nhận emp= như q= và print=1", () => {
    const s = parseTimesheetSearch("view=daily&emp=1514&print=1&date=2026-08-19");
    expect(s.view).toBe("daily");
    expect(s.q).toBe("1514");
    expect(s.print).toBe(true);
    expect(s.date).toBe("2026-08-19");
  });

  it("bỏ period/date sai dạng", () => {
    const s = parseTimesheetSearch("?view=leave&period=8&date=19-08");
    expect(s.view).toBe("leave");
    expect(s.period).toBeNull();
    expect(s.date).toBeNull();
  });
});

describe("isTimesheetExportHref", () => {
  it("nhận đường Excel bảng công", () => {
    expect(isTimesheetExportHref("/api/attendance/timesheets/2026-08/export")).toBe(true);
    expect(isTimesheetExportHref("/m/timekeeping?view=monthly")).toBe(false);
  });
});
