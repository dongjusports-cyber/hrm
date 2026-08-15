import { useCallback, useEffect, useState } from "react";
import {
  exportOtExternalExcel,
  fetchOtExternalPreview,
  type OtExternalPreview,
} from "../../shared/api";
import { FullScreenSheet } from "../../shared/FullScreenSheet";
import { formatOtHours } from "../../shared/formatOtHours";
import { formatVnd } from "../payroll/payrollGridColumns";

type Props = {
  open: boolean;
  period: string;
  onClose: () => void;
  onExported?: (message: string) => void;
};

/** OT ngoài lưu theo GIỜ → × 60 để dùng chung formatOtHours (phút). */
function fmtOt(v: unknown): string {
  const n = Number(v);
  if (v == null || v === "" || Number.isNaN(n)) return "—";
  return formatOtHours(n * 60, "—");
}

function fmtRate(v: unknown): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toFixed(2);
}

export function OtExternalPreviewSheet({ open, period, onClose, onExported }: Props) {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<OtExternalPreview | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchOtExternalPreview(period);
      setPreview(data);
    } catch (e) {
      setPreview(null);
      setError(e instanceof Error ? e.message : "Không tải preview OT ngoài được.");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    if (!open) return;
    void load();
  }, [open, load]);

  async function onExport() {
    setExporting(true);
    setError(null);
    try {
      const data = preview ?? (await fetchOtExternalPreview(period));
      const blob = await exportOtExternalExcel(period);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `OT_ngoai_${period}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      const amt = Number(data.total_amount_vnd);
      onExported?.(
        `Đã xuất OT ngoài ${period}: ${data.employee_count} NV · ${Number(data.total_effective_hours).toFixed(1)}h · ${amt.toLocaleString("vi-VN")}đ (ATM riêng).`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xuất OT ngoài được.");
    } finally {
      setExporting(false);
    }
  }

  const busy = loading || exporting;

  return (
    <FullScreenSheet
      open={open}
      title={`OT ngoài · kỳ ${period}`}
      subtitle="Bảng trả ATM riêng — không vào payslip / BHXH / PIT"
      onClose={onClose}
      actions={
        <button
          type="button"
          className="btn-primary"
          disabled={busy || !preview || preview.employee_count === 0}
          onClick={() => void onExport()}
        >
          {exporting ? "Đang xuất…" : "Xuất Excel"}
        </button>
      }
      inFrameScroll
      bodyClassName="fs-sheet-body-shell"
    >
      <div className="ot-ext-preview">
        {error && <p className="banner-warn">{error}</p>}

        {loading && !preview ? (
          <p className="fs-sheet-loading">Đang tải preview OT ngoài…</p>
        ) : preview ? (
          <>
            <div className="ot-ext-summary">
              <div className="ot-ext-stat">
                <span className="ot-ext-stat-label">Nhân viên</span>
                <strong>{preview.employee_count}</strong>
              </div>
              <div className="ot-ext-stat">
                <span className="ot-ext-stat-label">Giờ gốc</span>
                <strong>{fmtOt(preview.total_raw_hours)}</strong>
              </div>
              <div className="ot-ext-stat">
                <span className="ot-ext-stat-label">Giờ hiệu lực</span>
                <strong className="tk-ot-ext">{fmtOt(preview.total_effective_hours)}</strong>
              </div>
              <div className="ot-ext-stat ot-ext-stat-total">
                <span className="ot-ext-stat-label">Tổng trả ATM</span>
                <strong>{formatVnd(preview.total_amount_vnd)} đ</strong>
              </div>
            </div>

            {preview.policy_note ? (
              <p className="field-hint ot-ext-policy">{preview.policy_note}</p>
            ) : null}

            {preview.rows.length === 0 ? (
              <p className="ot-ext-empty">Không có OT ngoài trong kỳ này.</p>
            ) : (
              <div className="ot-ext-table-wrap">
                <table className="ot-ext-table">
                  <thead>
                    <tr>
                      <th>MSNV</th>
                      <th>Họ tên</th>
                      <th>STK</th>
                      <th className="num">Giờ gốc</th>
                      <th className="num">Giờ HL</th>
                      <th className="num">Cơ sở OT</th>
                      <th className="num">Đơn giá/giờ</th>
                      <th className="num">Hệ số</th>
                      <th className="num">Thành tiền</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r) => (
                      <tr key={r.employee_code}>
                        <td>{r.employee_code}</td>
                        <td>{r.full_name}</td>
                        <td>{r.bank_account || "—"}</td>
                        <td className="num">{fmtOt(r.raw_hours)}</td>
                        <td className="num tk-ot-ext">{fmtOt(r.effective_hours)}</td>
                        <td className="num">{formatVnd(r.ot_base)}</td>
                        <td className="num">{formatVnd(r.hourly_base)}</td>
                        <td className="num">{fmtRate(r.rate)}</td>
                        <td className="num ot-ext-amt">{formatVnd(r.amount_vnd)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={3}>
                        <strong>Tổng {preview.employee_count} NV</strong>
                      </td>
                      <td className="num">{fmtOt(preview.total_raw_hours)}</td>
                      <td className="num tk-ot-ext">{fmtOt(preview.total_effective_hours)}</td>
                      <td colSpan={3} />
                      <td className="num ot-ext-amt">
                        <strong>{formatVnd(preview.total_amount_vnd)}</strong>
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </>
        ) : null}

        <div className="ot-ext-actions">
          <button type="button" className="btn-ghost-dark" disabled={busy} onClick={() => void load()}>
            Làm mới
          </button>
        </div>
      </div>
    </FullScreenSheet>
  );
}
