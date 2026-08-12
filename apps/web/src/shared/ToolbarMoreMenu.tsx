import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

type Props = {
  label?: string;
  children: ReactNode;
  disabled?: boolean;
};

type Coords = { top: number; right: number };

/**
 * Menu ⋮ Thêm — gom nút phụ toolbar §23.1.
 * Panel render qua portal (position:fixed, neo theo nút) để KHÔNG bị
 * `overflow` của toolbar (overflow-y:hidden, max-height:46px) cắt mất.
 */
export function ToolbarMoreMenu({ label = "⋮ Thêm", children, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<Coords | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const reposition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setCoords({
      top: r.bottom + 4,
      right: Math.max(8, window.innerWidth - r.right),
    });
  }, []);

  useLayoutEffect(() => {
    if (open) reposition();
  }, [open, reposition]);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t)) return;
      if (panelRef.current?.contains(t)) return;
      setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", reposition);
    // capture=true để bắt cả scroll trong toolbar (overflow-x:auto)
    window.addEventListener("scroll", reposition, true);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
    };
  }, [open, reposition]);

  return (
    <div className="toolbar-more">
      <button
        ref={triggerRef}
        type="button"
        className="btn-ghost-dark toolbar-more-trigger"
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
      >
        {label}
      </button>
      {open &&
        coords &&
        createPortal(
          <div
            ref={panelRef}
            className="toolbar-more-panel toolbar-more-panel--floating"
            role="menu"
            style={{ position: "fixed", top: coords.top, right: coords.right, zIndex: 1000 }}
          >
            {children}
          </div>,
          document.body,
        )}
    </div>
  );
}
