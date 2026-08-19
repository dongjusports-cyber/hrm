import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useState,
  type ReactNode,
} from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../shared/authStore";
import { showDenied } from "../../shared/deniedStore";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";

const SetHrHeaderRight = createContext<((node: ReactNode | null) => void) | null>(null);

/** Gắn nút góc phải thanh trên (Portal / Nhân Sự). Tự gỡ khi rời trang. */
export function useHrHeaderRight(node: ReactNode | null) {
  const setRight = useContext(SetHrHeaderRight);
  useLayoutEffect(() => {
    if (!setRight) return;
    setRight(node);
    const t = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 0);
    return () => {
      window.clearTimeout(t);
      setRight(null);
    };
  }, [setRight, node]);
}

export function HrLayout({ children }: { children?: ReactNode }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [headerRight, setHeaderRight] = useState<ReactNode | null>(null);
  const allowed = user?.role === "admin" || (user?.modules.includes("hr") ?? false);

  useHrSubpageEsc({ backTo: "/m/hr" });

  useEffect(() => {
    if (user && !allowed) {
      showDenied(user.full_name);
      navigate("/", { replace: true });
    }
  }, [user, allowed, navigate]);

  if (!allowed) return null;

  return (
    <SetHrHeaderRight.Provider value={setHeaderRight}>
      <div className="module-page hr-shell">
        <header className="module-header hr-layer-header">
          <div className="hr-layer-left">
            <Link to="/" className="hr-layer-btn">
              ← Portal
            </Link>
            <Link to="/m/hr" className="hr-layer-btn">
              Nhân Sự
            </Link>
          </div>
          <div className="hr-layer-right">{headerRight}</div>
        </header>
        <main className="module-body module-body-wide hr-shell-body">
          {children ?? <Outlet />}
        </main>
      </div>
    </SetHrHeaderRight.Provider>
  );
}
