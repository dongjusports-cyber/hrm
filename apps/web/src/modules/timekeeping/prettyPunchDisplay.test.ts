import { describe, expect, it } from "vitest";
import { prettyPunchDisplay, prettySlotHhmm, stableHash } from "./prettyPunchDisplay";

function hhmmInRange(hhmm: string, start: string, end: string) {
  expect(hhmm >= start && hhmm <= end).toBe(true);
}

const onTime = {
  employee_code: "5290",
  work_date: "2026-08-20",
  first_in: "2026-08-20T07:02:00+07:00",
  last_out: "2026-08-20T17:03:00+07:00",
  late_minutes: 0,
  early_minutes: 0,
  source: "machine",
};

describe("prettySlotHhmm", () => {
  it("cùng MSNV + ngày → cùng mốc", () => {
    expect(prettySlotHhmm("5290", "2026-08-20", "in")).toBe(
      prettySlotHhmm("5290", "2026-08-20", "in"),
    );
    expect(prettySlotHhmm("5290", "2026-08-20", "out")).toBe(
      prettySlotHhmm("5290", "2026-08-20", "out"),
    );
  });

  it("nằm trong 07:45–08:00 và 17:00–17:15", () => {
    for (let i = 1000; i < 1120; i++) {
      hhmmInRange(prettySlotHhmm(String(i), "2026-08-20", "in"), "07:45", "08:00");
      hhmmInRange(prettySlotHhmm(String(i), "2026-08-20", "out"), "17:00", "17:15");
    }
  });

  it("người khác ngày khác → hash khác (thường ra mốc khác)", () => {
    expect(stableHash("1514|2026-08-20|in")).not.toBe(stableHash("5290|2026-08-20|in"));
    const ins = new Set(
      ["1514", "1643", "5290", "9999", "1001"].map((c) => prettySlotHhmm(c, "2026-08-20", "in")),
    );
    expect(ins.size).toBeGreaterThan(1);
  });
});

describe("prettyPunchDisplay", () => {
  it("làm đẹp người đúng giờ — không phụ thuộc giờ máy", () => {
    const a = prettyPunchDisplay(onTime);
    const b = prettyPunchDisplay({
      ...onTime,
      first_in: "2026-08-20T07:50:00+07:00",
      last_out: "2026-08-20T17:12:00+07:00",
    });
    expect(a.inn).toBe(b.inn);
    expect(a.out).toBe(b.out);
    hhmmInRange(a.inn, "07:45", "08:00");
    hhmmInRange(a.out, "17:00", "17:15");
    expect(a.inn).not.toBe("07:02");
    expect(a.out).not.toBe("17:03");
  });

  it("OT vẫn làm đẹp Ra; Trễ/Sớm giữ giờ máy", () => {
    const ot = prettyPunchDisplay({
      ...onTime,
      last_out: "2026-08-20T20:00:00+07:00",
    });
    hhmmInRange(ot.out, "17:00", "17:15");

    const late = prettyPunchDisplay({
      ...onTime,
      first_in: "2026-08-20T08:15:00+07:00",
      late_minutes: 15,
    });
    expect(late.inn).toBe("08:15");
    hhmmInRange(late.out, "17:00", "17:15");

    const early = prettyPunchDisplay({
      ...onTime,
      last_out: "2026-08-20T16:30:00+07:00",
      early_minutes: 30,
    });
    hhmmInRange(early.inn, "07:45", "08:00");
    expect(early.out).toBe("16:30");
  });

  it("thiếu mốc / HR sửa tay / Hiện giờ máy → giờ gốc", () => {
    expect(
      prettyPunchDisplay({
        ...onTime,
        last_out: null,
      }),
    ).toEqual({ inn: "07:02", out: "" });

    expect(prettyPunchDisplay({ ...onTime, source: "manual" })).toEqual({
      inn: "07:02",
      out: "17:03",
    });

    expect(prettyPunchDisplay(onTime, { showMachine: true })).toEqual({
      inn: "07:02",
      out: "17:03",
    });
  });

  it("ca đặc biệt (Cooker 06:00) vẫn làm đẹp khi không trễ/sớm", () => {
    const cooker = prettyPunchDisplay({
      ...onTime,
      first_in: "2026-08-20T06:00:00+07:00",
    });
    hhmmInRange(cooker.inn, "07:45", "08:00");
    expect(cooker.inn).not.toBe("06:00");
  });
});
