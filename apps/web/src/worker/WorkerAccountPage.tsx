import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PWAInstallPrompt } from "./PWAInstallPrompt";
import { workerChangePassword } from "./workerApi";
import { clearWorkerAuth, patchWorkerUser, useWorkerAuth } from "./workerAuthStore";

export function WorkerAccountPage() {
  const { worker } = useWorkerAuth();
  const navigate = useNavigate();
  const forced = Boolean(worker?.must_change_password);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      const msg = await workerChangePassword(current, next);
      patchWorkerUser({ must_change_password: false });
      setOk(msg);
      setCurrent("");
      setNext("");
      if (forced) {
        navigate("/worker", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đổi mật khẩu thất bại.");
    }
  }

  function logout() {
    clearWorkerAuth();
    navigate("/worker/login", { replace: true });
  }

  return (
    <div className="worker-page worker-home">
      <PWAInstallPrompt />
      <header className="worker-top">
        <div>
          <h1>{forced ? "Đổi mật khẩu lần đầu" : "Tài khoản"}</h1>
          <p className="worker-msnv">
            {worker?.full_name} · MSNV {worker?.employee_code}
          </p>
        </div>
        {!forced && (
          <Link to="/worker" className="worker-btn-secondary">
            ← Phiếu lương
          </Link>
        )}
      </header>

      {forced && (
        <p className="worker-banner">
          Lần đầu đăng nhập: hãy đặt mật khẩu mới (ít nhất 8 ký tự), khác 4 số cuối CCCD/MSNV, rồi
          mới xem phiếu lương.
        </p>
      )}

      <form className="worker-card" onSubmit={onSubmit}>
        <label className="worker-field">
          <span>Mật khẩu hiện tại</span>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <label className="worker-field">
          <span>Mật khẩu mới (≥ 6 ký tự)</span>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            minLength={6}
            autoComplete="new-password"
            required
          />
        </label>
        {error && <p className="worker-error">{error}</p>}
        {ok && <p className="worker-ok">{ok}</p>}
        <button type="submit" className="worker-btn">
          {forced ? "Lưu mật khẩu & tiếp tục" : "Đổi mật khẩu"}
        </button>
        <button type="button" className="worker-btn-secondary" onClick={logout}>
          Đăng xuất
        </button>
      </form>
    </div>
  );
}
