/**
 * Định dạng ngày chuẩn DJ HRM: dd/mm/yyyy (luôn có số 0 đầu).
 */

function parseInput(v: string | Date): Date | null {
  if (v instanceof Date) {
    return Number.isNaN(v.getTime()) ? null : v;
  }
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(v.trim());
  if (iso) {
    const d = new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(v);
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
