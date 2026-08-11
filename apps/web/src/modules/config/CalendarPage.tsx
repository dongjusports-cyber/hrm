import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  addHoliday,
  deleteHoliday,
  fetchDivisor,
  fetchHolidays,
  fetchWorkWeek,
  updateWorkWeek,
  type DivisorInfo,
  type Holiday,
  type WorkWeek,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";

const DAY_LABELS: Record<number, string> = {
  1: "Thứ 2",
  2: "Thứ 3",
  3: "Thứ 4",
  4: "Thứ 5",
  5: "Thứ 6",
  6: "Thứ 7",
  7: "Chủ nhật",
};

export function CalendarPage() {
  const [year, setYear] = useState(2025);
  const [month, setMonth] = useState(10);
  const [divisor, setDivisor] = useState<DivisorInfo | null>(null);
  const [workWeek, setWorkWeek] = useState<WorkWeek | null>(null);
  const [weekDays, setWeekDays] = useState<number[]>([1, 2, 3, 4, 5, 6]);
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [newDate, setNewDate] = useState("");
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function reloadAll() {
    setLoading(true);
    setError(null);
    try {
      const [ww, hol, div] = await Promise.all([
        fetchWorkWeek(),
        fetchHolidays(year),
        fetchDivisor(year, month),
      ]);
      setWorkWeek(ww);
      setWeekDays(ww.work_weekdays);
      setHolidays(hol);
      setDivisor(div);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được lịch.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reloadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onPreview() {
    setError(null);
    try {
      const div = await fetchDivisor(year, month);
      setDivisor(div);
      const hol = await fetchHolidays(year);
      setHolidays(hol);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tính được mẫu số.");
    }
  }

  function toggleDay(d: number) {
    setWeekDays((prev) => {
      if (prev.includes(d)) {
        if (prev.length <= 1) {
          setError("Trợ Lý AI: phải giữ ít nhất 1 ngày làm việc.");
          return prev;
        }
        return prev.filter((x) => x !== d);
      }
      return [...prev, d].sort((a, b) => a - b);
    });
  }

  async function onSaveWeek(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      const ww = await updateWorkWeek({ work_weekdays: weekDays });
      setWorkWeek(ww);
      setOk("Đã lưu tuần làm việc.");
      const div = await fetchDivisor(year, month);
      setDivisor(div);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại.");
    }
  }

  async function onAddHoliday(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      await addHoliday({ date: newDate, name: newName });
      setNewDate("");
      setNewName("");
      setOk("Đã thêm ngày lễ.");
      await reloadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thêm được ngày lễ.");
    }
  }

  async function onDeleteHoliday(day: string) {
    if (!confirm(`Xóa ngày lễ ${day}?`)) return;
    try {
      await deleteHoliday(day);
      setOk("Đã xóa ngày lễ.");
      await reloadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    }
  }

  return (
    <div className="calendar-page">
      <div className="users-head">
        <div>
          <h1>Lịch công ty</h1>
          <p className="module-placeholder">
            Tuần làm việc + ngày lễ → tự tính ngày công chuẩn và mẫu số (rule 27→26 từ Policy).
          </p>
        </div>
        <Link to="/m/config" className="btn-back">
          ← Cấu Hình
        </Link>
      </div>

      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}
      {loading ? (
        <p>Đang tải…</p>
      ) : (
        <div className="calendar-layout">
          <section className="users-form-card">
            <h2>Xem mẫu số tháng</h2>
            <div className="calendar-row">
              <label className="field">
                <span>Năm</span>
                <input
                  type="number"
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  min={2000}
                  max={2100}
                />
              </label>
              <label className="field">
                <span>Tháng</span>
                <input
                  type="number"
                  value={month}
                  onChange={(e) => setMonth(Number(e.target.value))}
                  min={1}
                  max={12}
                />
              </label>
              <button type="button" className="btn-primary" onClick={() => void onPreview()}>
                Tính lại
              </button>
            </div>
            {divisor && (
              <div className="divisor-box">
                <p>
                  <strong>Ngày công chuẩn:</strong> {divisor.official_work_days}
                </p>
                <p>
                  <strong>Mẫu số (chia lương):</strong> {divisor.salary_divisor}
                </p>
                <p className="field-hint">{divisor.detail}</p>
                {divisor.policy_package_name && (
                  <p className="field-hint">Policy: {divisor.policy_package_name}</p>
                )}
              </div>
            )}
          </section>

          <section className="users-form-card">
            <h2>Tuần làm việc</h2>
            <form onSubmit={onSaveWeek}>
              <div className="week-checks">
                {[1, 2, 3, 4, 5, 6, 7].map((d) => (
                  <label key={d} className="check-row">
                    <input
                      type="checkbox"
                      checked={weekDays.includes(d)}
                      onChange={() => toggleDay(d)}
                    />
                    <span>{DAY_LABELS[d]}</span>
                  </label>
                ))}
              </div>
              {workWeek && (
                <p className="field-hint">
                  Giờ chuẩn: {workWeek.morning_start.slice(0, 5)}–{workWeek.morning_end.slice(0, 5)} /{" "}
                  {workWeek.afternoon_start.slice(0, 5)}–{workWeek.afternoon_end.slice(0, 5)}
                </p>
              )}
              <button type="submit" className="btn-primary login-submit">
                Lưu tuần làm việc
              </button>
            </form>
          </section>

          <section className="users-form-card calendar-holidays">
            <h2>Ngày lễ {year}</h2>
            <form className="holiday-add" onSubmit={onAddHoliday}>
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                required
              />
              <input
                placeholder="Tên ngày lễ"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
              />
              <button type="submit" className="btn-primary">
                Thêm
              </button>
            </form>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Ngày</th>
                  <th>Tên</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {holidays.map((h) => (
                  <tr key={h.date}>
                    <td>{formatDateDDMMYYYY(h.date)}</td>
                    <td>{h.name}</td>
                    <td>
                      <button
                        type="button"
                        className="link-btn danger"
                        onClick={() => void onDeleteHoliday(h.date)}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </div>
  );
}
