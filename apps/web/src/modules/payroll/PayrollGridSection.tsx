import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import type { RowClickedEvent } from "ag-grid-community";
import type { Payslip } from "../../shared/api";
import {
  PAYROLL_VIEW_LABELS,
  columnsForViewMode,
  formatVnd,
  payrollGridNeedsHorizontalScroll,
  sumPayslipField,
  type PayrollViewMode,
} from "./payrollGridColumns";
import { AG_GRID_DEFAULT_COL_DEF, AG_GRID_LOCALE_VI } from "../../shared/agGridVi";

type Props = {
  period: string;
  rows: Payslip[];
  viewMode: PayrollViewMode;
  onViewModeChange: (mode: PayrollViewMode) => void;
  selectedId: string | null;
  onSelect: (slip: Payslip) => void;
};

export function PayrollGridSection({
  period,
  rows,
  viewMode,
  onViewModeChange,
  selectedId,
  onSelect,
}: Props) {
  const columnDefs = useMemo(() => columnsForViewMode(viewMode), [viewMode]);
  const allowHorizontalScroll = payrollGridNeedsHorizontalScroll(viewMode);

  function fitGridColumns() {
    return (api: { sizeColumnsToFit: () => void }) => {
      if (!allowHorizontalScroll) {
        api.sizeColumnsToFit();
      }
    };
  }

  const totals = useMemo(
    () => ({
      gross: sumPayslipField(rows, "gross"),
      net: sumPayslipField(rows, "net"),
    }),
    [rows],
  );

  function onRowClicked(e: RowClickedEvent<Payslip>) {
    if (e.data) onSelect(e.data);
  }

  return (
    <section className="payroll-grid-section">
      <div className="payroll-view-toolbar">
        <h2>
          Bảng lương {period} · {rows.length} NV
        </h2>
        <div className="payroll-view-modes" role="tablist" aria-label="Chế độ xem bảng lương">
          {(Object.keys(PAYROLL_VIEW_LABELS) as PayrollViewMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={viewMode === mode}
              className={viewMode === mode ? "btn-primary btn-sm" : "btn-ghost-dark btn-sm"}
              onClick={() => onViewModeChange(mode)}
            >
              {PAYROLL_VIEW_LABELS[mode]}
            </button>
          ))}
        </div>
      </div>

      <div className="ag-theme-quartz hr-grid payroll-grid payroll-grid-fill">
        <AgGridReact<Payslip>
          rowData={rows}
          columnDefs={columnDefs}
          getRowId={(p) => p.data.id}
          rowSelection="single"
          onRowClicked={onRowClicked}
          getRowClass={(p) => (p.data?.id === selectedId ? "payroll-row-selected" : undefined)}
          localeText={AG_GRID_LOCALE_VI}
          defaultColDef={{ ...AG_GRID_DEFAULT_COL_DEF, sortable: true, resizable: true, filter: true }}
          suppressHorizontalScroll={!allowHorizontalScroll}
          onGridReady={(e) => fitGridColumns()(e.api)}
          onGridSizeChanged={(e) => fitGridColumns()(e.api)}
          onFirstDataRendered={(e) => fitGridColumns()(e.api)}
          animateRows={false}
        />
      </div>

      <footer className="payroll-sticky-totals" aria-label="Tổng kỳ lương">
        <div>
          <span className="payroll-total-label">Tổng thu nhập</span>
          <strong>{formatVnd(totals.gross)}</strong>
        </div>
        <div>
          <span className="payroll-total-label">Thực lãnh</span>
          <strong className="payroll-total-net">{formatVnd(totals.net)}</strong>
        </div>
        <div>
          <span className="payroll-total-label">Số phiếu</span>
          <strong>{rows.length}</strong>
        </div>
      </footer>
    </section>
  );
}
