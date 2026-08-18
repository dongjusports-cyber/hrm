import { afterEach, describe, expect, it } from "vitest";
import {
  cacheClearAll,
  cacheInvalidate,
  cachePeek,
  cacheSet,
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

  it("employeesCacheKey ổn định", () => {
    expect(employeesCacheKey()).toBe("employees:|||");
    expect(employeesCacheKey({ status: "all" })).toBe("employees:all|||");
  });
});
