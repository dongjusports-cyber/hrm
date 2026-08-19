import { describe, expect, it } from "vitest";
import { formatOrgColumnCell, orgColumnHeader, sortByViName, type OrgListFilter } from "./formatOrg";

describe("formatOrgColumnCell", () => {
  const row = {
    deptName: "Main office",
    deptCode: "MO",
    teamName: "IT",
    teamCode: "IT1",
  };

  it("bộ phận + tất cả tổ → chỉ hiện bộ phận", () => {
    const filter: OrgListFilter = { departmentId: "dept-mo", teamId: "" };
    expect(
      formatOrgColumnCell(row.deptName, row.deptCode, row.teamName, row.teamCode, filter),
    ).toBe("Main office");
  });

  it("bộ phận + một tổ → chỉ hiện tổ", () => {
    const filter: OrgListFilter = { departmentId: "dept-mo", teamId: "team-it" };
    expect(
      formatOrgColumnCell(row.deptName, row.deptCode, row.teamName, row.teamCode, filter),
    ).toBe("IT");
  });

  it("tất cả bộ phận → hiện bộ phận từng dòng", () => {
    const filter: OrgListFilter = { departmentId: "", teamId: "" };
    expect(
      formatOrgColumnCell(row.deptName, row.deptCode, row.teamName, row.teamCode, filter),
    ).toBe("Main office");
  });
});

describe("orgColumnHeader", () => {
  it("đã chọn tổ → tiêu đề Tổ", () => {
    expect(orgColumnHeader({ departmentId: "d1", teamId: "t1" })).toBe("Tổ");
  });

  it("chưa chọn tổ → tiêu đề Bộ phận", () => {
    expect(orgColumnHeader({ departmentId: "d1", teamId: "" })).toBe("Bộ phận");
    expect(orgColumnHeader({ departmentId: "", teamId: "" })).toBe("Bộ phận");
  });
});

describe("sortByViName", () => {
  it("A→Z tiếng Việt: Đ không nhảy xuống cuối", () => {
    const rows = [{ name: "Đóng gói" }, { name: "Cắt" }, { name: "01 May" }];
    expect(sortByViName(rows).map((r) => r.name)).toEqual(["Cắt", "Đóng gói", "01 May"]);
  });
});
