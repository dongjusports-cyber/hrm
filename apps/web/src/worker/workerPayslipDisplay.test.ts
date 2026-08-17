import { describe, expect, it } from "vitest";
import { formatWorkerQty } from "./workerPayslipDisplay";

describe("formatWorkerQty", () => {
  it("null / rỗng → —", () => {
    expect(formatWorkerQty(null)).toBe("—");
    expect(formatWorkerQty(undefined)).toBe("—");
    expect(formatWorkerQty("")).toBe("—");
  });

  it("giữ phần thập phân ngày/giờ, không làm tròn thành số nguyên", () => {
    expect(formatWorkerQty("23.04")).toBe("23,04");
    expect(formatWorkerQty(23.0375)).toBe("23,04");
    expect(formatWorkerQty(6.5)).toBe("6,5");
    expect(formatWorkerQty(26)).toBe("26");
    expect(formatWorkerQty(0)).toBe("0");
  });
});
