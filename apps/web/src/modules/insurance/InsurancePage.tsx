import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import {
  fetchInsuranceRows,
  fetchInsuranceSummary,
  type InsuranceRow,
  type InsuranceSummary,
} from "../../shared/api";
import { currentPayPeriod } from "../../shared/formatDate";
import { InsuranceDeclarationsSection } from "./InsuranceDeclarationsSection";
import { FamilyDependentsPage } from "../hr/FamilyDependentsPage";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

function formatVnd(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return `${Number(v).toLocaleString("vi-VN")} đ`;
}

type InsuranceTab = "tax" | "insurance" | "declarations";

const TAB_LABELS: Record<InsuranceTab, string> = {
  tax: "Thuế",
  insurance: "Bảo hiểm",
  declarations: "Báo tăng BHXH",
};

function parseTab(raw: string | null): InsuranceTab {
  if (raw === "tax" || raw === "insurance" || raw === "declarations") return raw;
  return "tax";
}

/** Bảo Hiểm Thuế — tab Thuế (NPT) · BH/TNCN theo kỳ · báo tăng BHXH. */
export function InsurancePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = parseTab(searchParams.get("tab"));
  const [period, setPeriod] = useState(currentPayPeriod);
  const [summary, setSummary] = useState<InsuranceSummary | null>(null);
  const [rows, setRows] = useState<InsuranceRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function setTab(next: InsuranceTab) {
    setSearchParams({ tab: next }, { replace: true });
  }

  const reload = useCallback(async () => {
    if (tab !== "insurance") return;
    setLoading(true);
    try {
      const [s, r] = await Promise.all([
        fetchInsuranceSummary(period),
        fetchInsuranceRows(period),
      ]);
      setSummary(s);
      setRows(r);
      setError(null);
    } catch (e) {
      setSummary(null);
      setRows([]);
      setError(e instanceof Error ? e.message : "Không tải Bảo Hiểm Thuế.");
    } finally {
      setLoading(false);
    }
  }, [period, tab]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const columnDefs = useMemo<ColDef<InsuranceRow>[]>(
    () => [
      { field: "employee_code", headerName: "MSNV", width: 90, pinned: "left" },
      { field: "full_name", headerName: "Họ tên", flex: 1, minWidth: 140 },
      {
        field: "gross",
        headerName: "Tổng thu",
        width: 120,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        field: "bhxh",
        headerName: "BHXH",
        width: 100,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        field: "bhyt",
        headerName: "BHYT",
        width: 95,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        field: "bhtn",
        headerName: "BHTN",
        width: 95,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        field: "union_fee",
        headerName: "Công đoàn",
        width: 110,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        field: "pit_amount",
        headerName: "TNCN",
        width: 110,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        field: "tax_dependent_count",
        headerName: "NPT",
        width: 70,
      },
      {
        field: "net",
        headerName: "Thực lãnh",
        width: 120,
        valueFormatter: (p) => formatVnd(p.value),
      },
    ],
    [],
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
          <span>Bảo Hiểm Thuế</span>
        </nav>
      </header>
      <main className="module-body">
        <div className="module-toolbar">
          <h1>Bảo Hiểm Thuế</h1>
          {tab === "insurance" && (
            <>
              <label className="period-picker">
                Kỳ
                <input
                  type="month"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                />
              </label>
              <Link to="/m/config/payroll-policy" className="btn-secondary">
                Cấu hình BH / TNCN
              </Link>
            </>
          )}
        </div>

        <nav className="payroll-tabs" aria-label="Bảo Hiểm Thuế">
          {(Object.keys(TAB_LABELS) as InsuranceTab[]).map((key) => (
            <button
              key={key}
              type="button"
              className={tab === key ? "btn-primary" : "btn-ghost-dark"}
              onClick={() => setTab(key)}
            >
              {TAB_LABELS[key]}
            </button>
          ))}
        </nav>

        {tab === "tax" && <FamilyDependentsPage embedded />}

        {tab === "insurance" && (
          <>
            {error && <p className="banner-warn">{error}</p>}
            {loading ? (
              <p className="field-hint">Đang tải…</p>
            ) : summary ? (
              <>
                <p className="field-hint">
                  TNCN trong kỳ:{" "}
                  {summary.pit_enabled_in_snapshot === true
                    ? "đã bật (ảnh chụp Policy)"
                    : summary.pit_enabled_in_snapshot === false
                      ? "đang tắt — bật TNCN trong Policy khi Chủ chốt"
                      : "chưa có snapshot"}
                </p>
                <div className="kpi-cards">
                  <article className="kpi-card">
                    <p>Số phiếu</p>
                    <strong>{summary.employee_count}</strong>
                  </article>
                  <article className="kpi-card">
                    <p>Tổng BHXH</p>
                    <strong>{formatVnd(summary.total_bhxh)}</strong>
                  </article>
                  <article className="kpi-card">
                    <p>Tổng BHYT</p>
                    <strong>{formatVnd(summary.total_bhyt)}</strong>
                  </article>
                  <article className="kpi-card">
                    <p>Tổng BHTN</p>
                    <strong>{formatVnd(summary.total_bhtn)}</strong>
                  </article>
                  <article className="kpi-card">
                    <p>Tổng TNCN</p>
                    <strong>{formatVnd(summary.total_pit)}</strong>
                  </article>
                  <article className="kpi-card">
                    <p>Tổng thực lãnh</p>
                    <strong>{formatVnd(summary.total_net)}</strong>
                  </article>
                </div>
                <div className="ag-theme-alpine payroll-grid" style={{ height: 480, width: "100%" }}>
                  <AgGridReact<InsuranceRow>
                    rowData={rows}
                    columnDefs={columnDefs}
                    getRowId={(p) => p.data.employee_id}
                    defaultColDef={{ sortable: true, resizable: true }}
                  />
                </div>
              </>
            ) : null}
          </>
        )}

        {tab === "declarations" && <InsuranceDeclarationsSection />}
      </main>
    </div>
  );
}
