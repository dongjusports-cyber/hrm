import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { changePasswordRequest } from "../shared/api";
import { clearAuth, useAuth } from "../shared/authStore";

/** Bắt buộc đổi mật khẩu lần đầu (staff) — Dark Glass đồng bộ Login. */
export function ForceChangePasswordPage() {
  const { accessToken, user } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }
  if (!user?.must_change_password) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await changePasswordRequest(current, next);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đổi mật khẩu thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page login-titan">
      <div className="login-orb login-orb-blue" aria-hidden />
      <div className="login-orb login-orb-amber" aria-hidden />

      <form className="login-card" onSubmit={onSubmit}>
        <div className="login-logo-wrap">
          <img className="login-logo-img" src="/dj-logo.png" alt="DJ" />
        </div>

        <p className="login-hint">
          Xin chào {user.full_name}. Đặt mật khẩu mới (≥ 8 ký tự) trước khi vào Portal.
        </p>

        <label className="login-field">
          <span>Mật khẩu hiện tại</span>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        <label className="login-field">
          <span>Mật khẩu mới</span>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>

        {error && <p className="login-error">{error}</p>}

        <button type="submit" className="login-submit" disabled={loading}>
          {loading ? "Đang lưu…" : "Lưu mật khẩu mới"}
        </button>

        <button
          type="button"
          className="login-link-btn"
          onClick={() => {
            clearAuth();
            navigate("/login", { replace: true });
          }}
        >
          Đăng xuất
        </button>

        <footer className="login-credit">
          <p>Designed &amp; Built by NGUYỄN THANH THIỆN</p>
        </footer>
      </form>
    </div>
  );
}
