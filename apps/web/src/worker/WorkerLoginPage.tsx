import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { PWAInstallPrompt } from "./PWAInstallPrompt";
import { workerLogin } from "./workerApi";
import { useWorkerAuth } from "./workerAuthStore";

/** Đăng nhập công nhân — Dark Glass, font/nút lớn trên điện thoại. */
export function WorkerLoginPage() {
  const { accessToken } = useWorkerAuth();
  const navigate = useNavigate();
  const [msnv, setMsnv] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (accessToken) return <Navigate to="/worker" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const worker = await workerLogin(msnv.trim(), password);
      if (worker.must_change_password) {
        navigate("/worker/account", { replace: true });
      } else {
        navigate("/worker", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page login-titan">
      <div className="login-orb login-orb-blue" aria-hidden />
      <div className="login-orb login-orb-amber" aria-hidden />

      <div className="login-stack">
        <PWAInstallPrompt />

        <form className="login-card" onSubmit={onSubmit}>
          <div className="login-logo-wrap">
            <img className="login-logo-img" src="/dj-logo.png" alt="DJ" />
          </div>
          <p className="login-app-name">DJ HRM — Công nhân</p>

          <label className="login-field">
            <span>Mã số nhân viên (MSNV)</span>
            <input
              value={msnv}
              onChange={(e) => setMsnv(e.target.value)}
              inputMode="numeric"
              autoComplete="username"
              placeholder="Nhập MSNV"
              required
            />
          </label>

          <label className="login-field">
            <span>Mật khẩu</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="Lần đầu: 1234"
              required
            />
          </label>

          <p className="login-hint">
            Lần đầu đăng nhập dùng mật khẩu <strong>1234</strong>, hệ thống sẽ yêu cầu đổi mật khẩu
            mới.
          </p>

          {error && <p className="login-error">{error}</p>}

          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>

          <footer className="login-credit">
            <p>Designed &amp; Built by NGUYỄN THANH THIỆN</p>
          </footer>
        </form>
      </div>
    </div>
  );
}
