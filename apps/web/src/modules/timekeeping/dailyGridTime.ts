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
};

export type DayTimePatchErr = { ok: false; error: string };

/** Ghép ô đang sửa với giờ còn lại trên dòng — được phép chỉ một mốc (vào hoặc ra). */
export function buildDayTimePatch(opts: {
  workDate: string;
  col: "first_in" | "last_out";
  editedRaw: string;
  existingInHHmm: string;
  existingOutHHmm: string;
}): DayTimePatchOk | DayTimePatchErr {
  const typed = String(opts.editedRaw ?? "").trim();
  if (!typed) {
    return { ok: false, error: "Nhập giờ vào hoặc giờ ra." };
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
    return { ok: false, error: "Nhập giờ vào hoặc giờ ra." };
  }
  return { ok: true, first_in, last_out };
}
