/** Tên file Excel.
 *  Lương / OT / KPI / chu kỳ: 08.2026 theo kỳ.
 *  Danh sách NV: 20.08.2026 ngày bấm xuất (giờ VN).
 */

import { todayIsoDateVN } from "./formatDate";

export const COMPANY_EXCEL_SUFFIX = "công ty Dongju Sports VN";

export function excelMonthYearTag(period?: string, ref: Date = new Date()): string {
  const src = (period && period.trim()) || todayIsoDateVN(ref).slice(0, 7);
  const [year, month] = src.split("-");
  if (!year || !month) return src;
  return `${String(Number(month)).padStart(2, "0")}.${year}`;
}

export function excelExportDayTag(ref: Date = new Date()): string {
  const [year, month, day] = todayIsoDateVN(ref).split("-");
  return `${day}.${month}.${year}`;
}

export function companyExcelFilename(
  label: string,
  opts: { period?: string; extra?: string; onExportDay?: boolean; asOf?: Date } = {},
): string {
  const stamp =
    opts.onExportDay || opts.asOf
      ? excelExportDayTag(opts.asOf ?? new Date())
      : excelMonthYearTag(opts.period);
  const parts = [label.trim(), stamp];
  if (opts.extra?.trim()) parts.push(opts.extra.trim());
  parts.push(COMPANY_EXCEL_SUFFIX);
  return `${parts.join(" ")}.xlsx`;
}

export function filenameFromContentDisposition(
  header: string | null | undefined,
  fallback: string,
): string {
  if (!header) return fallback;
  const star = /filename\*=(?:UTF-8''|utf-8'')([^;]+)/i.exec(header);
  if (star) {
    try {
      return decodeURIComponent(star[1].trim().replace(/^"(.*)"$/, "$1"));
    } catch {
      /* dùng fallback / filename= */
    }
  }
  const quoted = /filename="([^"]+)"/.exec(header);
  if (quoted) return quoted[1];
  const plain = /filename=([^;]+)/.exec(header);
  if (plain) return plain[1].trim();
  return fallback;
}
