import { describe, expect, it } from "vitest";
import { buildDayTimePatch, parseGridTimeInput, toIsoTime } from "./dailyGridTime";

describe("parseGridTimeInput", () => {
  it("keeps HH:mm", () => {
    expect(parseGridTimeInput("08:00")).toBe("08:00");
  });

  it("normalizes 800 and 735", () => {
    expect(parseGridTimeInput("800")).toBe("08:00");
    expect(parseGridTimeInput("735")).toBe("07:35");
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
