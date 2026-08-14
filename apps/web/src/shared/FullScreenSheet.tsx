import { ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";
import { useEscLayer } from "./useEscLayer";

type Props = {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
  /** Nút hành động chính (vd. Lưu) — hiển thị cạnh nút đóng. */
  actions?: ReactNode;
  /** Chỉ vùng con cuộn; header/tab cố định (hồ sơ NV). */
  inFrameScroll?: boolean;
  /** Ẩn thanh tiêu đề — chrome nằm trong children (hồ sơ NV). */
  hideHeader?: boolean;
  /** Class bổ sung cho vùng body (vd. form tạo NV không cuộn). */
  bodyClassName?: string;
  /** Khi true (mặc định): ESC đóng sheet nếu không có useSheetKeyboard/onBeforeClose chặn. */
  closeOnEsc?: boolean;
  /** Trả true nếu đã xử lý ESC (chưa đóng sheet). Chỉ dùng khi `closeOnEsc`. */
  onBeforeClose?: () => boolean;
};

/** Cửa sổ nổi full màn hình — form tập trung, danh sách phía sau vẫn giữ ngữ cảnh. */
export function FullScreenSheet({
  open,
  title,
  subtitle,
  onClose,
  children,
  actions,
  inFrameScroll = false,
  hideHeader = false,
  bodyClassName,
  closeOnEsc = true,
  onBeforeClose,
}: Props) {
  useEscLayer(open && closeOnEsc, () => {
    if (onBeforeClose?.()) return;
    onClose();
  });

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="fs-sheet-backdrop" role="presentation" onClick={onClose}>
      <div
        className={hideHeader ? "fs-sheet fs-sheet--no-head" : "fs-sheet"}
        role="dialog"
        aria-modal="true"
        aria-label={hideHeader ? title : undefined}
        aria-labelledby={hideHeader ? undefined : "fs-sheet-title"}
        onClick={(e) => e.stopPropagation()}
      >
        {!hideHeader && (
          <header className="fs-sheet-head">
            <div className="fs-sheet-head-text">
              <h2 id="fs-sheet-title">{title}</h2>
              {subtitle && <p className="field-hint fs-sheet-subtitle">{subtitle}</p>}
            </div>
            <div className="fs-sheet-head-actions">
              {actions}
              <button type="button" className="btn-ghost-dark fs-sheet-close" onClick={onClose}>
                × Đóng
              </button>
            </div>
          </header>
        )}
        <div
          className={
            inFrameScroll
              ? `fs-sheet-body fs-sheet-body-shell${bodyClassName ? ` ${bodyClassName}` : ""}`
              : `fs-sheet-body${bodyClassName ? ` ${bodyClassName}` : ""}`
          }
        >
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
}
