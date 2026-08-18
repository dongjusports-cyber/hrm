import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchWorkerAttendance, type WorkerAttendanceMonth } from "./workerApi";
import { useWorkerAuth } from "./workerAuthStore";

const WD = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

function currentPeriod(): string {
  const n = new Date();
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}`;
}

function shiftPeriod(period: string, delta: number): string {
  const [y, m] = period.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function fmtHm(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Ho_Chi_Minh",
  });
}

function fmtDay(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return d && m ? `${d}/${m}` : isoDate;
}

function weekdayLabel(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  if (!y || !m || !d) return "";
  return WD[new Date(y, m - 1, d).getDay()] ?? "";
}

function fmtNum(v: string | number): string {
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("vi-VN", { maximumFractionDigits: 1 });
}

function periodTitle(period: string): string {
  const [y, m] = period.split("-");
  return `Tháng ${Number(m)}/${y}`;
}

export function WorkerAttendancePage() {
  const { worker } = useWorkerAuth();
  const [period, setPeriod] = useState(currentPeriod);
  const [data, setData] = useState<WorkerAttendanceMonth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const maxPeriod = useMemo(() => currentPeriod(), []);
  const canNext = period < maxPeriod;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void fetchWorkerAttendance(period)
      .then((row) => {
        if (!cancelled) setData(row);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được bảng công.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  const days = data?.days ?? [];

  return (
    <div className="worker-page">
      <header className="worker-top">
        <div>
          <p className="worker-hello">Chấm công của tôi</p>
          <h1>{worker?.full_name}</h1>
          <p className="worker-msnv">MSNV {worker?.employee_code}</p>
        </div>
        <Link to="/worker" className="worker-btn-secondary">
          Về trang chủ
        </Link>
      </header>

      <div className="worker-att-toolbar">
        <button
          type="button"
          className="worker-btn-secondary"
          onClick={() => setPeriod(shiftPeriod(period, -1))}
        >
          Tháng trước
        </button>
        <strong>{periodTitle(period)}</strong>
        <button
          type="button"
          className="worker-btn-secondary"
          disabled={!canNext}
          onClick={() => setPeriod(shiftPeriod(period, 1))}
        >
          Tháng sau
        </button>
      </div>

      {error && <p className="worker-error">{error}</p>}

      {data && !loading ? (
        <div className="worker-att-summary" aria-label="Tóm tắt tháng">
          <div>
            <span>Công</span>
            <strong>{fmtNum(data.worked_days)}</strong>
          </div>
          <div>
            <span>Phép</span>
            <strong>{fmtNum(data.al_days)}</strong>
          </div>
          <div>
            <span>Muộn</span>
            <strong>{data.late_count}</strong>
          </div>
        </div>
      ) : null}

      <section className="worker-section">
        {loading ? (
          <p className="worker-empty">Đang tải…</p>
        ) : days.length === 0 ? (
          <p className="worker-empty">Chưa có ngày công trong tháng này.</p>
        ) : (
          <ul className="worker-att-list">
            {days.map((row) => {
              const wd = weekdayLabel(row.work_date);
              const hours = Number(row.worked_hours);
              const notes: string[] = [];
              if (row.leave_code) notes.push(row.leave_code);
              if (row.late_minutes > 0) notes.push(`muộn ${row.late_minutes}p`);
              if (row.early_minutes > 0) notes.push(`về sớm ${row.early_minutes}p`);
              if (row.ot_minutes > 0) notes.push(`OT ${row.ot_minutes}p`);
              const empty = !row.first_in && !row.last_out && !row.leave_code && hours <= 0;
              return (
                <li
                  key={row.work_date}
                  className={
                    empty && wd === "CN" ? "worker-att-off" : empty ? "worker-att-empty" : undefined
                  }
                >
                  <div className="worker-att-when">
                    <strong>
                      {fmtDay(row.work_date)} {wd}
                    </strong>
                    {notes.length ? <span>{notes.join(" · ")}</span> : null}
                  </div>
                  <div className="worker-att-times">
                    <span>
                      {fmtHm(row.first_in)} → {fmtHm(row.last_out)}
                    </span>
                    <em>{hours > 0 ? `${fmtNum(hours)}h` : empty ? "—" : ""}</em>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
