import { describe, expect, it } from "vitest";
import { holidayOtMinutes, hoursToOtMinutes, weekendOtMinutes } from "./otDisplay";

describe("weekendOtMinutes", () => {
  it("CN sửa máy: ot_type weekend + 610 phút → 10.17h", () => {
    expect(
      weekendOtMinutes({ ot_type: "weekend", ot_minutes: 610, sunday_hours: "10.17" }),
    ).toBe(610);
  });

  it("falls back to sunday_hours", () => {
    expect(weekendOtMinutes({ sunday_hours: 4 })).toBe(240);
  });

  it("weekday has no CN OT", () => {
    expect(weekendOtMinutes({ ot_type: null, ot_minutes: 20, sunday_hours: 0 })).toBe(0);
  });
});

describe("holidayOtMinutes", () => {
  it("uses ot_minutes when holiday", () => {
    expect(holidayOtMinutes({ ot_type: "holiday", ot_minutes: 120, holiday_hours: 2 })).toBe(120);
  });

  it("falls back to holiday_hours", () => {
    expect(holidayOtMinutes({ holiday_hours: 8 })).toBe(480);
  });
});

describe("hoursToOtMinutes", () => {
  it("ignores empty", () => {
    expect(hoursToOtMinutes(0)).toBe(0);
    expect(hoursToOtMinutes(null)).toBe(0);
  });
});
