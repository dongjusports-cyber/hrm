import { useEffect } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../shared/authStore";
import { showDenied } from "../../shared/deniedStore";

/** Lv2 Cấu Hình — chỉ Admin (file 02). */
export function ConfigLayout() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const allowed = user?.role === "admin";

  useEffect(() => {
    if (user && !allowed) {
      showDenied(user.full_name);
      navigate("/", { replace: true });
    }
  }, [user, allowed, navigate]);

  if (!allowed) return null;

  return (
    <div className="module-page">
      <header className="module-header">
        <Link to="/" className="btn-back" aria-label="Về Portal">
          ← Portal
        </Link>
        <nav className="breadcrumb" aria-label="Đường dẫn">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <Link to="/m/config">Cấu Hình</Link>
        </nav>
      </header>
      <main className="module-body">
        <Outlet />
      </main>
    </div>
  );
}
