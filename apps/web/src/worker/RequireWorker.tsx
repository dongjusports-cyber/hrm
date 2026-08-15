import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useWorkerAuth } from "./workerAuthStore";
import { useWorkerSurface } from "./useWorkerSurface";

export function RequireWorker({ children }: { children: ReactNode }) {
  const { accessToken, worker } = useWorkerAuth();
  const location = useLocation();
  useWorkerSurface();

  if (!accessToken) return <Navigate to="/worker/login" replace />;

  // Bắt buộc đổi mật khẩu lần đầu trước khi dùng phiếu lương
  if (
    worker?.must_change_password &&
    location.pathname !== "/worker/account"
  ) {
    return <Navigate to="/worker/account" replace />;
  }

  return <>{children}</>;
}
