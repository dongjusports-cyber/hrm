import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  confirmWorkerPayslip,
  disputeWorkerPayslip,
  fetchDisputeReasons,
  fetchWorkerPayslip,
  type DisputeReason,
  type WorkerPayslipDetail,
} from "./workerApi";
import { formatDateDDMMYYYY, formatDateTimeDDMMYYYY } from "../shared/formatDate";
import {
  formatWorkerQty,
  formatWorkerVnd,
  periodTitle,
  WorkerPayslipHeaderGrid,
  WorkerPayslipSectionTable,
} from "./workerPayslipDisplay";

const STATUS_VI: Record<string, string> = {
  published: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  disputed: "Đang khiếu nại",
  resolved: "Đã xử lý",
  expired: "Hết hạn xác nhận",
};

/** Chi tiết phiếu Genus-style — confirm P4.2 · khiếu nại P4.3 (WK-I003). */
export function WorkerPayslipPage() {
  const { payslipId = "" } = useParams();
  const [slip, setSlip] = useState<WorkerPayslipDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [showDispute, setShowDispute] = useState(false);
  const [reasons, setReasons] = useState<DisputeReason[]>([]);
  const [reasonCode, setReasonCode] = useState("");
  const [description, setDescription] = useState("");
  const [submittingDispute, setSubmittingDispute] = useState(false);
  const [ticketCode, setTicketCode] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchWorkerPayslip(payslipId);
        if (!cancelled) setSlip(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Không tải phiếu.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [payslipId]);

  async function onConfirm() {
    if (!slip?.can_confirm || confirming) return;
    const ok = window.confirm(
      "Xác nhận phiếu lương đúng? Sau khi xác nhận, phiếu sẽ khóa và bạn không khiếu nại được nữa.",
    );
    if (!ok) return;
    setConfirming(true);
    setActionError(null);
    try {
      const updated = await confirmWorkerPayslip(payslipId);
      setSlip(updated);
      setShowDispute(false);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Không xác nhận được phiếu.");
    } finally {
      setConfirming(false);
    }
  }

  async function openDisputeForm() {
    if (!slip?.can_dispute) return;
    setActionError(null);
    setShowDispute(true);
    if (reasons.length === 0) {
      try {
        const list = await fetchDisputeReasons();
        setReasons(list);
        if (list[0]) setReasonCode(list[0].code);
      } catch (e) {
        setActionError(e instanceof Error ? e.message : "Không tải lý do khiếu nại.");
      }
    } else if (!reasonCode && reasons[0]) {
      setReasonCode(reasons[0].code);
    }
  }

  async function onSubmitDispute(e: FormEvent) {
    e.preventDefault();
    if (!slip?.can_dispute || submittingDispute) return;
    setSubmittingDispute(true);
    setActionError(null);
    try {
      const ticket = await disputeWorkerPayslip(payslipId, reasonCode, description.trim());
      setTicketCode(ticket.code);
      setShowDispute(false);
      setDescription("");
      const updated = await fetchWorkerPayslip(payslipId);
      setSlip(updated);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Không gửi được khiếu nại.");
    } finally {
      setSubmittingDispute(false);
    }
  }

  if (error) {
    return (
      <div className="worker-page">
        <p className="worker-error">{error}</p>
        <Link to="/worker" className="worker-btn-secondary">
          ← Danh sách phiếu
        </Link>
      </div>
    );
  }

  if (!slip) {
    return (
      <div className="worker-page">
        <p className="worker-empty">Đang tải phiếu lương…</p>
      </div>
    );
  }

  return (
    <div className="worker-page worker-payslip-detail worker-payslip-genus">
      <header className="worker-detail-head">
        <Link to="/worker" className="worker-back">
          ← Phiếu lương
        </Link>
        <h1 className="worker-slip-doc-title">
          Bảng lương chi tiết tháng {periodTitle(slip.period)}
        </h1>
        <span className={`worker-status worker-status-${slip.status}`}>
          {STATUS_VI[slip.status] ?? slip.status}
        </span>
      </header>

      <WorkerPayslipHeaderGrid slip={slip} />

      <p className="worker-hint">{slip.message}</p>
      {ticketCode && (
        <p className="worker-banner">
          Đã gửi khiếu nại <strong>{ticketCode}</strong>. HR sẽ xử lý — không có chat AI trên điện thoại.
        </p>
      )}

      <WorkerPayslipSectionTable
        title="I. Ngày công — tiền lương"
        lines={slip.work_lines}
        subtotalLabel="Lương ngày công"
        subtotal={slip.work_subtotal}
      />

      <WorkerPayslipSectionTable
        title="II. Ngày nghỉ"
        lines={slip.leave_lines}
        subtotalLabel="Lương ngày nghỉ"
        subtotal={slip.leave_subtotal}
      />

      <WorkerPayslipSectionTable
        title="III. Các khoản trợ cấp"
        lines={slip.allowance_lines}
        subtotalLabel="Tổng trợ cấp"
        subtotal={slip.allowance_subtotal}
      />

      <div className="worker-slip-summary-block">
        <div className="worker-slip-summary-row">
          <span>Tổng thu nhập</span>
          <strong>{formatWorkerVnd(slip.gross)}</strong>
        </div>
      </div>

      <WorkerPayslipSectionTable
        title="IV. Các khoản khấu trừ"
        lines={slip.deduction_lines}
        subtotalLabel="Tổng khấu trừ"
        subtotal={slip.deduction_subtotal}
      />

      <div className="worker-slip-net-block" aria-label="Thực lãnh">
        <span>Thực lãnh</span>
        <strong>{formatWorkerVnd(slip.net)}</strong>
      </div>

      <section className="worker-slip-section worker-slip-al-section" aria-label="Phép năm">
        <h2 className="worker-slip-section-title">V. Phép năm</h2>
        <div className="worker-slip-al-grid">
          <div>
            <span>Phép năm hiện tại</span>
            <strong>{formatWorkerQty(slip.annual_leave_entitled)}</strong>
          </div>
          <div>
            <span>Phép năm đã dùng</span>
            <strong>{formatWorkerQty(slip.annual_leave_used)}</strong>
          </div>
          <div>
            <span>Phép năm còn lại</span>
            <strong>{formatWorkerQty(slip.annual_leave_remaining)}</strong>
          </div>
        </div>
      </section>

      {actionError && <p className="worker-error">{actionError}</p>}

      {showDispute && slip.can_dispute ? (
        <form className="worker-dispute-form" onSubmit={onSubmitDispute}>
          <h2>Gửi khiếu nại</h2>
          <label>
            Lý do
            <select
              value={reasonCode}
              onChange={(ev) => setReasonCode(ev.target.value)}
              required
            >
              {reasons.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ghi chú
            <textarea
              value={description}
              onChange={(ev) => setDescription(ev.target.value)}
              rows={4}
              minLength={3}
              maxLength={2000}
              required
              placeholder="Mô tả ngắn vấn đề (ví dụ: thiếu OT Chủ nhật)…"
            />
          </label>
          <div className="worker-actions">
            <button type="submit" className="worker-btn" disabled={submittingDispute}>
              {submittingDispute ? "Đang gửi…" : "Gửi khiếu nại"}
            </button>
            <button
              type="button"
              className="worker-btn-secondary"
              onClick={() => setShowDispute(false)}
              disabled={submittingDispute}
            >
              Hủy
            </button>
          </div>
        </form>
      ) : (
        <div className="worker-actions">
          <button
            type="button"
            className="worker-btn"
            disabled={!slip.can_confirm || confirming}
            onClick={onConfirm}
          >
            {confirming ? "Đang xác nhận…" : "Xác nhận đúng"}
          </button>
          <button
            type="button"
            className="worker-btn-secondary"
            disabled={!slip.can_dispute}
            onClick={() => void openDisputeForm()}
          >
            Khiếu nại
          </button>
        </div>
      )}

      {slip.confirm_deadline && slip.status === "published" && (
        <p className="worker-deadline">Hạn xác nhận: {formatDateDDMMYYYY(slip.confirm_deadline)}</p>
      )}
      {slip.status === "confirmed" && slip.confirmed_at && (
        <p className="worker-deadline">
          Đã khóa lúc {formatDateTimeDDMMYYYY(slip.confirmed_at)}
        </p>
      )}
    </div>
  );
}
