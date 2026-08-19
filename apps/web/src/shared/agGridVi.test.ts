import { describe, expect, it } from "vitest";
import { compareViAz } from "./agGridVi";

describe("compareViAz", () => {
  it("A→Z tiếng Việt: Đ sau D, trước E — không đẩy Đ xuống cuối Unicode", () => {
    expect(compareViAz("Dũng", "Đặng")).toBeLessThan(0);
    expect(compareViAz("Đặng", "Em")).toBeLessThan(0);
    expect(compareViAz("Đặng", "Zzz")).toBeLessThan(0);
  });

  it("Ă / Â đứng gần A, không sau Z", () => {
    expect(compareViAz("An", "Ăn")).toBeLessThan(0);
    expect(compareViAz("Ăn", "Bình")).toBeLessThan(0);
    expect(compareViAz("Âu", "Zzz")).toBeLessThan(0);
  });

  it("MSNV có số: DJ2 trước DJ10", () => {
    expect(compareViAz("DJ2", "DJ10")).toBeLessThan(0);
  });

  it("ô trống đứng cuối khi A→Z", () => {
    expect(compareViAz("", "An", undefined, undefined, false)).toBeGreaterThan(0);
    expect(compareViAz(null, "An", undefined, undefined, false)).toBeGreaterThan(0);
  });

  it("số so sánh số", () => {
    expect(compareViAz(2, 10)).toBeLessThan(0);
    expect(compareViAz(8, 1.5)).toBeGreaterThan(0);
  });

  it("Vào/Ra HH:mm — trống cuối, 08:00 trước 17:00", () => {
    expect(compareViAz("", "08:00", undefined, undefined, false)).toBeGreaterThan(0);
    expect(compareViAz("08:00", "17:00")).toBeLessThan(0);
    expect(compareViAz("7:00", "08:00")).toBeLessThan(0);
  });
});
