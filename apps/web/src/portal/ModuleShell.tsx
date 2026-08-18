import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../shared/authStore";
import { showDenied } from "../shared/deniedStore";

const MODULE_TITLES: Record<string, string> = {
  overview: "Tổng Quan",
  hr: "Nhân Sự",
  timekeeping: "Chấm Công",
  payroll: "Tính Lương",
  insurance: "Bảo Hiểm",
  report: "Báo Cáo / KPI",
  dispute: "Khiếu Nại",
  config: "Cấu Hình",
};

/**
 * Lv2 placeholder — full màn + nút ← Portal.
 * Vào URL trực tiếp khi không quyền → popup + quay Portal.
 */
export function ModuleShell() {
  const { moduleKey = "" } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const title = MODULE_TITLES[moduleKey] ?? moduleKey;
  const allowed =
    user?.role === "admin" ||
    (moduleKey !== "config" && (user?.modules.includes(moduleKey) ?? false));

  useEffect(() => {
    if (user && !allowed) {
      showDenied(user.full_name);
      navigate("/", { replace: true });
    }
  }, [user, allowed, navigate]);

  if (!allowed) {
    return null;
  }

  return (
    <div className="module-page">
      <header className="module-header">
        <Link to="/" className="btn-back" aria-label="Về Portal">
          ← Portal
        </Link>
        <nav className="breadcrumb" aria-label="Đường dẫn">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <span>{title}</span>
        </nav>
      </header>

      <main className="module-body">
        <h1>{title}</h1>
        <p className="module-placeholder">
          Màn hình Lv2 đang trống — sẽ được dựng theo Hiến pháp ở các phiên tiếp theo.
        </p>
        <p className="module-key">
          Mã module: <code>{moduleKey}</code>
        </p>
      </main>
    </div>
  );
}
