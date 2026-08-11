import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchHRPayslipDetail, type HRPayslipDetail, type Payslip } from "../../shared/api";
import { formatVnd } from "./payrollGridColumns";

type Props = {
  rows: Payslip[];
  selected: Payslip | null;
  onSelect: (slip: Payslip) => void;
};

function LineTable({
  title,
  lines,
  empty,
}: {
  title: string;
  lines: HRPayslipDetail["work_lines"];
  empty: string;
}) {
  if (lines.length === 0) {
    return (
      <div className="payroll-slip-block">
        <h3>{title}</h3>
        <p className="field-hint">{empty}</p>
      </div>
    );
  }
  return (
    <div className="payroll-slip-block">
      <h3>{title}</h3>
      <table className="payroll-slip-lines">
        <thead>
          <tr>
            <th>Khoản</th>
            <th>SL</th>
            <th className="num">Số tiền</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((ln) => (
            <tr key={`${ln.component_code}-${ln.segment}-${ln.seq_no}`}>
              <td>
                <span className="payroll-line-name">{ln.component_name}</span>
                {ln.note ? <span className="payroll-line-note">{ln.note}</span> : null}
              </td>
              <td>{ln.quantity != null ? `${ln.quantity}${ln.unit ? ` ${ln.unit}` : ""}` : "—"}</td>
              <td className="num">{formatVnd(ln.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PayrollPayslipSection({ rows, selected, onSelect }: Props) {
  const [detail, setDetail] = useState<HRPayslipDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(
      (r) =>
        r.employee_code.toLowerCase().includes(needle) ||
        r.full_name.toLowerCase().includes(needle),
    );
  }, [rows, q]);

  const loadDetail = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      setDetail(await fetchHRPayslipDetail(id));
    } catch (e) {
      setDetail(null);
      setError(e instanceof Error ? e.message : "Không tải phiếu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selected?.id) void loadDetail(selected.id);
    else setDetail(null);
  }, [selected?.id, loadDetail]);

  const slip = detail?.payslip ?? selected;

  function goPrev() {
    if (!selected || filtered.length === 0) return;
    const idx = filtered.findIndex((r) => r.id === selected.id);
    const next = filtered[(idx - 1 + filtered.length) % filtered.length];
    onSelect(next);
  }

  function goNext() {
    if (!selected || filtered.length === 0) return;
    const idx = filtered.findIndex((r) => r.id === selected.id);
    const next = filtered[(idx + 1) % filtered.length];
    onSelect(next);
  }

  return (
    <section className="payroll-payslip-split">
      <aside className="payroll-payslip-list">
        <div className="payroll-payslip-list-head">
          <h2>Phiếu lương</h2>
          <input
            type="search"
            placeholder="Tìm MSNV / họ tên…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Tìm nhân viên"
          />
        </div>
        <ul className="payroll-payslip-picker">
          {filtered.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                className={selected?.id === r.id ? "is-active" : undefined}
                onClick={() => onSelect(r)}
              >
                <span className="payroll-picker-code">{r.employee_code}</span>
                <span className="payroll-picker-name">{r.full_name}</span>
                <span className="payroll-picker-net">{formatVnd(r.net)}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <div className="payroll-payslip-detail">
        {!slip ? (
          <p className="field-hint">Chọn một nhân viên bên trái để xem phiếu.</p>
        ) : (
          <>
            <header className="payroll-payslip-detail-head">
              <div>
                <h2>
                  {slip.full_name}{" "}
                  <span className="payroll-picker-code">MSNV {slip.employee_code}</span>
                </h2>
                <p className="field-hint">
                  Kỳ {detail?.period ?? slip.period ?? "—"}
                  {slip.worked_days != null ? ` · Công ${slip.worked_days}` : ""}
                  {slip.al_days != null ? ` · AL ${slip.al_days}` : ""}
                </p>
              </div>
              <div className="payroll-nav-slips">
                <button type="button" className="btn-ghost-dark btn-sm" onClick={goPrev}>
                  ← Trước
                </button>
                <button type="button" className="btn-ghost-dark btn-sm" onClick={goNext}>
                  Sau →
                </button>
              </div>
            </header>

            {error && <p className="banner-warn">{error}</p>}
            {loading && <p className="field-hint">Đang tải chi tiết…</p>}

            {detail && !loading && (
              <div className="payroll-slip-three-cols">
                <LineTable
                  title="Ngày công & nghỉ"
                  lines={detail.work_lines}
                  empty="Chưa có dòng công / nghỉ / OT."
                />
                <LineTable
                  title="Trợ cấp"
                  lines={detail.allowance_lines}
                  empty="Không có phụ cấp / thưởng kỳ này."
                />
                <LineTable
                  title="Khấu trừ"
                  lines={detail.deduction_lines}
                  empty="Không có khấu trừ."
                />
              </div>
            )}

            {slip && (
              <footer className="payroll-sticky-totals payroll-slip-footer">
                <div>
                  <span className="payroll-total-label">Tổng thu nhập</span>
                  <strong>{formatVnd(slip.gross)}</strong>
                </div>
                <div>
                  <span className="payroll-total-label">Thu nhập chịu thuế</span>
                  <strong>{formatVnd(slip.taxable_income)}</strong>
                </div>
                <div>
                  <span className="payroll-total-label">Thực lãnh</span>
                  <strong className="payroll-total-net">{formatVnd(slip.net)}</strong>
                </div>
                <div>
                  <span className="payroll-total-label">Số dư phép</span>
                  <strong>
                    {detail?.annual_leave_remaining != null
                      ? Number(detail.annual_leave_remaining).toLocaleString("vi-VN")
                      : "—"}
                  </strong>
                </div>
              </footer>
            )}
          </>
        )}
      </div>
    </section>
  );
}
