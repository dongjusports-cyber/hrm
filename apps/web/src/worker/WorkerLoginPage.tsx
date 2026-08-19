import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PWAInstallPrompt } from "./PWAInstallPrompt";
import { fetchWorkerMe, workerLogin } from "./workerApi";
import { clearWorkerAuth, useWorkerAuth } from "./workerAuthStore";
import { workerLoginGate } from "./workerLoginGate";
import { getWorkerPhoneLock, phoneLockBlocksOtherMsnv, rememberWorkerPhoneLock } from "./workerPhoneLock";

/** Đăng nhập công nhân — Dark Glass, font/nút lớn trên điện thoại. */
export function WorkerLoginPage() {
  const { accessToken, worker } = useWorkerAuth();
  const navigate = useNavigate();
  const phoneLock = getWorkerPhoneLock();
  const [msnv, setMsnv] = useState(phoneLock?.employee_code ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const gate = workerLoginGate(accessToken);
  const lockedCode = phoneLock?.employee_code ?? null;

  useEffect(() => {
    function resetFields() {
      setMsnv(getWorkerPhoneLock()?.employee_code ?? "");
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
    const lock = getWorkerPhoneLock();
    const code = msnv.trim();
    if (phoneLockBlocksOtherMsnv(code, lock)) {
      setError(
        `Điện thoại này đã khóa với MSNV ${lock!.employee_code}. Không đăng nhập hộ người khác. Đổi máy: liên hệ HR mở khóa.`,
      );
      return;
    }
    setLoading(true);
    try {
      const next = await workerLogin(code, password);
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

  function logoutOnly() {
    rememberWorkerPhoneLock(worker);
    clearWorkerAuth();
    setMsnv(getWorkerPhoneLock()?.employee_code ?? "");
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
            <button type="button" className="login-resume-other" onClick={logoutOnly}>
              Đăng xuất
            </button>
            <p className="login-hint login-hint-muted">
              Máy này chỉ dùng cho MSNV này. Không đăng nhập hộ người khác.
            </p>
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
                readOnly={Boolean(lockedCode)}
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

            {lockedCode ? (
              <p className="login-hint">
                Điện thoại này đã khóa với <strong>MSNV {lockedCode}</strong>
                {phoneLock?.full_name ? ` (${phoneLock.full_name})` : ""}. Không đăng nhập tài khoản
                khác — tránh chấm công hộ. Đổi máy: liên hệ HR mở khóa.
              </p>
            ) : (
              <p className="login-hint">
                Lần đầu đăng nhập dùng <strong>4 số cuối CCCD</strong> (nếu chưa có CCCD:{" "}
                <strong>4 số cuối MSNV</strong>). Hệ thống sẽ yêu cầu đổi mật khẩu mới. Máy này sẽ
                gắn với MSNV đó — không đăng nhập hộ người khác.
              </p>
            )}
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
