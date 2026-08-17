import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { fetchWorkerMe, submitWorkerPunch } from "./workerApi";
import { useWorkerAuth } from "./workerAuthStore";

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Không đọc được ảnh."));
    reader.readAsDataURL(file);
  });
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
  const [photo, setPhoto] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    void fetchWorkerMe()
      .catch(() => null)
      .finally(() => setReady(true));
  }, []);

  if (ready && worker && worker.can_mobile_punch === false) {
    return <Navigate to="/worker" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      if (!photo) throw new Error("Chụp mặt để chấm công.");
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
        photo_base64: photo,
        device_id: navigator.userAgent.slice(0, 64),
      });
      setOk(result.detail);
      setPhoto(null);
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
        Máy vân tay vẫn dùng bình thường. Điện thoại chỉ ghi thêm giờ khi bạn đang ở nhà máy.
      </p>

      <form className="worker-section worker-leave-form" onSubmit={(ev) => void onSubmit(ev)}>
        <h2>Chụp mặt + vị trí</h2>
        <label>
          Ảnh mặt (camera trước)
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="user"
            required
            onChange={(ev) => {
              const file = ev.target.files?.[0];
              if (!file) {
                setPhoto(null);
                return;
              }
              void fileToDataUrl(file).then(setPhoto).catch((err: unknown) => {
                setError(err instanceof Error ? err.message : "Không đọc ảnh.");
              });
            }}
          />
        </label>
        {photo ? (
          <img className="worker-punch-preview" src={photo} alt="Ảnh sẽ gửi" />
        ) : null}
        {error && <p className="worker-error">{error}</p>}
        {ok && <p className="worker-banner">{ok}</p>}
        <button type="submit" className="worker-btn-primary" disabled={busy}>
          {busy ? "Đang gửi…" : "Chấm công"}
        </button>
      </form>
    </div>
  );
}
