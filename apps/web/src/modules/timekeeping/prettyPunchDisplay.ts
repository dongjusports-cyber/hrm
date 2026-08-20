import { formatTimeHHMM } from "../../shared/formatDate";

/** Chỉ hiển thị lưới chấm công — không ghi DB, không đụng engine công/OT. */

const IN_START_MIN = 7 * 60 + 45;
const IN_SPAN_MIN = 15; // 07:45 … 08:00
const OUT_START_MIN = 17 * 60;
const OUT_SPAN_MIN = 15; // 17:00 … 17:15

export type PrettyPunchRow = {
  employee_code?: string;
  work_date?: string;
  first_in?: string | null;
  last_out?: string | null;
  late_minutes?: number | null;
  early_minutes?: number | null;
  source?: string | null;
};

/** FNV-1a 32-bit — cùng MSNV + ngày luôn ra cùng mốc. */
export function stableHash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function minToHhmm(totalMin: number): string {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/** Mốc đẹp cố định theo MSNV + ngày + vào/ra. */
export function prettySlotHhmm(employeeCode: string, workDate: string, slot: "in" | "out"): string {
  const start = slot === "in" ? IN_START_MIN : OUT_START_MIN;
  const span = slot === "in" ? IN_SPAN_MIN : OUT_SPAN_MIN;
  const n = stableHash(`${String(employeeCode).trim()}|${workDate}|${slot}`);
  return minToHhmm(start + (n % (span + 1)));
}

function isManualSource(source: string | null | undefined): boolean {
  const s = String(source ?? "").trim().toLowerCase();
  return s === "manual" || s === "import";
}

/**
 * Giờ Vào/Ra trên lưới. Công / trễ / sớm / OT lấy từ dữ liệu gốc, không dùng kết quả này.
 *
 * Làm đẹp khi: nguồn máy, đủ vào+ra, không trễ (cột Vào) / không về sớm (cột Ra).
 * OT vẫn làm đẹp cột Ra. HR sửa tay (`source=manual`) và thiếu mốc → giờ gốc.
 */
export function prettyPunchDisplay(
  row: PrettyPunchRow,
  opts: { showMachine?: boolean } = {},
): { inn: string; out: string } {
  const inn = formatTimeHHMM(row.first_in, "");
  const out = formatTimeHHMM(row.last_out, "");
  if (opts.showMachine || isManualSource(row.source) || !inn || !out) {
    return { inn, out };
  }
  const code = String(row.employee_code ?? "").trim();
  const date = String(row.work_date ?? "").trim();
  return {
    inn: (row.late_minutes ?? 0) > 0 ? inn : prettySlotHhmm(code, date, "in"),
    out: (row.early_minutes ?? 0) > 0 ? out : prettySlotHhmm(code, date, "out"),
  };
}
