import { describe, expect, it } from "vitest";
import { formatDateDDMMYYYY, formatDateTimeDDMMYYYY, formatTimeHHMM, currentPayPeriod, payPeriodDateBounds } from "./formatDate";

describe("formatTimeHHMM", () => {
  it("UTC punch → giờ VN (+7)", () => {
    expect(formatTimeHHMM("2026-08-07T00:52:01+00:00")).toBe("07:52");
    expect(formatTimeHHMM("2026-08-07T17:09:00+00:00")).toBe("00:09"); // next day VN? 17+7=24 -> 00:09 next day
  });

  it("null/empty → —", () => {
    expect(formatTimeHHMM(null)).toBe("—");
    expect(formatTimeHHMM("", "—")).toBe("—");
    expect(formatTimeHHMM(undefined, "")).toBe("");
  });
});

describe("currentPayPeriod", () => {
  it("trả YYYY-MM theo tham chiếu", () => {
    expect(currentPayPeriod(new Date(2026, 7, 12))).toBe("2026-08");
    expect(currentPayPeriod(new Date(2025, 9, 1))).toBe("2025-10");
  });
});

describe("payPeriodDateBounds", () => {
  it("tháng 8 → 01..31", () => {
    expect(payPeriodDateBounds("2026-08")).toEqual({
      date_from: "2026-08-01",
      date_to: "2026-08-31",
    });
  });

  it("tháng 2 nhuận", () => {
    expect(payPeriodDateBounds("2024-02").date_to).toBe("2024-02-29");
  });
});

describe("formatDateTimeDDMMYYYY", () => {
  it("giữ giờ từ ISO datetime (sync_jobs, punch_time)", () => {
    const out = formatDateTimeDDMMYYYY("2026-08-12T07:56:05.089637+00:00");
    expect(out).not.toMatch(/00:00$/);
    expect(out).toMatch(/^12\/08\/2026 \d{2}:\d{2}$/);
  });

  it("date-only vẫn dd/mm/yyyy", () => {
    expect(formatDateDDMMYYYY("2026-08-12")).toBe("12/08/2026");
  });
});
