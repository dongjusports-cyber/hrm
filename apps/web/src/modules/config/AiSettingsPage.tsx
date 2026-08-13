import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { fetchAiSettings, updateAiSettings, type AiSettings } from "../../shared/api";
import { ConfigTabNav } from "./ConfigTabNav";

/** Cấu Hình → AI Gemini (05§5.2) — key mã hóa at-rest / env. */
export function AiSettingsPage() {
  const [settings, setSettings] = useState<AiSettings | null>(null);
  const [enabled, setEnabled] = useState(true);
  const [modelName, setModelName] = useState("gemini-3-flash-preview");
  const [maxDay, setMaxDay] = useState(20);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const s = await fetchAiSettings();
        setSettings(s);
        setEnabled(s.enabled);
        setModelName(s.model_name);
        setMaxDay(s.max_queries_per_day);
        setMaxTokens(s.max_output_tokens);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tải cấu hình AI.");
      }
    })();
  }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const s = await updateAiSettings({
        enabled,
        model_name: modelName.trim(),
        max_queries_per_day: maxDay,
        max_output_tokens: maxTokens,
        ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      });
      setSettings(s);
      setApiKey("");
      setOk("Đã lưu cấu hình Trợ Lý AI / Gemini.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    } finally {
      setBusy(false);
    }
  }

  async function onClearKey() {
    if (!window.confirm("Xóa API key đã lưu trong DB? (Vẫn dùng GEMINI_API_KEY trong .env nếu có)")) {
      return;
    }
    setBusy(true);
    try {
      const s = await updateAiSettings({ clear_api_key: true });
      setSettings(s);
      setOk("Đã xóa key trong DB.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được key.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="config-section-page">
      <ConfigTabNav />
      <p className="field-hint">
        <Link to="/m/config">← Cấu Hình</Link>
      </p>
      <h1>AI Gemini (Trợ Lý AI)</h1>
      <p className="field-hint">
        Lớp A nhắc việc = 0 token. Lớp B hỏi đáp chỉ khi user có <code>ai_query</code> và bấm Gửi.
        Không hiện trên Worker Portal.
      </p>
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}
      {!settings ? (
        <p className="field-hint">Đang tải…</p>
      ) : (
        <form className="ai-settings-form" onSubmit={(e) => void onSave(e)}>
          <label className="check-row">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            Bật Gemini toàn cục
          </label>
          <label>
            Mô hình AI
            <select value={modelName} onChange={(e) => setModelName(e.target.value)}>
              <option value="gemini-3-flash-preview">gemini-3-flash-preview (khuyến nghị)</option>
              <option value="gemini-flash-latest">gemini-flash-latest</option>
              <option value="gemini-pro-latest">gemini-pro-latest</option>
            </select>
            {modelName.startsWith("gemini-2.") && (
              <span className="field-hint" style={{ color: "#b45309" }}>
                Model 2.x đã ngừng — chọn 3-flash-preview rồi Lưu.
              </span>
            )}
          </label>
          <label>
            Tối đa câu / người dùng / ngày
            <input
              type="number"
              min={1}
              max={200}
              value={maxDay}
              onChange={(e) => setMaxDay(Number(e.target.value))}
            />
          </label>
          <label>
            Tối đa token / câu trả lời
            <input
              type="number"
              min={128}
              max={8192}
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
            />
          </label>
          <label>
            API key mới (để trống = giữ nguyên)
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Dán key Google AI Studio / Workspace"
              autoComplete="off"
            />
          </label>
          <p className="field-hint">
            Key hiện tại:{" "}
            {settings.has_api_key
              ? `${settings.api_key_masked ?? "****"} (nguồn: ${settings.source})`
              : "chưa có — set GEMINI_API_KEY hoặc dán ở trên"}
          </p>
          <div className="dispute-action-btns">
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Đang lưu…" : "Lưu"}
            </button>
            {settings.has_api_key && settings.source === "database" && (
              <button type="button" className="btn-secondary" disabled={busy} onClick={() => void onClearKey()}>
                Xóa key DB
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
