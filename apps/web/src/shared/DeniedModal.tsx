type Props = {
  open: boolean;
  message: string;
  onClose: () => void;
};

export function DeniedModal({ open, message, onClose }: Props) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="denied-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="denied-title">Không có quyền truy cập</h2>
        <p className="modal-message">{message}</p>
        <button type="button" className="btn-primary" onClick={onClose}>
          Đã hiểu
        </button>
      </div>
    </div>
  );
}
