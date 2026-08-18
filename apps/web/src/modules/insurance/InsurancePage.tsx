import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, ICellRendererParams } from "ag-grid-community";
import {
  fetchInsuranceRows,
  fetchInsuranceSummary,
  updateEmployee,
  type InsuranceRow,
  type InsuranceSummary,
} from "../../shared/api";
import { currentPayPeriod } from "../../shared/formatDate";
import { InsuranceDeclarationsSection } from "./InsuranceDeclarationsSection";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

function formatVnd(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return `${Number(v).toLocaleString("vi-VN")} đ`;
}

type InsuranceTab = "insurance" | "declarations";

const TAB_LABELS: Record<InsuranceTab, string> = {
  insurance: "Bảo hiểm",
  declarations: "Báo tăng BHXH",
};

function parseTab(raw: string | null): InsuranceTab {
  if (raw === "declarations") return "declarations";
  return "insurance";
}

function SiEnrolledCheckbox(p: ICellRendererParams<InsuranceRow>) {
  const row = p.data;
  const [busy, setBusy] = useState(false);
  if (!row) return null;
  return (
    <label className="field emp-check-row" onClick={(e) => e.stopPropagation()}>
      <input
        type="checkbox"
        checked={Boolean(p.value)}
        disabled={busy}
        title="Tham gia BHXH tại CTY này — NV còn sổ CTY cũ thì bỏ tick"
        onChange={async (e) => {
          const next = e.target.checked;
          setBusy(true);
          try {
            await updateEmployee(row.employee_id, { si_enrolled: next });
            p.node.setDataValue("si_enrolled", next);
          } catch (err) {
            window.alert(err instanceof Error ? err.message : "Không lưu tick BHXH.");
          } finally {
            setBusy(false);
          }
        }}
      />
    </label>
  );
}

/** Bảo Hiểm — kỳ lương + báo tăng BHXH. Ẩn TNCN / NPT (kế toán làm riêng). */
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
      setError(e instanceof Error ? e.message : "Không tải Bảo Hiểm.");
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
        field: "si_enrolled",
        headerName: "Tham gia BHXH",
        width: 130,
        cellRenderer: SiEnrolledCheckbox,
        sortable: true,
      },
      {
        field: "si_base",
        headerName: "Tổng lương tham gia BH",
        width: 180,
        headerTooltip: "Lương HĐ + chức vụ + độc hại + tay nghề + thâm niên + PCCC + HSE",
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
          <span>Bảo Hiểm</span>
        </nav>
      </header>
      <main className="module-body">
        <div className="module-toolbar">
          <h1>Bảo Hiểm</h1>
          {tab === "insurance" && (
            <label className="period-picker">
              Kỳ
              <input
                type="month"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              />
            </label>
          )}
        </div>

        <nav className="payroll-tabs" aria-label="Bảo Hiểm">
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

        {tab === "insurance" && (
          <>
            {error && <p className="banner-warn">{error}</p>}
            {loading && !summary ? (
              <p className="field-hint">Đang tải…</p>
            ) : summary ? (
              <>
                {loading && <p className="field-hint">Đang cập nhật…</p>}
                <p className="field-hint">
                  Đóng đủ tháng khi đã tick BHXH, còn làm từ ngày 16 và ≥ 12 ngày công.
                  NV còn sổ CTY cũ: bỏ tick. Tick xong cần Tính lương lại để cập nhật số tiền.
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
                    <p>Tổng công đoàn</p>
                    <strong>{formatVnd(summary.total_union_fee)}</strong>
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
                    animateRows={false}
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
