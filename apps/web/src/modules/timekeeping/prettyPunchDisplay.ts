/** Chỉ hiển thị lưới chấm công — không ghi DB, không đụng engine công/OT. */

const IN_START_MIN = 7 * 60 + 45;
const IN_SPAN_MIN = 15; // 07:45 … 08:00
const OUT_START_MIN = 17 * 60;
const OUT_SPAN_MIN = 15; // 17:00 … 17:15
const SHIFT_START = "08:00";
const SHIFT_END = "17:00";
const VN_MS = 7 * 60 * 60 * 1000;

export type PrettyPunchRow = {
  employee_code?: string;
  work_date?: string;
  first_in?: string | null;
  last_out?: string | null;
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

/** HH:mm VN từ ISO — không dùng toLocaleTimeString (chậm trên lưới). */
export function isoToHhmm(iso: string | null | undefined): string {
  if (iso == null || iso === "") return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const vn = new Date(d.getTime() + VN_MS);
  const hh = String(vn.getUTCHours()).padStart(2, "0");
  const mm = String(vn.getUTCMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

/** Mốc đẹp cố định theo MSNV + ngày + vào/ra. */
export function prettySlotHhmm(employeeCode: string, workDate: string, slot: "in" | "out"): string {
  const start = slot === "in" ? IN_START_MIN : OUT_START_MIN;
  const span = slot === "in" ? IN_SPAN_MIN : OUT_SPAN_MIN;
  const n = stableHash(`${String(employeeCode).trim()}|${workDate}|${slot}`);
  return minToHhmm(start + (n % (span + 1)));
}

/**
 * Giờ Vào/Ra trên lưới. Công / trễ / sớm / OT lấy từ dữ liệu gốc.
 *
 * Vào ≤ 08:00 → 07:45–08:00. Ra ≥ 17:00 (kể cả OT) → 17:00–17:15.
 * Mỗi cột độc lập (thiếu mốc kia vẫn làm đẹp mốc có). Trễ / về sớm giữ giờ máy.
 */
export function prettyPunchDisplay(
  row: PrettyPunchRow,
  opts: { showMachine?: boolean } = {},
): { inn: string; out: string } {
  const inn = isoToHhmm(row.first_in);
  const out = isoToHhmm(row.last_out);
  if (opts.showMachine) return { inn, out };
  const code = String(row.employee_code ?? "").trim();
  const date = String(row.work_date ?? "").trim();
  return {
    inn: inn && inn <= SHIFT_START ? prettySlotHhmm(code, date, "in") : inn,
    out: out && out >= SHIFT_END ? prettySlotHhmm(code, date, "out") : out,
  };
}
