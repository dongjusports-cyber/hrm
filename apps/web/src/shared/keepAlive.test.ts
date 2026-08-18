import { afterEach, describe, expect, it } from "vitest";
import {
  activateKeepAlive,
  deactivateKeepAliveIf,
  getKeepAliveState,
  resetKeepAlive,
} from "./keepAlive";

afterEach(() => {
  resetKeepAlive();
});

describe("keepAlive store", () => {
  it("giữ pane đã vào, ẩn khi rời route", () => {
    activateKeepAlive("hr-lists", {
      pathname: "/m/hr/lists/all",
      search: "",
      params: { filterKey: "all" },
    });
    expect(getKeepAliveState().current).toBe("hr-lists");
    expect(getKeepAliveState().visited).toEqual(["hr-lists"]);

    deactivateKeepAliveIf("hr-lists");
    expect(getKeepAliveState().current).toBeNull();
    expect(getKeepAliveState().visited).toEqual(["hr-lists"]);
    expect(getKeepAliveState().snaps["hr-lists"]?.params.filterKey).toBe("all");
  });

  it("đổi giữa 3 lưới không xóa visited", () => {
    activateKeepAlive("hr-lists", {
      pathname: "/m/hr/lists/all",
      search: "",
      params: { filterKey: "all" },
    });
    activateKeepAlive("timekeeping", { pathname: "/m/timekeeping", search: "", params: {} });
    expect(getKeepAliveState().current).toBe("timekeeping");
    expect(getKeepAliveState().visited).toEqual(["hr-lists", "timekeeping"]);
  });

  it("đổi filterKey khi đang ở lưới NV", () => {
    activateKeepAlive("hr-lists", {
      pathname: "/m/hr/lists/all",
      search: "",
      params: { filterKey: "all" },
    });
    activateKeepAlive("hr-lists", {
      pathname: "/m/hr/lists/special_regime",
      search: "",
      params: { filterKey: "special_regime" },
    });
    expect(getKeepAliveState().visited).toEqual(["hr-lists"]);
    expect(getKeepAliveState().snaps["hr-lists"]?.params.filterKey).toBe("special_regime");
  });

  it("reset khi đăng xuất", () => {
    activateKeepAlive("payroll", { pathname: "/m/payroll", search: "", params: {} });
    resetKeepAlive();
    expect(getKeepAliveState()).toEqual({ current: null, visited: [], snaps: {} });
  });
});
