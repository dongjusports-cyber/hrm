import { useRef, useState } from "react";
import {
  applyTransferTeam,
  previewTransferTeam,
  type Employee,
  type Team,
  type TransferTeamPreview,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { formatTeamLabel } from "../../shared/formatOrg";
import { useSheetKeyboard } from "../../shared/formFieldEsc";

function todayIso(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

/** Modal chuyển tổ hàng loạt từ lưới NV (23§145, hạng mục 1.5) — luôn xem trước trước khi lưu. */
export function TransferTeamModal({
  employees,
  teams,
  onClose,
  onDone,
}: {
  employees: Employee[];
  teams: Team[];
  onClose: () => void;
  onDone: (message: string) => void;
}) {
  const [teamId, setTeamId] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(todayIso());
  const [decisionNo, setDecisionNo] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [preview, setPreview] = useState<TransferTeamPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const formShellRef = useRef<HTMLDivElement>(null);

  useSheetKeyboard({ open: true, containerRef: formShellRef, onClose });

  function body() {
    return {
      employee_ids: employees.map((e) => e.id),
      team_id: teamId,
      effective_from: effectiveFrom,
      decision_no: decisionNo.trim() || undefined,
      reason_code: reasonCode.trim() || undefined,
    };
  }

  async function onPreview() {
    if (!teamId) {
      setError("Trợ Lý AI: chọn tổ đích trước khi xem trước.");
      return;
    }
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      setPreview(await previewTransferTeam(body()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xem trước được.");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!preview) return;
    if (
      !window.confirm(
        `Xác nhận chuyển ${preview.affected_count} nhân viên sang tổ ${preview.team_code} — ` +
          `${preview.team_name}, hiệu lực từ ${formatDateDDMMYYYY(preview.effective_from)}?\n\n` +
          (preview.skipped.length
            ? `${preview.skipped.length} NV sẽ bị loại khỏi lô (xem danh sách bên dưới).`
            : "Bấm OK để lưu."),
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await applyTransferTeam(body());
      onDone(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chuyển tổ thất bại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div ref={formShellRef} className="modal-card modal-card-wide" onClick={(e) => e.stopPropagation()}>
        <h2>Chuyển tổ hàng loạt</h2>
        <p className="field-hint">
          Đã chọn {employees.length} nhân viên. Ghi vào lịch sử đổi tổ (employee_assignments) —
          không có bảng này in lại lương cũ sẽ ra sai tổ.
        </p>

        <div className="hr-raise-grid">
          <label className="field">
            <span>Tổ đích</span>
            <select
              value={teamId}
              onChange={(e) => {
                setTeamId(e.target.value);
                setPreview(null);
              }}
            >
              <option value="">— Chọn tổ —</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {formatTeamLabel(t, { showDepartment: true })}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Ngày hiệu lực</span>
            <input
              type="date"
              value={effectiveFrom}
              max={todayIso()}
              onChange={(e) => {
                setEffectiveFrom(e.target.value);
                setPreview(null);
              }}
            />
          </label>
          <label className="field">
            <span>Số quyết định (tuỳ chọn)</span>
            <input value={decisionNo} onChange={(e) => setDecisionNo(e.target.value)} />
          </label>
          <label className="field">
            <span>Lý do (tuỳ chọn)</span>
            <input
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value)}
              placeholder="vd: tái cấu trúc, theo yêu cầu NV…"
            />
          </label>
        </div>

        {error && <p className="banner-warn">{error}</p>}

        {preview && (
          <div className="hr-raise-preview">
            <p>{preview.message}</p>
            {preview.skipped.length > 0 && (
              <table className="mini-table">
                <thead>
                  <tr>
                    <th>MSNV</th>
                    <th>Họ tên</th>
                    <th>Lý do bị loại</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.skipped.map((s, i) => (
                    <tr key={i}>
                      <td>{s.employee_code}</td>
                      <td>{s.full_name}</td>
                      <td>{s.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        <div className="hr-raise-actions">
          <button type="button" className="btn-ghost-dark" onClick={onClose} disabled={busy}>
            Đóng
          </button>
          <button type="button" className="btn-secondary" onClick={() => void onPreview()} disabled={busy || !teamId}>
            Xem trước
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={busy || !preview || preview.affected_count === 0}
            onClick={() => void onConfirm()}
          >
            Xác nhận chuyển tổ
          </button>
        </div>
      </div>
    </div>
  );
}
