import { useEffect, type ReactNode } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../shared/authStore";
import { showDenied } from "../../shared/deniedStore";

export function HrLayout({ children }: { children?: ReactNode }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const allowed = user?.role === "admin" || (user?.modules.includes("hr") ?? false);

  useEffect(() => {
    if (user && !allowed) {
      showDenied(user.full_name);
      navigate("/", { replace: true });
    }
  }, [user, allowed, navigate]);

  if (!allowed) return null;

  return (
    <div className="module-page hr-shell">
      <header className="module-header">
        <Link to="/" className="btn-back">
          ← Portal
        </Link>
        <nav className="breadcrumb">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <Link to="/m/hr">Nhân Sự</Link>
        </nav>
      </header>
      <main className="module-body module-body-wide hr-shell-body">
        {children ?? <Outlet />}
      </main>
    </div>
  );
}
