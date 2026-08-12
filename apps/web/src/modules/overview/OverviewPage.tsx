import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchOverview, type OverviewData } from "../../shared/api";
import { currentPayPeriod } from "../../shared/formatDate";

function fmtPct(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return `${Number(v).toLocaleString("vi-VN")}%`;
}

function fmtVnd(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return `${Number(v).toLocaleString("vi-VN")} đ`;
}

/** Tổng Quan — card KPI + HC/OT theo bộ phận (02§2.4). */
export function OverviewPage() {
  const [period, setPeriod] = useState(currentPayPeriod);
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const ov = await fetchOverview(period);
      setData(ov);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải Tổng Quan.");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const maxHc = Math.max(1, ...(data?.by_department.map((d) => d.headcount) ?? [1]));
  const maxOt = Math.max(
    1,
    ...(data?.by_department.map((d) => Number(d.ot_hours)) ?? [1]),
  );

  return (
    <div className="module-page">
      <header className="module-header">
        <Link to="/" className="btn-back">
          ← Portal
        </Link>
        <nav className="breadcrumb">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <span>Tổng Quan</span>
        </nav>
      </header>
      <main className="module-body">
        <div className="module-toolbar">
          <h1>Tổng Quan</h1>
          <label className="period-picker">
            Kỳ
            <input
              type="month"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
            />
          </label>
        </div>
        {error && <p className="banner-warn">{error}</p>}
        {loading || !data ? (
          <p className="field-hint">Đang tải…</p>
        ) : (
          <>
            <div className="kpi-cards">
              <article className="kpi-card">
                <p>Tổng NV đang làm</p>
                <strong>{data.total_employees}</strong>
              </article>
              <article className="kpi-card">
                <p>Chuyên cần</p>
                <strong>{fmtPct(data.attendance_rate_pct)}</strong>
              </article>
              <article className="kpi-card">
                <p>Chi phí OT</p>
                <strong>{fmtVnd(data.ot_pay_total)}</strong>
              </article>
              <article className="kpi-card">
                <p>Khiếu nại mở</p>
                <strong>{data.open_disputes}</strong>
              </article>
            </div>

            <section className="kpi-section">
              <h2>HC / OT theo bộ phận</h2>
              <ul className="bar-chart">
                {data.by_department.map((d) => (
                  <li key={d.department_code}>
                    <span className="bar-label">
                      {d.department_name}
                      <small>
                        HC {d.headcount} · OT {Number(d.ot_hours).toLocaleString("vi-VN")}h
                      </small>
                    </span>
                    <div className="bar-tracks">
                      <div
                        className="bar-fill bar-hc"
                        style={{ width: `${(d.headcount / maxHc) * 100}%` }}
                        title="Số NV"
                      />
                      <div
                        className="bar-fill bar-ot"
                        style={{ width: `${(Number(d.ot_hours) / maxOt) * 100}%` }}
                        title="Giờ OT"
                      />
                    </div>
                  </li>
                ))}
              </ul>
              {data.by_department.length === 0 && (
                <p className="field-hint">Chưa có dữ liệu bộ phận kỳ này.</p>
              )}
            </section>

            <section className="kpi-section">
              <div className="module-toolbar">
                <h2>Cảnh báo gần đây</h2>
                <Link to="/m/report" className="btn-secondary">
                  Xem Báo cáo KPI
                </Link>
              </div>
              {data.recent_alerts.length === 0 ? (
                <p className="field-hint">Không có cảnh báo.</p>
              ) : (
                <ul className="alert-mini-list">
                  {data.recent_alerts.map((a) => (
                    <li key={a.id}>
                      <strong>{a.title}</strong>
                      <span>{a.body}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
