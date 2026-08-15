import { describe, expect, it } from "vitest";
import { formatOtHours } from "./formatOtHours";

describe("formatOtHours", () => {
  it("phút → giờ, bỏ 0 thừa, hậu tố h (bảng spec Bước B)", () => {
    expect(formatOtHours(90)).toBe("1.5h");
    expect(formatOtHours(50)).toBe("0.83h");
    expect(formatOtHours(45)).toBe("0.75h");
    expect(formatOtHours(30)).toBe("0.5h");
    expect(formatOtHours(66)).toBe("1.1h");
    expect(formatOtHours(120)).toBe("2h");
    expect(formatOtHours(480)).toBe("8h");
    expect(formatOtHours(600)).toBe("10h"); // không bị cắt thành 1h
    expect(formatOtHours(1200)).toBe("20h");
  });

  it("0 · null · âm → rỗng", () => {
    expect(formatOtHours(0)).toBe("");
    expect(formatOtHours(null)).toBe("");
    expect(formatOtHours(undefined)).toBe("");
    expect(formatOtHours(-30)).toBe("");
  });

  it("tham số empty tuỳ biến khi <= 0 / null", () => {
    expect(formatOtHours(0, "—")).toBe("—");
    expect(formatOtHours(null, "—")).toBe("—");
  });

  it("giá trị giờ dùng chung bằng cách × 60", () => {
    expect(formatOtHours(2.5 * 60)).toBe("2.5h");
    expect(formatOtHours(8 * 60)).toBe("8h");
  });
});
