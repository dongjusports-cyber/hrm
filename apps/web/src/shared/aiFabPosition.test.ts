import { describe, expect, it } from "vitest";
import {
  clampFabPosition,
  computePanelBox,
  defaultFabPosition,
  isFabOverGridZone,
  loadFabPosition,
  nudgeFabFromGrid,
} from "./aiFabPosition";

describe("clampFabPosition", () => {
  it("giữ nút trong khung màn hình", () => {
    expect(clampFabPosition(-100, 10, 800, 600)).toEqual({ left: 12, top: 12 });
    expect(clampFabPosition(900, 700, 800, 600)).toEqual({ left: 732, top: 532 });
  });
});

describe("defaultFabPosition", () => {
  it("mặc định góc phải dưới", () => {
    expect(defaultFabPosition(800, 600)).toEqual({ left: 732, top: 532 });
  });
});

describe("loadFabPosition", () => {
  it("không có lưu → góc phải dưới", () => {
    expect(loadFabPosition(800, 600)).toEqual({ left: 732, top: 532 });
  });
});

describe("isFabOverGridZone", () => {
  it("FAB góc dưới phải → không che lưới", () => {
    expect(isFabOverGridZone({ left: 732, top: 532 }, 800, 600)).toBe(false);
  });

  it("FAB giữa trái → che lưới", () => {
    expect(isFabOverGridZone({ left: 120, top: 200 }, 800, 600)).toBe(true);
  });
});

describe("nudgeFabFromGrid", () => {
  it("đẩy về góc dưới phải khi đè lưới", () => {
    expect(nudgeFabFromGrid({ left: 120, top: 200 }, 800, 600)).toEqual({
      left: 732,
      top: 532,
    });
  });

  it("giữ vị trí khi không đè lưới", () => {
    expect(nudgeFabFromGrid({ left: 700, top: 500 }, 800, 600)).toEqual({
      left: 700,
      top: 500,
    });
  });
});

describe("computePanelBox", () => {
  it("FAB góc trên phải → panel vẫn trong màn, không âm top", () => {
    const box = computePanelBox({ left: 732, top: 12 }, 800, 600);
    expect(box.top).toBeGreaterThanOrEqual(12);
    expect(box.left).toBeGreaterThanOrEqual(12);
    expect(box.left + box.width).toBeLessThanOrEqual(800 - 12);
    expect(box.top + Math.min(280, box.maxHeight)).toBeLessThanOrEqual(600);
  });

  it("FAB góc dưới phải → panel mở lên/trái trong khung", () => {
    const box = computePanelBox({ left: 732, top: 532 }, 800, 600);
    expect(box.top).toBeGreaterThanOrEqual(12);
    expect(box.left + box.width).toBeLessThanOrEqual(788);
  });
});
