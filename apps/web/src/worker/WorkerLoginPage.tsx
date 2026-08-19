import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PWAInstallPrompt } from "./PWAInstallPrompt";
import { fetchWorkerMe, workerLogin } from "./workerApi";
import { clearWorkerAuth, useWorkerAuth } from "./workerAuthStore";
import { workerLoginGate } from "./workerLoginGate";

/** Đăng nhập công nhân — Dark Glass, font/nút lớn trên điện thoại. */
export function WorkerLoginPage() {
  const { accessToken, worker } = useWorkerAuth();
  const navigate = useNavigate();
  const [msnv, setMsnv] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const gate = workerLoginGate(accessToken);

  useEffect(() => {
    function resetFields() {
      setMsnv("");
      setPassword("");
    }
    function onPageShow(e: PageTransitionEvent) {
      resetFields();
      if (e.persisted) setError(null);
    }
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, []);

  useEffect(() => {
    if (gate !== "confirm-session") return;
    void fetchWorkerMe().catch(() => {
      clearWorkerAuth();
    });
  }, [gate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const next = await workerLogin(msnv.trim(), password);
      setMsnv("");
      setPassword("");
      if (next.must_change_password) {
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

  function enterExisting() {
    if (worker?.must_change_password) {
      navigate("/worker/account", { replace: true });
      return;
    }
    navigate("/worker", { replace: true });
  }

  function notMe() {
    clearWorkerAuth();
    setMsnv("");
    setPassword("");
    setError(null);
  }

  return (
    <div className="login-page login-titan">
      <div className="login-orb login-orb-blue" aria-hidden />
      <div className="login-orb login-orb-amber" aria-hidden />

      <div className="login-stack">
        <PWAInstallPrompt />

        {gate === "confirm-session" && worker ? (
          <div className="login-card">
            <div className="login-logo-wrap">
              <img className="login-logo-img" src="/dj-logo.png" alt="DJ" />
            </div>
            <p className="login-app-name">DJ HRM — Công nhân</p>
            <p className="login-hint">Điện thoại này đang mở tài khoản</p>
            <h1 className="login-resume-name">{worker.full_name}</h1>
            <p className="login-resume-msnv">MSNV {worker.employee_code}</p>
            <button type="button" className="login-submit" onClick={enterExisting}>
              Vào tài khoản này
            </button>
            <button type="button" className="login-resume-other" onClick={notMe}>
              Không phải tôi — đăng nhập khác
            </button>
            <footer className="login-credit">
              <p>Designed &amp; Built by NGUYỄN THANH THIỆN</p>
            </footer>
          </div>
        ) : (
          <form className="login-card" onSubmit={onSubmit} autoComplete="off">
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
                name="djhrm-worker-msnv"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
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
                name="djhrm-worker-password"
                autoComplete="new-password"
                placeholder="Lần đầu: 4 số cuối CCCD"
                required
              />
            </label>

            <p className="login-hint">
              Lần đầu đăng nhập dùng <strong>4 số cuối CCCD</strong> (nếu chưa có CCCD:{" "}
              <strong>4 số cuối MSNV</strong>). Hệ thống sẽ yêu cầu đổi mật khẩu mới.
            </p>
            {typeof window !== "undefined" && window.location.hostname !== "localhost" && (
              <p className="login-hint login-hint-muted">
                Đang mở qua <strong>{window.location.host}</strong> — đúng cho điện thoại trong LAN.
              </p>
            )}
            {typeof window !== "undefined" && window.location.hostname === "localhost" && (
              <p className="login-hint login-hint-warn">
                Trên điện thoại không dùng <strong>localhost</strong>. Mở{" "}
                <strong>http://192.168.1.123:5173/worker/login</strong> (IP máy HR, cùng WiFi).
              </p>
            )}

            {error && <p className="login-error">{error}</p>}

            <button type="submit" className="login-submit" disabled={loading}>
              {loading ? "Đang đăng nhập…" : "Đăng nhập"}
            </button>

            <footer className="login-credit">
              <p>Designed &amp; Built by NGUYỄN THANH THIỆN</p>
            </footer>
          </form>
        )}
      </div>
    </div>
  );
}
