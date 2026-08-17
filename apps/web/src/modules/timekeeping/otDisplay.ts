/** Phút OT CN / lễ — lưới Chấm công và phiếu lương. */

export function hoursToOtMinutes(hours: string | number | null | undefined): number {
  const n = Number(hours ?? 0);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return n * 60;
}

export function weekendOtMinutes(day: {
  sunday_hours?: string | number | null;
  ot_minutes?: number | null;
  ot_type?: string | null;
}): number {
  if ((day.ot_type || "").toLowerCase() === "weekend" && (day.ot_minutes ?? 0) > 0) {
    return Number(day.ot_minutes);
  }
  return hoursToOtMinutes(day.sunday_hours);
}

export function holidayOtMinutes(day: {
  holiday_hours?: string | number | null;
  ot_minutes?: number | null;
  ot_type?: string | null;
}): number {
  if ((day.ot_type || "").toLowerCase() === "holiday" && (day.ot_minutes ?? 0) > 0) {
    return Number(day.ot_minutes);
  }
  return hoursToOtMinutes(day.holiday_hours);
}
