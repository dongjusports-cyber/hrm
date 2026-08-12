import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { downloadKpiExport, fetchKpi, type KpiPeriod } from "../../shared/api";
import { currentPayPeriod } from "../../shared/formatDate";

function fmtPct(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return `${Number(v).toLocaleString("vi-VN")}%`;
}

function fmtNum(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return Number(v).toLocaleString("vi-VN");
}

const CAT_VI: Record<string, string> = {
  direct: "Trực tiếp",
  prod_indirect: "Gián tiếp SX",
  admin_indirect: "Gián tiếp hành chính",
};

/** Báo Cáo / KPI — Attendance, OT, Turnover (04§4.6). */
export function ReportPage() {
  const [period, setPeriod] = useState(currentPayPeriod);
  const [kpi, setKpi] = useState<KpiPeriod | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setKpi(await fetchKpi(period));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải KPI.");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onExport() {
    setExporting(true);
    try {
      await downloadKpiExport(period);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xuất Excel.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="module-page">
      <header className="module-header">
        <Link to="/" className="btn-back">
          ← Portal
        </Link>
        <nav className="breadcrumb">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <span>Báo Cáo / KPI</span>
        </nav>
      </header>
      <main className="module-body">
        <div className="module-toolbar">
          <h1>Báo Cáo / KPI</h1>
          <div className="toolbar-right">
            <label className="period-picker">
              Kỳ
              <input
                type="month"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              />
            </label>
            <button
              type="button"
              className="btn-secondary"
              disabled={exporting}
              onClick={() => void onExport()}
            >
              {exporting ? "Đang xuất…" : "Xuất Excel"}
            </button>
          </div>
        </div>
        <p className="field-hint">
          Công thức theo chuyên cần, tỷ lệ OT, tỷ lệ nghỉ việc; phân loại Trực tiếp / Gián tiếp theo
          bộ phận.
        </p>
        {error && <p className="banner-warn">{error}</p>}
        {loading || !kpi ? (
          <p className="field-hint">Đang tải…</p>
        ) : (
          <>
            <div className="kpi-cards">
              <article className="kpi-card">
                <p>Tỷ lệ chuyên cần</p>
                <strong>{fmtPct(kpi.attendance_rate_pct)}</strong>
                <small>
                  {fmtNum(kpi.attendants)} / {fmtNum(kpi.monthly_manpower)} (HC×B3)
                </small>
              </article>
              <article className="kpi-card">
                <p>Tỷ lệ OT</p>
                <strong>{fmtPct(kpi.ot_rate_pct)}</strong>
                <small>
                  {fmtNum(kpi.ot_hours)}h / {fmtNum(kpi.reference_hours)}h
                </small>
              </article>
              <article className="kpi-card">
                <p>Tỷ lệ nghỉ việc</p>
                <strong>{fmtPct(kpi.turnover_rate_pct)}</strong>
                <small>
                  Nghỉ {kpi.resign} · Đầu kỳ {kpi.begin_hc} → Cuối kỳ {kpi.end_hc}
                </small>
              </article>
              <article className="kpi-card">
                <p>Số NV kỳ</p>
                <strong>{kpi.headcount}</strong>
                <small>
                  Tuyển {kpi.recruit} · B3={fmtNum(kpi.param_b3)}
                </small>
              </article>
            </div>

            <section className="kpi-section">
              <h2>Nhân lực theo loại</h2>
              <table className="kpi-table">
                <thead>
                  <tr>
                    <th>Loại</th>
                    <th>HC</th>
                    <th>Ngày công</th>
                    <th>OT (giờ)</th>
                  </tr>
                </thead>
                <tbody>
                  {kpi.by_category.map((c) => (
                    <tr key={c.category}>
                      <td>{CAT_VI[c.category] ?? c.label}</td>
                      <td>{c.headcount}</td>
                      <td>{fmtNum(c.worked_days)}</td>
                      <td>{fmtNum(c.ot_hours)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="kpi-section">
              <h2>Theo bộ phận</h2>
              <table className="kpi-table">
                <thead>
                  <tr>
                    <th>Bộ phận</th>
                    <th>Loại</th>
                    <th>HC</th>
                    <th>Ngày công</th>
                    <th>OT giờ</th>
                    <th>OT tiền</th>
                  </tr>
                </thead>
                <tbody>
                  {kpi.by_department.map((d) => (
                    <tr key={d.department_code}>
                      <td>
                        {d.department_name} ({d.department_code})
                      </td>
                      <td>{CAT_VI[d.category] ?? d.category}</td>
                      <td>{d.headcount}</td>
                      <td>{fmtNum(d.worked_days)}</td>
                      <td>{fmtNum(d.ot_hours)}</td>
                      <td>{fmtNum(d.ot_pay)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <p className="field-hint">{kpi.formula_note}</p>
          </>
        )}
      </main>
    </div>
  );
}
