import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  askAi,
  assignDispute,
  closeDispute,
  fetchDisputes,
  type DisputeTicket,
} from "../../shared/api";
import { formatDateTimeDDMMYYYY } from "../../shared/formatDate";
import { useAuth } from "../../shared/authStore";
import { ModuleLayerHeader } from "../../shared/ModuleLayerHeader";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";

const STATUS_VI: Record<string, string> = {
  open: "Mở",
  ai_reviewed: "AI đã rà — chờ HR",
  hr_pending: "HR đang xử lý",
  closed: "Đã đóng",
};

const PAYSLIP_VI: Record<string, string> = {
  disputed: "Đang khiếu nại",
  resolved: "Đã xử lý (có thể phát hành lại)",
  published: "Đã phát hành lại",
  confirmed: "CN đã xác nhận",
};

type Filter = "open" | "all" | "closed";

/** P4.4 inbox + P4.5 rà soát AI (ai_query). */
export function DisputePage() {
  useHrSubpageEsc({ backTo: "/" });
  const { user } = useAuth();
  const canQuery = Boolean(user?.permissions?.includes("ai_query") || user?.role === "admin");
  const [filter, setFilter] = useState<Filter>("open");
  const [rows, setRows] = useState<DisputeTicket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [aiAnswers, setAiAnswers] = useState<Record<string, string>>({});

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const status =
        filter === "open" ? "open" : filter === "closed" ? "closed" : undefined;
      const list = await fetchDisputes(status);
      setRows(list);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải khiếu nại.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onAssign(id: string) {
    setBusyId(id);
    setOk(null);
    try {
      await assignDispute(id);
      setOk("Đã gán cho bạn xử lý.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không gán được.");
    } finally {
      setBusyId(null);
    }
  }

  async function onAiReview(id: string, code: string) {
    if (!canQuery) return;
    setBusyId(id);
    setOk(null);
    setError(null);
    try {
      const res = await askAi(`Rà soát khiếu nại ${code}`, id);
      setAiAnswers((prev) => ({ ...prev, [id]: res.answer }));
      setOk(res.message);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không rà soát AI được.");
    } finally {
      setBusyId(null);
    }
  }

  async function onClose(id: string) {
    const note = (notes[id] ?? "").trim();
    if (!window.confirm("Đóng khiếu nại này? Phiếu lương sẽ chuyển sang trạng thái đã xử lý.")) {
      return;
    }
    setBusyId(id);
    setOk(null);
    try {
      const closed = await closeDispute(id, note);
      setOk(
        `Đã đóng ${closed.code}. Phiếu kỳ ${closed.period} → resolved — có thể Phát hành lại ở ô Tính Lương nếu cần.`,
      );
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không đóng được.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="module-page">
      <ModuleLayerHeader
        layers={[
          { label: "← Portal", to: "/" },
          { label: "Khiếu Nại", current: true },
        ]}
      />

      <main className="module-body">
        <div className="module-toolbar">
          <h1>Khiếu Nại</h1>
          <button type="button" className="btn-secondary" onClick={() => void reload()}>
            Làm mới
          </button>
        </div>
        <p className="field-hint">
          Hộp thư khiếu nại công nhân. Trợ Lý AI không tự đóng khiếu nại. Nút rà soát AI chỉ hiện khi có
          quyền <code>ai_query</code>.
        </p>

        <div className="dispute-filters" role="tablist" aria-label="Lọc khiếu nại">
          {(
            [
              ["open", "Đang mở"],
              ["closed", "Đã đóng"],
              ["all", "Tất cả"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={filter === key}
              className={filter === key ? "btn-primary" : "btn-secondary"}
              onClick={() => setFilter(key)}
            >
              {label}
            </button>
          ))}
        </div>

        {error && <p className="banner-warn">{error}</p>}
        {ok && <p className="banner-ok">{ok}</p>}

        {loading ? (
          <p className="field-hint">Đang tải…</p>
        ) : rows.length === 0 ? (
          <p className="field-hint">Không có khiếu nại trong bộ lọc này.</p>
        ) : (
          <ul className="dispute-list">
            {rows.map((d) => {
              const open = d.status !== "closed";
              const busy = busyId === d.id;
              return (
                <li key={d.id} className="dispute-card">
                  <div className="dispute-card-head">
                    <strong>{d.code}</strong>
                    <span className={`dispute-status dispute-status-${d.status}`}>
                      {STATUS_VI[d.status] ?? d.status}
                    </span>
                  </div>
                  <p>
                    {d.employee_name} · MSNV {d.employee_code} · Kỳ {d.period}
                  </p>
                  <p>
                    <strong>{d.reason_label}</strong>
                  </p>
                  <p className="dispute-desc">{d.description}</p>
                  <p className="field-hint">
                    Phiếu: {PAYSLIP_VI[d.payslip_status] ?? d.payslip_status}
                    {d.assigned_user_name ? ` · Phụ trách: ${d.assigned_user_name}` : " · Chưa gán"}
                    {d.created_at
                      ? ` · ${formatDateTimeDDMMYYYY(d.created_at)}`
                      : ""}
                  </p>
                  {d.hr_note && (
                    <p className="field-hint">
                      Ghi chú HR: {d.hr_note}
                    </p>
                  )}
                  {(aiAnswers[d.id] || d.ai_summary) && (
                    <pre className="ai-fab-answer dispute-ai-summary">
                      {aiAnswers[d.id] || d.ai_summary}
                    </pre>
                  )}
                  <div className="dispute-actions">
                    {open && (
                      <label className="dispute-note">
                        Ghi chú đóng (tuỳ chọn)
                        <input
                          type="text"
                          value={notes[d.id] ?? ""}
                          onChange={(e) =>
                            setNotes((prev) => ({ ...prev, [d.id]: e.target.value }))
                          }
                          placeholder="Ví dụ: đã đối chiếu chấm công…"
                          disabled={busy}
                        />
                      </label>
                    )}
                    <div className="dispute-action-btns">
                      {canQuery && open && (
                        <button
                          type="button"
                          className="btn-secondary"
                          disabled={busy}
                          onClick={() => void onAiReview(d.id, d.code)}
                        >
                          Rà soát bằng AI
                        </button>
                      )}
                      {open && (
                        <>
                          <button
                            type="button"
                            className="btn-secondary"
                            disabled={busy}
                            onClick={() => void onAssign(d.id)}
                          >
                            {d.assigned_user_id ? "Gán lại cho tôi" : "Nhận xử lý"}
                          </button>
                          <button
                            type="button"
                            className="btn-primary"
                            disabled={busy}
                            onClick={() => void onClose(d.id)}
                          >
                            Đóng khiếu nại
                          </button>
                        </>
                      )}
                      <Link to="/m/payroll" className="btn-secondary">
                        Mở Tính Lương
                      </Link>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </div>
  );
}
