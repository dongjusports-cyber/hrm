import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { loginRequest } from "../shared/api";
import { useAuth } from "../shared/authStore";

export function LoginPage() {
  const { accessToken, user } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (accessToken) {
    return (
      <Navigate
        to={user?.must_change_password ? "/change-password" : "/"}
        replace
      />
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await loginRequest(username.trim(), password);
      navigate(
        data.user.must_change_password ? "/change-password" : "/",
        { replace: true },
      );
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

      <form className="login-card" onSubmit={onSubmit}>
        <div className="login-logo-wrap">
          <img className="login-logo-img" src="/dj-logo.png" alt="DJ" />
        </div>

        <label className="login-field">
          <span>Tên đăng nhập</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            placeholder="Tên đăng nhập"
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
            placeholder="Mật khẩu"
            required
          />
        </label>

        {error && <p className="login-error">{error}</p>}

        <button type="submit" className="login-submit" disabled={loading}>
          {loading ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>

        <footer className="login-credit">
          <p>Designed &amp; Built by NGUYỄN THANH THIỆN</p>
        </footer>
      </form>
    </div>
  );
}
