import { describe, expect, it } from "vitest";
import { employeeMatchesQuery, findEmployeeByQuery } from "./employeeSearch";

const rows = [
  { employee_code: "1514", full_name: "Nguyễn Văn A" },
  { employee_code: "1519", full_name: "Trần Thị B" },
  { employee_code: "5290", full_name: "Lê Văn C" },
];

describe("employeeMatchesQuery", () => {
  it("empty query matches all", () => {
    expect(rows.every((r) => employeeMatchesQuery(r, " "))).toBe(true);
  });

  it("matches MSNV substring", () => {
    expect(employeeMatchesQuery(rows[2], "529")).toBe(true);
    expect(employeeMatchesQuery(rows[0], "529")).toBe(false);
  });

  it("matches name case-insensitive", () => {
    expect(employeeMatchesQuery(rows[0], "nguyễn")).toBe(true);
  });
});

describe("findEmployeeByQuery", () => {
  it("prefers exact MSNV over prefix", () => {
    expect(findEmployeeByQuery(rows, "1514")?.employee_code).toBe("1514");
  });

  it("falls back to prefix then first filtered", () => {
    expect(findEmployeeByQuery(rows, "15")?.employee_code).toBe("1514");
    expect(findEmployeeByQuery(rows, "thị b")?.employee_code).toBe("1519");
  });

  it("exactOnly skips fuzzy", () => {
    expect(findEmployeeByQuery(rows, "15", { exactOnly: true })).toBeUndefined();
  });
});
