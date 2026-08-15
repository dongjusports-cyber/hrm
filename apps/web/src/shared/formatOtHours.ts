/**
 * Định dạng OT: phút → giờ, tối đa 2 số thập phân, bỏ số 0 thừa, hậu tố `h`.
 * <= 0 / null / undefined → chuỗi rỗng (mặc định) để lưới không hiện "0h".
 *
 * Nguồn giá trị theo GIỜ (vd. KPI, monthly grid): nhân 60 trước khi gọi
 * để dùng chung một hàm — formatOtHours(hoursValue * 60).
 */
export function formatOtHours(minutes: number | null | undefined, empty = ""): string {
  if (minutes == null || minutes <= 0) return empty;
  const h = minutes / 60;
  const s = h.toFixed(2).replace(/\.?0+$/, "");
  return `${s}h`;
}
