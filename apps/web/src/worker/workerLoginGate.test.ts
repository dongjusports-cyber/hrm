// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { getWorkerDeviceId } from "./workerDevice";
import { getWorkerPhoneLock, phoneLockBlocksOtherMsnv, rememberWorkerPhoneLock, setWorkerPhoneLock } from "./workerPhoneLock";
import { workerLoginGate } from "./workerLoginGate";

describe("workerLoginGate", () => {
  it("leftover token must confirm identity, never silent enter", () => {
    expect(workerLoginGate("jwt-from-previous-worker")).toBe("confirm-session");
  });

  it("empty session shows the credential form", () => {
    expect(workerLoginGate(null)).toBe("credentials");
    expect(workerLoginGate("")).toBe("credentials");
    expect(workerLoginGate(undefined)).toBe("credentials");
  });
});

describe("workerDevice", () => {
  it("keeps the same id across reads", () => {
    localStorage.clear();
    const a = getWorkerDeviceId();
    const b = getWorkerDeviceId();
    expect(a.length).toBeGreaterThanOrEqual(8);
    expect(b).toBe(a);
  });

  it("đăng xuất không đổi mã máy", () => {
    localStorage.clear();
    const id = getWorkerDeviceId();
    localStorage.removeItem("djhrm_worker_auth");
    expect(getWorkerDeviceId()).toBe(id);
  });

  it("xóa localStorage vẫn lấy lại mã máy từ cookie", () => {
    localStorage.clear();
    const id = getWorkerDeviceId();
    localStorage.removeItem("djhrm_worker_device_id");
    expect(getWorkerDeviceId()).toBe(id);
  });
});

describe("workerPhoneLock", () => {
  it("blocks a different MSNV on the same phone", () => {
    localStorage.clear();
    setWorkerPhoneLock({ employee_code: "5290", full_name: "A" });
    const lock = getWorkerPhoneLock();
    expect(lock?.employee_code).toBe("5290");
    expect(phoneLockBlocksOtherMsnv("1514", lock)).toBe(true);
    expect(phoneLockBlocksOtherMsnv("5290", lock)).toBe(false);
  });

  it("rememberWorkerPhoneLock keeps MSNV after logout payload", () => {
    localStorage.clear();
    rememberWorkerPhoneLock({ employee_code: "1732", full_name: "B" });
    expect(getWorkerPhoneLock()?.employee_code).toBe("1732");
  });
});
