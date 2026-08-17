import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { fetchWorkerMe, submitWorkerPunch } from "./workerApi";
import { useWorkerAuth } from "./workerAuthStore";

async function sha256Hex(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function previewUrl(file: File): string {
  return URL.createObjectURL(file);
}

function getPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Điện thoại không hỗ trợ GPS."));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, () => {
      reject(new Error("Bật vị trí (GPS) để chấm công tại nhà máy."));
    }, { enableHighAccuracy: true, timeout: 20_000, maximumAge: 10_000 });
  });
}

export function WorkerPunchPage() {
  const { worker } = useWorkerAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [verifyCode, setVerifyCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    void fetchWorkerMe()
      .catch(() => null)
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  if (ready && worker && worker.can_mobile_punch === false) {
    return <Navigate to="/worker" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    setVerifyCode(null);
    try {
      if (!file) throw new Error("Chụp mặt để lấy mã xác minh.");
      const photo_hash = await sha256Hex(file);
      let latitude: number | undefined;
      let longitude: number | undefined;
      let accuracy_m: number | undefined;
      if (worker?.gps_required) {
        const pos = await getPosition();
        latitude = pos.coords.latitude;
        longitude = pos.coords.longitude;
        accuracy_m = pos.coords.accuracy;
      }
      const result = await submitWorkerPunch({
        latitude,
        longitude,
        accuracy_m,
        photo_hash,
        device_id: navigator.userAgent.slice(0, 64),
      });
      setOk(result.detail);
      setVerifyCode(result.verify_code);
      setFile(null);
      if (preview) URL.revokeObjectURL(preview);
      setPreview(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chấm công thất bại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="worker-page">
      <header className="worker-top">
        <div>
          <p className="worker-hello">Chấm công</p>
          <h1>{worker?.full_name}</h1>
          <p className="worker-msnv">MSNV {worker?.employee_code}</p>
        </div>
        <Link to="/worker" className="worker-btn-secondary">
          Về trang chủ
        </Link>
      </header>

      <p className="worker-empty">
        Ảnh chỉ dùng trên máy bạn để tạo mã. Máy chủ nhận mã xác minh (~64 ký tự), không nhận file ảnh.
      </p>

      <form className="worker-section worker-leave-form" onSubmit={(ev) => void onSubmit(ev)}>
        <h2>Chụp mặt lấy mã</h2>
        <label>
          Camera trước
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="user"
            required
            onChange={(ev) => {
              const next = ev.target.files?.[0] ?? null;
              if (preview) URL.revokeObjectURL(preview);
              setFile(next);
              setPreview(next ? previewUrl(next) : null);
            }}
          />
        </label>
        {preview ? (
          <img className="worker-punch-preview" src={preview} alt="Xem trên máy, không gửi lên server" />
        ) : null}
        {error && <p className="worker-error">{error}</p>}
        {ok && <p className="worker-banner">{ok}</p>}
        {verifyCode && (
          <p className="worker-verify-code" aria-label="Mã xác minh">
            {verifyCode}
          </p>
        )}
        <button type="submit" className="worker-btn-primary" disabled={busy}>
          {busy ? "Đang gửi mã…" : "Chấm công"}
        </button>
      </form>
    </div>
  );
}
