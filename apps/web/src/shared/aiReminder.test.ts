import { describe, expect, it } from "vitest";
import { aiFabBadgeCount } from "./aiReminder";

describe("aiFabBadgeCount", () => {
  it("cộng alert chưa đọc + số thẻ todo rule-based", () => {
    expect(aiFabBadgeCount(9, 1)).toBe(10);
    expect(aiFabBadgeCount(0, 354)).toBe(354);
    expect(aiFabBadgeCount(0, 0)).toBe(0);
  });
});
