import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchWorkerPayslips, type WorkerPayslipListItem } from "./workerApi";
import { clearWorkerAuth, useWorkerAuth } from "./workerAuthStore";
import { PWAInstallPrompt } from "./PWAInstallPrompt";

const STATUS_VI: Record<string, string> = {
  published: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  disputed: "Đang khiếu nại",
  resolved: "Đã xử lý",
  expired: "Hết hạn xác nhận",
};

function formatVnd(v: string | number): string {
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("vi-VN") + " đ";
}

/** Trang chủ worker — danh sách phiếu đã phát hành. Không AI. */
export function WorkerHomePage() {
  const { worker } = useWorkerAuth();
  const navigate = useNavigate();
  const [payslips, setPayslips] = useState<WorkerPayslipListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchWorkerPayslips();
        if (!cancelled) setPayslips(list);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được phiếu lương.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function logout() {
    clearWorkerAuth();
    navigate("/worker/login", { replace: true });
  }

  return (
    <div className="worker-page worker-home">
      <PWAInstallPrompt />
      <header className="worker-top">
        <div>
          <p className="worker-hello">Xin chào</p>
          <h1>{worker?.full_name}</h1>
          <p className="worker-msnv">MSNV {worker?.employee_code}</p>
        </div>
        <button type="button" className="worker-btn-secondary" onClick={logout}>
          Đăng xuất
        </button>
      </header>

      {worker?.must_change_password && (
        <p className="worker-banner">
          Bạn nên đổi mật khẩu lần đầu.{" "}
          <Link to="/worker/account">Đổi mật khẩu</Link>
        </p>
      )}

      {error && <p className="worker-error">{error}</p>}

      <section className="worker-section">
        <h2>Phiếu lương</h2>
        {loading ? (
          <p className="worker-empty">Đang tải…</p>
        ) : payslips.length === 0 ? (
          <p className="worker-empty">
            Chưa có phiếu lương phát hành. Khi HR bấm Phát hành ở ô Tính Lương, phiếu sẽ hiện tại đây.
          </p>
        ) : (
          <ul className="worker-payslip-list">
            {payslips.map((p) => (
              <li key={p.id}>
                <Link to={`/worker/payslips/${p.id}`} className="worker-payslip-card">
                  <div>
                    <strong>Tháng {p.period}</strong>
                    <span className={`worker-status worker-status-${p.status}`}>
                      {STATUS_VI[p.status] ?? p.status}
                    </span>
                  </div>
                  <p className="worker-net-preview">{formatVnd(p.net)}</p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <nav className="worker-nav">
        <Link to="/worker/leave" className="worker-btn-primary">
          Xin nghỉ phép
        </Link>
        <Link to="/worker/account" className="worker-btn-secondary">
          Tài khoản
        </Link>
      </nav>
    </div>
  );
}
