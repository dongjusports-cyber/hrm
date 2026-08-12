import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { setEscFallback } from "./escStack";

/**
 * Fallback ESC khi không còn overlay/tầng con:
 * - Portal / đăng nhập: bỏ qua
 * - Module Lv1 `/m/hr`: về lưới Portal `/`
 * - HR hồ sơ NV `/m/hr/employees/:id`: về lưới danh sách (mặc định Chính thức)
 * - HR lưới/con khác `/m/hr/lists/…`, `/m/hr/contracts`: về hub `/m/hr`
 * - Module khác cấp sâu: về module cha
 */
function escTarget(pathname: string): string | null {
  if (
    pathname === "/" ||
    pathname === "/login" ||
    pathname === "/change-password" ||
    pathname === "/worker/login" ||
    pathname === "/worker"
  ) {
    return null;
  }
  if (/^\/m\/[^/]+$/.test(pathname)) {
    return "/";
  }
  if (pathname.startsWith("/m/")) {
    const parts = pathname.split("/").filter(Boolean);
    if (parts[0] === "m" && parts[1] === "hr" && parts.length >= 3) {
      if (parts[2] === "employees") {
        return parts[3] === "new" ? "/m/hr" : "/m/hr/lists/active";
      }
      return "/m/hr";
    }
    if (parts.length >= 2) return `/${parts[0]}/${parts[1]}`;
  }
  if (pathname.startsWith("/worker/")) {
    return "/worker";
  }
  return null;
}

export function GlobalEscBack() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    setEscFallback(() => {
      const to = escTarget(pathname);
      if (to) navigate(to);
    });
    return () => setEscFallback(null);
  }, [navigate, pathname]);

  return null;
}
