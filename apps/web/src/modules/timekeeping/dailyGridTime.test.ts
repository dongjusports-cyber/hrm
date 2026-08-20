import { describe, expect, it } from "vitest";
import {
  buildDayTimePatch,
  formatWorkedHours,
  outTimeAfterWorkedHours,
  parseGridTimeInput,
  parseWorkedHoursInput,
  planQuickHours,
  previewShiftWorkedHours,
  toIsoTime,
} from "./dailyGridTime";

describe("parseGridTimeInput", () => {
  it("keeps HH:mm", () => {
    expect(parseGridTimeInput("08:00")).toBe("08:00");
  });

  it("normalizes 9:10 and 910", () => {
    expect(parseGridTimeInput("9:10")).toBe("09:10");
    expect(parseGridTimeInput("910")).toBe("09:10");
    expect(parseGridTimeInput("7:44")).toBe("07:44");
  });

  it("rejects garbage", () => {
    expect(parseGridTimeInput("abc")).toBeNull();
    expect(parseGridTimeInput("99:99")).toBeNull();
  });
});

describe("toIsoTime", () => {
  it("builds VN ISO", () => {
    expect(toIsoTime("2026-08-17", "08:00")).toBe("2026-08-17T08:00:00+07:00");
    expect(toIsoTime("2026-08-17", "800")).toBe("2026-08-17T08:00:00+07:00");
  });
});

describe("buildDayTimePatch", () => {
  it("saves one punch when the other cell is empty", () => {
    const r = buildDayTimePatch({
      workDate: "2026-08-17",
      col: "first_in",
      editedRaw: "800",
      existingInHHmm: "",
      existingOutHHmm: "",
    });
    expect(r).toEqual({
      ok: true,
      first_in: "2026-08-17T08:00:00+07:00",
      last_out: undefined,
    });
  });

  it("keeps the other punch when editing one cell", () => {
    const r = buildDayTimePatch({
      workDate: "2026-08-17",
      col: "last_out",
      editedRaw: "17:30",
      existingInHHmm: "08:00",
      existingOutHHmm: "17:00",
    });
    expect(r).toEqual({
      ok: true,
      first_in: "2026-08-17T08:00:00+07:00",
      last_out: "2026-08-17T17:30:00+07:00",
    });
  });

  it("errors on invalid time instead of silent skip", () => {
    const r = buildDayTimePatch({
      workDate: "2026-08-17",
      col: "first_in",
      editedRaw: "abc",
      existingInHHmm: "",
      existingOutHHmm: "",
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).toMatch(/08:00/);
  });

  it("empty cell clears that punch and keeps the other", () => {
    const r = buildDayTimePatch({
      workDate: "2026-08-17",
      col: "first_in",
      editedRaw: "   ",
      existingInHHmm: "06:13",
      existingOutHHmm: "17:00",
    });
    expect(r).toEqual({ ok: true, clear_first_in: true });
  });

  it("empty cell with no other punch clears the day", () => {
    const r = buildDayTimePatch({
      workDate: "2026-08-17",
      col: "last_out",
      editedRaw: "",
      existingInHHmm: "",
      existingOutHHmm: "17:10",
    });
    expect(r).toEqual({ ok: true, clear_times: true });
  });
});

describe("previewShiftWorkedHours / outTimeAfterWorkedHours", () => {
  it("clamps 07:44–09:10 to 1.1667 hours (08:00–09:10)", () => {
    expect(previewShiftWorkedHours("07:44", "09:10")).toBeCloseTo(70 / 60, 5);
    expect(formatWorkedHours(70 / 60)).toBe("1.1667");
  });

  it("full day 08:00–17:00 is 8h after lunch", () => {
    expect(previewShiftWorkedHours("08:00", "17:00")).toBe(8);
    expect(outTimeAfterWorkedHours("07:44", 8)).toBe("17:00");
    expect(outTimeAfterWorkedHours("08:00", 4)).toBe("12:00");
  });

  it("hours input 1,17 fills 09:10 from morning in", () => {
    expect(parseWorkedHoursInput("1,17")).toBeCloseTo(1.17, 5);
    expect(outTimeAfterWorkedHours("07:44", 1.1667)).toBe("09:10");
    expect(toIsoTime("2026-08-19", "9:10")).toBe("2026-08-19T09:10:00+07:00");
  });
});

describe("planQuickHours", () => {
  it("8h từ sáng → 08:00–17:00", () => {
    expect(planQuickHours("8", "")).toEqual({ inn: "08:00", out: "17:00", hoursLabel: "8" });
    expect(planQuickHours("8", "07:55")).toEqual({ inn: "07:55", out: "17:00", hoursLabel: "8" });
  });

  it("4h → 08:00–12:00", () => {
    expect(planQuickHours("4", "")).toEqual({ inn: "08:00", out: "12:00", hoursLabel: "4" });
  });

  it("ô trống hoặc >8 → không gán", () => {
    expect(planQuickHours("", "08:00")).toBeNull();
    expect(planQuickHours("9", "08:00")).toBeNull();
  });
});
