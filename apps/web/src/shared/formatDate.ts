/**
 * Định dạng ngày chuẩn DJ HRM: dd/mm/yyyy (luôn có số 0 đầu).
 */

function parseInput(v: string | Date): Date | null {
  if (v instanceof Date) {
    return Number.isNaN(v.getTime()) ? null : v;
  }
  const s = v.trim();
  // ISO datetime (2026-08-12T14:56:05+07:00) — phải giữ giờ; regex date-only làm mất → 00:00
  if (s.includes("T") || /:\d{2}/.test(s)) {
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (iso) {
    const d = new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** dd/mm/yyyy — dùng cho mọi ngày hiển thị trên UI. */
export function formatDateDDMMYYYY(v: string | Date | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const d = typeof v === "string" || v instanceof Date ? parseInput(v) : null;
  if (!d) return String(v);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()}`;
}

/** dd/mm/yyyy HH:mm — nhật ký, vi phạm, audit. */
export function formatDateTimeDDMMYYYY(v: string | Date | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const d = typeof v === "string" || v instanceof Date ? parseInput(v) : null;
  if (!d) return String(v);
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${formatDateDDMMYYYY(d)} ${hh}:${mi}`;
}

const VN_TZ = "Asia/Ho_Chi_Minh";

/** Kỳ lương/chấm công mặc định: tháng hiện tại (YYYY-MM), theo giờ máy client. */
export function currentPayPeriod(ref: Date = new Date()): string {
  const y = ref.getFullYear();
  const m = String(ref.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

/** Ngày đầu tháng của kỳ YYYY-MM → YYYY-MM-01. */
export function payPeriodStartDate(period: string): string {
  const [y, m] = period.split("-");
  return `${y}-${m}-01`;
}

/** HH:mm theo giờ VN — giờ vào/ra chấm công (ISO UTC → 07:48). */
export function formatTimeHHMM(v: string | Date | null | undefined, empty = "—"): string {
  if (v === null || v === undefined || v === "") return empty;
  const d = v instanceof Date ? v : new Date(v);
  if (Number.isNaN(d.getTime())) return empty;
  return d.toLocaleTimeString("vi-VN", {
    timeZone: VN_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
