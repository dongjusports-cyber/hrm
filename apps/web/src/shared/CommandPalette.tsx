import { useCallback, useEffect, useMemo, useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import { fetchEmployees, type Employee } from "./api";
import {
  getPinnedScreens,
  isPinned,
  togglePinned,
  type PinnedScreen,
} from "./pinnedScreens";
import { useEscLayer } from "./useEscLayer";

type CommandItem = {
  id: string;
  label: string;
  hint?: string;
  to: string;
  pinId: string;
};

const ROUTES: CommandItem[] = [
  { id: "portal", label: "Portal", to: "/", pinId: "portal" },
  { id: "hr", label: "Nhân Sự", to: "/m/hr", pinId: "hr" },
  { id: "hr-all", label: "Danh sách nhân viên", to: "/m/hr/lists/all", pinId: "hr-all" },
  { id: "hr-contracts", label: "Hợp đồng lao động", to: "/m/hr/contracts", pinId: "hr-contracts" },
  { id: "hr-annual-leave", label: "Phép năm", to: "/m/hr/annual-leave", pinId: "hr-annual-leave" },
  { id: "hr-family", label: "Thân nhân & giảm trừ", to: "/m/hr/family", pinId: "hr-family" },
  { id: "hr-movements", label: "Biến động HR", to: "/m/hr/movements", pinId: "hr-movements" },
  { id: "hr-resign", label: "Thôi việc", to: "/m/hr/resignation", pinId: "hr-resign" },
  { id: "timekeeping", label: "Chấm Công", to: "/m/timekeeping", pinId: "timekeeping" },
  { id: "payroll", label: "Tính Lương", to: "/m/payroll", pinId: "payroll" },
  { id: "insurance", label: "Bảo Hiểm Thuế", to: "/m/insurance", pinId: "insurance" },
  { id: "overview", label: "Tổng Quan", to: "/m/overview", pinId: "overview" },
  { id: "config", label: "Cấu Hình", to: "/m/config", pinId: "config" },
];

/** Bảng lệnh Ctrl+K — đi tới màn, ghim yêu thích (5.7). */
export function CommandPalette() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [pinned, setPinned] = useState<PinnedScreen[]>(() => getPinnedScreens());

  useEscLayer(open, () => setOpen(false));

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    }
    function onOpenCmdk() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("djhrm:open-cmdk", onOpenCmdk);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("djhrm:open-cmdk", onOpenCmdk);
    };
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    setPinned(getPinnedScreens());
    void fetchEmployees()
      .then(setEmployees)
      .catch(() => setEmployees([]));
  }, [open]);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      const pinnedHits = pinned
        .map(
          (p): CommandItem => ({
            id: `pin-${p.id}`,
            label: p.label,
            hint: "Đã ghim",
            to: p.href,
            pinId: p.id,
          }),
        )
        .slice(0, 8);
      const rest = ROUTES.filter((r) => !pinned.some((p) => p.href === r.to)).slice(0, 8);
      return [...pinnedHits, ...rest];
    }

    const routeHits = ROUTES.filter(
      (r) => r.label.toLowerCase().includes(q) || r.id.includes(q),
    );
    const empHits = employees
      .filter(
        (e) =>
          e.employee_code.toLowerCase().includes(q) ||
          e.full_name.toLowerCase().includes(q),
      )
      .slice(0, 8)
      .map(
        (e): CommandItem => ({
          id: `emp-${e.id}`,
          label: `${e.employee_code} — ${e.full_name}`,
          hint: "Mở hồ sơ NV",
          to: `/m/hr/employees/${e.id}`,
          pinId: `emp-${e.id}`,
        }),
      );
    return [...empHits, ...routeHits].slice(0, 14);
  }, [query, employees, pinned]);

  const go = useCallback(
    (to: string) => {
      setOpen(false);
      navigate(to);
    },
    [navigate],
  );

  function onTogglePin(item: CommandItem, e: MouseEvent<HTMLButtonElement>) {
    e.stopPropagation();
    const next = togglePinned({ id: item.pinId, label: item.label, href: item.to });
    setPinned(next);
    window.dispatchEvent(new Event("djhrm:pinned-changed"));
  }

  if (!open) return null;

  return (
    <div className="cmdk-backdrop" role="presentation" onClick={() => setOpen(false)}>
      <div
        className="cmdk-panel"
        role="dialog"
        aria-label="Bảng lệnh"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          className="cmdk-input"
          autoFocus
          placeholder="Gõ tên màn hoặc MSNV… (Ctrl+K đóng)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && items[0]) go(items[0].to);
          }}
        />
        <ul className="cmdk-list">
          {items.length === 0 && <li className="module-placeholder">Không có kết quả.</li>}
          {items.map((item) => (
            <li key={item.id} className="cmdk-row">
              <button type="button" className="cmdk-item" onClick={() => go(item.to)}>
                <span>{item.label}</span>
                {item.hint && <small>{item.hint}</small>}
              </button>
              {!item.id.startsWith("emp-") && (
                <button
                  type="button"
                  className="cmdk-pin"
                  title={isPinned(item.to) ? "Bỏ ghim" : "Ghim màn"}
                  aria-label={isPinned(item.to) ? "Bỏ ghim" : "Ghim màn"}
                  onClick={(e) => onTogglePin(item, e)}
                >
                  {isPinned(item.to) ? "★" : "☆"}
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
