import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import QRCode from "qrcode";

const DEFAULT_LAN_HOST = "192.168.1.123:5173";
const STORAGE_KEY = "djhrm.workerQrHost";

function loadSavedHost(): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)?.trim();
    if (saved) return saved;
  } catch {
    /* ignore */
  }
  return DEFAULT_LAN_HOST;
}

/** Chuẩn hóa IP/domain → URL đầy đủ cổng Worker login. */
export function buildWorkerLoginUrl(hostOrUrl: string): string {
  let raw = hostOrUrl.trim();
  if (!raw) raw = DEFAULT_LAN_HOST;

  // Cho phép dán sẵn full URL
  if (/^https?:\/\//i.test(raw)) {
    try {
      const u = new URL(raw);
      return `${u.origin}/worker/login`;
    } catch {
      /* fall through */
    }
  }

  // Bỏ slash thừa / path nếu Admin gõ kèm
  raw = raw.replace(/^\/+/, "").replace(/\/+$/, "");
  raw = raw.replace(/\/worker\/login\/?$/i, "");
  const hostPart = (raw.split("/")[0] || DEFAULT_LAN_HOST).trim();
  const host = /:\d+$/.test(hostPart) ? hostPart : `${hostPart}:5173`;
  return `http://${host}/worker/login`;
}

/** Trang HR/Admin xuất mã QR đăng nhập công nhân (LAN nhà máy). */
export function WorkerQrPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hostInput, setHostInput] = useState(loadSavedHost);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const loginUrl = useMemo(() => buildWorkerLoginUrl(hostInput), [hostInput]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, hostInput.trim() || DEFAULT_LAN_HOST);
    } catch {
      /* ignore */
    }
  }, [hostInput]);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    (async () => {
      try {
        if (!canvasRef.current) return;
        await QRCode.toCanvas(canvasRef.current, loginUrl, {
          width: 320,
          margin: 2,
          color: { dark: "#0a1020", light: "#ffffff" },
          errorCorrectionLevel: "M",
        });
        if (!cancelled) {
          setError(null);
          setReady(true);
        }
      } catch (e) {
        if (!cancelled) {
          setReady(false);
          setError(e instanceof Error ? e.message : "Không tạo được mã QR.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loginUrl]);

  function onPrint() {
    window.print();
  }

  function onDownload() {
    const canvas = canvasRef.current;
    if (!canvas || !ready) return;
    const link = document.createElement("a");
    link.download = "dj-hrm-worker-login-qr.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  function onResetDefault() {
    setHostInput(DEFAULT_LAN_HOST);
  }

  return (
    <div className="hr-page qr-page">
      <div className="users-head hr-list-head no-print">
        <div>
          <h1>Mã QR đăng nhập công nhân</h1>
          <p className="field-hint">
            Quét từ điện thoại trong mạng LAN nhà máy → cổng Worker.{" "}
            <Link to="/m/hr">← Về Nhân Sự</Link>
          </p>
        </div>
        <div className="qr-actions">
          <button type="button" className="btn-primary" onClick={onPrint} disabled={!ready}>
            In Mã QR
          </button>
          <button
            type="button"
            className="btn-ghost-dark"
            onClick={onDownload}
            disabled={!ready}
          >
            Tải Ảnh QR
          </button>
        </div>
      </div>

      <div className="qr-host-panel no-print">
        <label className="qr-host-field">
          <span>Địa chỉ IP / Domain</span>
          <input
            value={hostInput}
            onChange={(e) => setHostInput(e.target.value)}
            placeholder="192.168.1.123:5173"
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <button type="button" className="btn-ghost-dark" onClick={onResetDefault}>
          Mặc định LAN
        </button>
        <p className="field-hint qr-host-hint">
          Đổi IP khi máy đổi Wi-Fi — mã QR cập nhật ngay. Có thể gõ IP, IP:cổng, hoặc URL đầy đủ.
        </p>
      </div>

      {error && <p className="banner-warn no-print">{error}</p>}

      <div className="qr-print-sheet">
        <img src="/dj-logo.png" alt="DJ HRM" className="qr-brand-logo" />
        <h2>DJ HRM</h2>
        <p className="qr-subtitle">Quét để đăng nhập phiếu lương</p>
        <canvas ref={canvasRef} className="qr-canvas" />
        <p className="qr-url">{loginUrl}</p>
        <p className="qr-credit">Designed &amp; Built by NGUYỄN THANH THIỆN</p>
      </div>
    </div>
  );
}
