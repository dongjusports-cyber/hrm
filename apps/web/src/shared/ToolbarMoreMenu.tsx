import { useEffect, useRef, useState, type ReactNode } from "react";

type Props = {
  label?: string;
  children: ReactNode;
  disabled?: boolean;
};

/** Menu ⋮ Thêm — gom nút phụ toolbar §23.1. */
export function ToolbarMoreMenu({ label = "⋮ Thêm", children, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <div className="toolbar-more" ref={rootRef}>
      <button
        type="button"
        className="btn-ghost-dark toolbar-more-trigger"
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
      >
        {label}
      </button>
      {open && (
        <div className="toolbar-more-panel" role="menu">
          {children}
        </div>
      )}
    </div>
  );
}
