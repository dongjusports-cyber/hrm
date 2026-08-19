import { useRef, useState } from "react";
import { submitWorkerPunch } from "./workerApi";
import { getWorkerDeviceId } from "./workerDevice";
import { useWorkerAuth } from "./workerAuthStore";

async function sha256Hex(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function getPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Điện thoại không hỗ trợ GPS."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      resolve,
      () => {
        reject(new Error("Bật vị trí (GPS) để chấm công tại nhà máy."));
      },
      { enableHighAccuracy: true, timeout: 20_000, maximumAge: 10_000 },
    );
  });
}

/** Một nút Chấm công → camera trước → chụp xong gửi ngay. Không chọn tệp. */
export function WorkerFacePunchButton() {
  const { worker } = useWorkerAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [verifyCode, setVerifyCode] = useState<string | null>(null);

  if (worker?.can_mobile_punch === false) {
    return (
      <>
        <button type="button" className="worker-btn-primary" disabled>
          Chấm công
        </button>
        <p className="worker-punch-hint">
          {worker.punch_blocked_reason ||
            "Đang thử nghiệm tại Main Office. Bộ phận khác vẫn chấm bằng máy vân tay."}
        </p>
      </>
    );
  }

  function openFrontCamera() {
    setError(null);
    setOk(null);
    setVerifyCode(null);
    inputRef.current?.click();
  }

  async function sendPunch(file: File) {
    setBusy(true);
    setError(null);
    setOk(null);
    setVerifyCode(null);
    try {
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
        device_id: getWorkerDeviceId(),
      });
      setOk(result.detail);
      setVerifyCode(result.verify_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chấm công thất bại.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        className="worker-punch-camera-input"
        type="file"
        accept="image/*"
        capture="user"
        aria-hidden
        tabIndex={-1}
        onChange={(ev) => {
          const file = ev.target.files?.[0];
          if (file) void sendPunch(file);
        }}
      />
      <button type="button" className="worker-btn-primary" disabled={busy} onClick={openFrontCamera}>
        {busy ? "Đang gửi mã…" : "Chấm công"}
      </button>
      {error ? <p className="worker-error">{error}</p> : null}
      {ok ? <p className="worker-banner">{ok}</p> : null}
      {verifyCode ? (
        <p className="worker-verify-code" aria-label="Mã xác minh">
          {verifyCode}
        </p>
      ) : null}
    </>
  );
}
