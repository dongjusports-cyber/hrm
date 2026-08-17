import type { PayslipLine, WorkerPayslipDetail } from "./workerApi";

const EMPTY = "—";

export function formatWorkerVnd(v: string | number | null | undefined): string {
  if (v == null || v === "") return EMPTY;
  const n = Number(v);
  if (Number.isNaN(n)) return EMPTY;
  return Math.round(n).toLocaleString("vi-VN", { maximumFractionDigits: 0 }) + " đ";
}

export function formatWorkerQty(v: string | number | null | undefined): string {
  if (v == null || v === "") return EMPTY;
  const n = Number(v);
  if (Number.isNaN(n)) return EMPTY;
  return n.toLocaleString("vi-VN", { maximumFractionDigits: 2, minimumFractionDigits: 0 });
}

export function formatWorkerUnit(unit: string | null | undefined): string {
  if (!unit) return EMPTY;
  const u = unit.toLowerCase();
  if (u === "day" || u === "days" || u === "ngày") return "ngày";
  if (u === "hour" || u === "hours" || u === "giờ") return "giờ";
  if (u === "month" || u === "tháng") return "tháng";
  return unit;
}

export function periodTitle(period: string): string {
  const [y, m] = period.split("-");
  if (!y || !m) return period;
  return `${m}/${y}`;
}

type SectionProps = {
  title: string;
  lines: PayslipLine[];
  subtotalLabel: string;
  subtotal: string | number | null | undefined;
};

export function WorkerPayslipSectionTable({ title, lines, subtotalLabel, subtotal }: SectionProps) {
  return (
    <section className="worker-slip-section">
      <h2 className="worker-slip-section-title">{title}</h2>
      <div className="worker-slip-table" role="table">
        <div className="worker-slip-row worker-slip-head" role="row">
          <span role="columnheader">Mô tả</span>
          <span role="columnheader">ĐVT</span>
          <span role="columnheader">TV</span>
          <span role="columnheader">CT</span>
          <span role="columnheader">Tiền</span>
        </div>
        {lines.length === 0 ? (
          <p className="worker-slip-empty">Không có dòng trong nhóm này.</p>
        ) : (
          lines.map((line, idx) => (
            <div className="worker-slip-row" role="row" key={`${line.label}-${idx}`}>
              <span className="worker-slip-desc" role="cell">{line.label}</span>
              <span role="cell">{formatWorkerUnit(line.unit)}</span>
              <span role="cell">{formatWorkerQty(line.target)}</span>
              <span role="cell">{formatWorkerQty(line.quantity)}</span>
              <span className="worker-slip-amt" role="cell">{formatWorkerVnd(line.amount)}</span>
            </div>
          ))
        )}
        <div className="worker-slip-row worker-slip-subtotal" role="row">
          <span className="worker-slip-desc" role="cell">{subtotalLabel}</span>
          <span role="cell">{EMPTY}</span>
          <span role="cell">{EMPTY}</span>
          <span role="cell">{EMPTY}</span>
          <span className="worker-slip-amt" role="cell">{formatWorkerVnd(subtotal)}</span>
        </div>
      </div>
    </section>
  );
}

export function WorkerPayslipHeaderGrid({ slip }: { slip: WorkerPayslipDetail }) {
  const rows: { label: string; value: string }[] = [
    { label: "Số thẻ", value: slip.employee_code || EMPTY },
    { label: "Họ tên", value: slip.full_name || EMPTY },
    { label: "Bộ phận", value: slip.department_name ?? EMPTY },
    { label: "Tổ", value: slip.team_name ?? EMPTY },
    { label: "Chức vụ", value: slip.position_title ?? EMPTY },
    { label: "Lương TV", value: formatWorkerVnd(slip.probation_salary) },
    { label: "Lương CB", value: formatWorkerVnd(slip.contract_salary) },
  ];
  return (
    <section className="worker-slip-header-grid" aria-label="Thông tin nhân viên">
      {rows.map((r) => (
        <div key={r.label} className="worker-slip-header-item">
          <span>{r.label}</span>
          <strong>{r.value}</strong>
        </div>
      ))}
    </section>
  );
}
