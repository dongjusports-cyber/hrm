import { isValidTimeHHMM, normalizeTimeHHMM } from "../../shared/TimeInput24";

/** Chuẩn hoá giờ ô lưới: 800 → 08:00. null nếu không phải giờ hợp lệ. */
export function parseGridTimeInput(raw: string): string | null {
  const n = normalizeTimeHHMM(String(raw ?? "").trim());
  if (!n || !isValidTimeHHMM(n)) return null;
  return n;
}

export function toIsoTime(workDate: string, hhmmVal: string): string | null {
  const n = parseGridTimeInput(hhmmVal) ?? (isValidTimeHHMM(hhmmVal) ? hhmmVal : null);
  if (!n) return null;
  return `${workDate}T${n}:00+07:00`;
}

export type DayTimePatchOk = {
  ok: true;
  first_in?: string;
  last_out?: string;
  clear_times?: boolean;
  clear_first_in?: boolean;
  clear_last_out?: boolean;
};

export type DayTimePatchErr = { ok: false; error: string };

/** Ghép ô đang sửa với giờ còn lại trên dòng — được phép chỉ một mốc (vào hoặc ra). Ô trống = xóa mốc đó. */
export function buildDayTimePatch(opts: {
  workDate: string;
  col: "first_in" | "last_out";
  editedRaw: string;
  existingInHHmm: string;
  existingOutHHmm: string;
}): DayTimePatchOk | DayTimePatchErr {
  const typed = String(opts.editedRaw ?? "").trim();
  if (!typed) {
    if (opts.col === "first_in") {
      const outH = parseGridTimeInput(opts.existingOutHHmm);
      if (!outH) return { ok: true, clear_times: true };
      return { ok: true, clear_first_in: true };
    }
    const inH = parseGridTimeInput(opts.existingInHHmm);
    if (!inH) return { ok: true, clear_times: true };
    return { ok: true, clear_last_out: true };
  }
  const edited = parseGridTimeInput(typed);
  if (!edited) {
    return { ok: false, error: "Giờ phải dạng 08:00 (hoặc gõ 800)." };
  }
  const inH = opts.col === "first_in" ? edited : parseGridTimeInput(opts.existingInHHmm);
  const outH = opts.col === "last_out" ? edited : parseGridTimeInput(opts.existingOutHHmm);
  const first_in = inH ? toIsoTime(opts.workDate, inH) ?? undefined : undefined;
  const last_out = outH ? toIsoTime(opts.workDate, outH) ?? undefined : undefined;
  if (!first_in && !last_out) {
    return { ok: true, clear_times: true };
  }
  return { ok: true, first_in, last_out };
}

const SHIFT_START_MIN = 8 * 60;
const LUNCH_START_MIN = 12 * 60;
const LUNCH_END_MIN = 13 * 60;
const SHIFT_END_MIN = 17 * 60;

function hhmmToMin(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function minToHhmm(total: number): string {
  const clamped = Math.max(0, Math.min(23 * 60 + 59, Math.round(total)));
  const h = Math.floor(clamped / 60);
  const m = clamped % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/** Giờ công ca 08:00–17:00 trừ trưa 12:00–13:00 — khớp engine. */
export function previewShiftWorkedHours(inRaw: string, outRaw: string): number | null {
  const inn = parseGridTimeInput(inRaw);
  const out = parseGridTimeInput(outRaw);
  if (!inn || !out) return null;
  const a = Math.max(hhmmToMin(inn), SHIFT_START_MIN);
  const b = Math.min(hhmmToMin(out), SHIFT_END_MIN);
  if (b <= a) return 0;
  const overlap = Math.max(0, Math.min(b, LUNCH_END_MIN) - Math.max(a, LUNCH_START_MIN));
  return (b - a - overlap) / 60;
}

export function formatWorkedHours(hours: number): string {
  if (!Number.isFinite(hours)) return "";
  return hours.toFixed(4).replace(/\.?0+$/, "");
}

export function parseWorkedHoursInput(raw: string): number | null {
  const s = String(raw ?? "")
    .trim()
    .replace(",", ".");
  if (!s) return null;
  const n = Number(s);
  if (!Number.isFinite(n) || n <= 0 || n > 8) return null;
  return n;
}

/** Từ giờ vào (kẹp 08:00) cộng số giờ công, nhảy qua nghỉ trưa, không quá 17:00. */
export function outTimeAfterWorkedHours(inRaw: string, hours: number): string | null {
  if (!Number.isFinite(hours) || hours <= 0) return null;
  const inn = parseGridTimeInput(inRaw) ?? "08:00";
  let t = Math.max(hhmmToMin(inn), SHIFT_START_MIN);
  let remain = Math.round(hours * 60);
  while (remain > 0 && t < SHIFT_END_MIN) {
    if (t >= LUNCH_START_MIN && t < LUNCH_END_MIN) {
      t = LUNCH_END_MIN;
      continue;
    }
    const barrier = t < LUNCH_START_MIN ? LUNCH_START_MIN : SHIFT_END_MIN;
    const chunk = Math.min(remain, barrier - t);
    if (chunk <= 0) break;
    t += chunk;
    remain -= chunk;
  }
  return minToHhmm(t);
}
