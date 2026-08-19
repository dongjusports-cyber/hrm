import { afterEach, describe, expect, it } from "vitest";
import {
  cacheClearAll,
  cacheInvalidate,
  cachePeek,
  cacheSet,
  cacheUpsertListItem,
  cachedFetch,
  employeesCacheKey,
} from "./clientCache";

afterEach(() => {
  cacheClearAll();
});

describe("clientCache", () => {
  it("peek / set trên RAM", () => {
    expect(cachePeek("k")).toBeUndefined();
    cacheSet("k", [1, 2]);
    expect(cachePeek<number[]>("k")).toEqual([1, 2]);
  });

  it("invalidate theo prefix", () => {
    cacheSet("employees:a", 1);
    cacheSet("employees:b", 2);
    cacheSet("payslips:x", 3);
    cacheInvalidate("employees:");
    expect(cachePeek("employees:a")).toBeUndefined();
    expect(cachePeek("employees:b")).toBeUndefined();
    expect(cachePeek("payslips:x")).toBe(3);
  });

  it("cachedFetch trả RAM tươi, không gọi loader lần 2", async () => {
    let n = 0;
    const a = await cachedFetch("t", async () => {
      n += 1;
      return "ok";
    });
    const b = await cachedFetch("t", async () => {
      n += 1;
      return "no";
    });
    expect(a).toBe("ok");
    expect(b).toBe("ok");
    expect(n).toBe(1);
  });

  it("upsert 1 phần tử, không tạo cache khi chưa có list", () => {
    cacheUpsertListItem("timesheets:2026-08", { id: "a", n: 1 }, (x: { id: string }) => x.id === "a");
    expect(cachePeek("timesheets:2026-08")).toBeUndefined();

    cacheSet("timesheets:2026-08", [
      { id: "a", n: 1 },
      { id: "b", n: 2 },
    ]);
    cacheUpsertListItem("timesheets:2026-08", { id: "b", n: 9 }, (x: { id: string }) => x.id === "b");
    expect(cachePeek("timesheets:2026-08")).toEqual([
      { id: "a", n: 1 },
      { id: "b", n: 9 },
    ]);
  });

  it("employeesCacheKey ổn định", () => {
    expect(employeesCacheKey()).toBe("employees:|||");
    expect(employeesCacheKey({ status: "all" })).toBe("employees:all|||");
  });
});
