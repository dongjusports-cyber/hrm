type Props = {
  open: boolean;
  step: number;
  detail: string;
  moneyFields: string[];
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** P10 — modal xác nhận 1 → 2 → 3 trước khi Save tham số tiền. */
export function ConfirmThreeStepModal({
  open,
  step,
  detail,
  moneyFields,
  busy,
  onCancel,
  onConfirm,
}: Props) {
  if (!open) return null;

  const titles = ["", "Xác nhận lần 1/3", "Xác nhận lần 2/3", "Đang lưu (bước 3/3)"];
  const btnLabel =
    step >= 3 ? "Đang lưu…" : step === 2 ? "Xác nhận lần 3 — Lưu ngay" : "Tiếp tục bước 2";

  return (
    <div className="modal-backdrop" role="presentation" onClick={busy ? undefined : onCancel}>
      <div
        className="modal-card confirm-modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="confirm-title">{titles[step] ?? "Xác nhận"}</h2>
        <div className="confirm-steps" aria-hidden>
          {[1, 2, 3].map((n) => (
            <span key={n} className={`confirm-dot${n <= step ? " is-on" : ""}`}>
              {n}
            </span>
          ))}
        </div>
        <p className="modal-message">{detail}</p>
        {moneyFields.length > 0 && (
          <p className="field-hint">
            Nhóm tiền thay đổi: <strong>{moneyFields.join(", ")}</strong>
          </p>
        )}
        <div className="confirm-actions">
          <button type="button" className="btn-ghost-dark" onClick={onCancel} disabled={busy}>
            Hủy
          </button>
          <button
            type="button"
            className={`btn-primary${step === 2 ? " btn-danger-ish" : ""}`}
            onClick={onConfirm}
            disabled={busy || step >= 3}
          >
            {busy && step >= 3 ? "Đang lưu…" : btnLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
