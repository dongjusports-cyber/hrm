import { useEffect, useState, type FormEvent } from "react";
import {
  fetchDepartments,
  fetchMobilePunchSettings,
  updateMobilePunchSettings,
  type Department,
  type MobilePunchSettings,
} from "../../shared/api";
import { ConfigTabNav } from "./ConfigTabNav";

export function MobilePunchSettingsPage() {
  const [settings, setSettings] = useState<MobilePunchSettings | null>(null);
  const [depts, setDepts] = useState<Department[]>([]);
  const [mode, setMode] = useState<MobilePunchSettings["mode"]>("allowlist");
  const [codes, setCodes] = useState<string[]>(["03"]);
  const [extra, setExtra] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [radius, setRadius] = useState(200);
  const [requirePhoto, setRequirePhoto] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const [s, d] = await Promise.all([fetchMobilePunchSettings(), fetchDepartments()]);
        setSettings(s);
        setDepts(d);
        setMode(s.mode);
        setCodes(s.department_codes.length ? s.department_codes : ["03"]);
        setExtra(s.extra_msnv.join(", "));
        setLat(s.gps_lat == null ? "" : String(s.gps_lat));
        setLng(s.gps_lng == null ? "" : String(s.gps_lng));
        setRadius(s.gps_radius_m);
        setRequirePhoto(s.require_photo);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tải cấu hình.");
      }
    })();
  }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const extraList = extra
        .split(/[,;\s]+/)
        .map((x) => x.trim())
        .filter(Boolean);
      const hasGps = lat.trim() !== "" && lng.trim() !== "";
      const s = await updateMobilePunchSettings({
        mode,
        department_codes: codes,
        extra_msnv: extraList,
        gps_radius_m: radius,
        require_photo: requirePhoto,
        ...(hasGps
          ? { gps_lat: Number(lat), gps_lng: Number(lng) }
          : { clear_gps: true }),
      });
      setSettings(s);
      setOk(
        s.mode === "all"
          ? "Đã mở chấm công điện thoại cho tất cả bộ phận."
          : s.mode === "off"
            ? "Đã tắt chấm công điện thoại."
            : "Đã lưu — chỉ bộ phận được chọn (và MSNV thêm) bấm được.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    } finally {
      setBusy(false);
    }
  }

  function toggleCode(code: string) {
    setCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );
  }

  return (
    <div className="config-section-page">
      <ConfigTabNav />
      <h1>Chấm công điện thoại</h1>
      <p className="module-placeholder">
        Máy vân tay giữ nguyên. App công nhân hiện nút Chấm công cho cả công ty — chỉ người
        được mở mới bấm được. Ông Định test xong: chọn «Mở tất cả».
      </p>

      <form className="config-form" onSubmit={(ev) => void onSave(ev)}>
        <fieldset className="mobile-punch-modes">
          <legend>Phạm vi</legend>
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === "allowlist"}
              onChange={() => setMode("allowlist")}
            />
            Thử nghiệm (bộ phận bên dưới)
          </label>
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === "all"}
              onChange={() => setMode("all")}
            />
            Mở tất cả
          </label>
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === "off"}
              onChange={() => setMode("off")}
            />
            Tắt
          </label>
        </fieldset>

        <fieldset>
          <legend>Bộ phận được mở (khi Thử nghiệm)</legend>
          <div className="mobile-punch-depts">
            {depts.map((d) => (
              <label key={d.id}>
                <input
                  type="checkbox"
                  checked={codes.includes(d.code)}
                  onChange={() => toggleCode(d.code)}
                  disabled={mode !== "allowlist"}
                />
                {d.code} — {d.name}
              </label>
            ))}
          </div>
        </fieldset>

        <label>
          MSNV thêm (cách nhau bằng dấu phẩy)
          <input
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder="1514, 5290"
            disabled={mode !== "allowlist"}
          />
        </label>

        <label>
          Vĩ độ nhà máy
          <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="10.8" />
        </label>
        <label>
          Kinh độ nhà máy
          <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="106.7" />
        </label>
        <label>
          Bán kính GPS (mét)
          <input
            type="number"
            min={20}
            max={5000}
            value={radius}
            onChange={(e) => setRadius(Number(e.target.value))}
          />
        </label>
        <p className="login-hint">
          Để trống tọa độ: chưa khóa GPS (văn phòng test sớm). Điền tọa độ: bắt buộc đúng nhà máy.
        </p>

        <label>
          <input
            type="checkbox"
            checked={requirePhoto}
            onChange={(e) => setRequirePhoto(e.target.checked)}
          />
          Bắt buộc chụp mặt
        </label>

        {error && <p className="worker-error">{error}</p>}
        {ok && <p className="worker-banner">{ok}</p>}
        {settings && !settings.persisted && (
          <p className="login-hint">Chưa lưu lần nào — đang dùng mặc định Main Office (03).</p>
        )}
        <button type="submit" className="worker-btn-primary" disabled={busy}>
          {busy ? "Đang lưu…" : "Lưu"}
        </button>
      </form>
    </div>
  );
}
