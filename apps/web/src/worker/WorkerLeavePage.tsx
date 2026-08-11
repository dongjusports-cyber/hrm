import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchWorkerLeaveRequests,
  fetchWorkerLeaveTypes,
  submitWorkerLeaveRequest,
  type WorkerLeaveRequest,
  type WorkerLeaveType,
} from "./workerApi";
import { useWorkerAuth } from "./workerAuthStore";

export function WorkerLeavePage() {
  const { worker } = useWorkerAuth();
  const [leaves, setLeaves] = useState<WorkerLeaveType[]>([]);
  const [history, setHistory] = useState<WorkerLeaveRequest[]>([]);
  const [leaveCode, setLeaveCode] = useState("ALE");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function reload() {
    const [types, reqs] = await Promise.all([fetchWorkerLeaveTypes(), fetchWorkerLeaveRequests()]);
    setLeaves(types);
    setHistory(reqs);
  }

  useEffect(() => {
    void reload().catch((e) =>
      setError(e instanceof Error ? e.message : "Không tải được dữ liệu."),
    );
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setOk(null);
    try {
      await submitWorkerLeaveRequest({
        leave_type_code: leaveCode,
        from_date: fromDate,
        to_date: toDate,
        reason: reason.trim(),
        submit: true,
      });
      setOk("Đã gửi đơn — chờ HR duyệt.");
      setReason("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gửi đơn thất bại.");
    } finally {
      setLoading(false);
    }
  }

  const STATUS_VI: Record<string, string> = {
    draft: "Nháp",
    submitted: "Chờ duyệt",
    approved: "Đã duyệt",
    rejected: "Từ chối",
    cancelled: "Đã hủy",
  };

  return (
    <div className="worker-page">
      <header className="worker-top">
        <div>
          <p className="worker-hello">Xin nghỉ phép</p>
          <h1>{worker?.full_name}</h1>
          <p className="worker-msnv">MSNV {worker?.employee_code}</p>
        </div>
        <Link to="/worker" className="worker-btn-secondary">
          Về trang chủ
        </Link>
      </header>

      {error && <p className="worker-error">{error}</p>}
      {ok && <p className="worker-banner">{ok}</p>}

      <form className="worker-section worker-leave-form" onSubmit={(e) => void onSubmit(e)}>
        <h2>Gửi đơn mới</h2>
        <label>
          Loại nghỉ
          <select value={leaveCode} onChange={(e) => setLeaveCode(e.target.value)} required>
            {leaves.map((l) => (
              <option key={l.code} value={l.code}>
                {l.code} — {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Từ ngày
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} required />
        </label>
        <label>
          Đến ngày
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} required />
        </label>
        <label>
          Lý do
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
        </label>
        <button type="submit" className="worker-btn-primary" disabled={loading}>
          {loading ? "Đang gửi…" : "Gửi đơn"}
        </button>
      </form>

      <section className="worker-section">
        <h2>Đơn của tôi</h2>
        {history.length === 0 ? (
          <p className="worker-empty">Chưa có đơn nghỉ.</p>
        ) : (
          <ul className="worker-payslip-list">
            {history.map((r) => (
              <li key={r.id} className="worker-leave-item">
                <div>
                  <strong>
                    {r.leave_type_name} · {r.from_date} → {r.to_date}
                  </strong>
                  <span className={`worker-status worker-status-${r.status}`}>
                    {STATUS_VI[r.status] ?? r.status}
                  </span>
                </div>
                <p>
                  {r.total_days} ngày — {r.reason || "Không ghi lý do"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
