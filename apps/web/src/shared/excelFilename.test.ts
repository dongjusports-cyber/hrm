import { describe, expect, it } from "vitest";
import {
  companyExcelFilename,
  excelMonthYearTag,
  filenameFromContentDisposition,
} from "./excelFilename";

describe("excelMonthYearTag", () => {
  it("kỳ YYYY-MM → mm.yyyy", () => {
    expect(excelMonthYearTag("2026-08")).toBe("08.2026");
    expect(excelMonthYearTag("2026-09")).toBe("09.2026");
    expect(excelMonthYearTag("2026-10")).toBe("10.2026");
  });
});

describe("companyExcelFilename", () => {
  it("lương / OT theo tháng kỳ", () => {
    expect(companyExcelFilename("Lương", { period: "2026-08" })).toBe(
      "Lương 08.2026 công ty Dongju Sports VN.xlsx",
    );
    expect(companyExcelFilename("Lương", { period: "2026-09" })).toBe(
      "Lương 09.2026 công ty Dongju Sports VN.xlsx",
    );
    expect(companyExcelFilename("OT", { period: "2026-10" })).toBe(
      "OT 10.2026 công ty Dongju Sports VN.xlsx",
    );
  });

  it("xuất khác vẫn đuôi công ty", () => {
    expect(companyExcelFilename("KPI", { period: "2026-08" })).toBe(
      "KPI 08.2026 công ty Dongju Sports VN.xlsx",
    );
    expect(companyExcelFilename("KPI", { period: "2026-09" })).toBe(
      "KPI 09.2026 công ty Dongju Sports VN.xlsx",
    );
    expect(companyExcelFilename("Chu kỳ", { period: "2026-08" })).toBe(
      "Chu kỳ 08.2026 công ty Dongju Sports VN.xlsx",
    );
    expect(companyExcelFilename("Chu kỳ", { period: "2026-09" })).toBe(
      "Chu kỳ 09.2026 công ty Dongju Sports VN.xlsx",
    );
    expect(
      companyExcelFilename("Danh sách nhân viên", {
        asOf: new Date("2026-08-20T10:00:00+07:00"),
      }),
    ).toBe("Danh sách nhân viên 20.08.2026 công ty Dongju Sports VN.xlsx");
    expect(
      companyExcelFilename("Danh sách nhân viên", {
        asOf: new Date("2026-08-22T10:00:00+07:00"),
      }),
    ).toBe("Danh sách nhân viên 22.08.2026 công ty Dongju Sports VN.xlsx");
  });
});

describe("filenameFromContentDisposition", () => {
  it("ưu tiên filename*", () => {
    const name = companyExcelFilename("Lương", { period: "2026-08" });
    const header = `attachment; filename="Luong.xlsx"; filename*=UTF-8''${encodeURIComponent(name)}`;
    expect(filenameFromContentDisposition(header, "x.xlsx")).toBe(name);
  });
});
