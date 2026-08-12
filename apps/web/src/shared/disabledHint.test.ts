import { describe, expect, it } from "vitest";
import { disabledTitle } from "./disabledHint";

describe("disabledTitle", () => {
  it("trả lý do khi disabled", () => {
    expect(disabledTitle(true, "Chọn dòng trước")).toBe("Chọn dòng trước");
  });

  it("undefined khi enabled", () => {
    expect(disabledTitle(false, "Chọn dòng trước")).toBeUndefined();
  });
});
