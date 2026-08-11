import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchPolicyPackages,
  updatePolicyPackage,
  type PolicyConfirmPreview,
  type PolicyPackage,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { ConfirmThreeStepModal } from "./ConfirmThreeStepModal";

export function PolicyEditorPage() {
  const [packages, setPackages] = useState<PolicyPackage[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [name, setName] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmStep, setConfirmStep] = useState(1);
  const [confirmDetail, setConfirmDetail] = useState("");
  const [moneyFields, setMoneyFields] = useState<string[]>([]);
  const [pendingPayload, setPendingPayload] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchPolicyPackages();
      setPackages(list);
      const current = list.find((p) => p.id === selectedId) ?? list[0];
      if (current) {
        setSelectedId(current.id);
        setName(current.name);
        setJsonText(JSON.stringify(current.payload, null, 2));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được policy.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onSelect(id: string) {
    const pkg = packages.find((p) => p.id === id);
    if (!pkg) return;
    setSelectedId(id);
    setName(pkg.name);
    setJsonText(JSON.stringify(pkg.payload, null, 2));
    setOk(null);
    setError(null);
  }

  function parsePayload(): Record<string, unknown> | null {
    try {
      const parsed = JSON.parse(jsonText) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        setError("Trợ Lý AI: payload phải là object JSON.");
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch {
      setError("Trợ Lý AI: JSON không hợp lệ. Kiểm tra dấu phẩy/ngoặc.");
      return null;
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    const payload = parsePayload();
    if (!payload || !selectedId) return;
    setPendingPayload(payload);
    setConfirmStep(1);
    setConfirmDetail("Đang chuẩn bị bước 1/3…");
    setMoneyFields([]);
    setConfirmOpen(true);
    void runStep(1, payload);
  }

  async function runStep(step: number, payload: Record<string, unknown>) {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const result: PolicyConfirmPreview = await updatePolicyPackage(
        selectedId,
        { name, payload },
        step,
      );
      setConfirmStep(result.step);
      setConfirmDetail(result.detail);
      setMoneyFields(result.changed_money_fields);
      if (result.status === "saved" && result.package) {
        setOk(result.detail);
        setConfirmOpen(false);
        setPendingPayload(null);
        await reload();
        setSelectedId(result.package.id);
        setName(result.package.name);
        setJsonText(JSON.stringify(result.package.payload, null, 2));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại.");
      setConfirmOpen(false);
    } finally {
      setBusy(false);
    }
  }

  function onConfirmNext() {
    if (!pendingPayload) return;
    if (confirmStep >= 3) return;
    void runStep(confirmStep + 1, pendingPayload);
  }

  const selected = packages.find((p) => p.id === selectedId);

  return (
    <div className="policy-page">
      <div className="users-head">
        <div>
          <h1>Nhân sự / Lương — Policy</h1>
          <p className="module-placeholder">
            Gói thông số mùa (không hard-code). Lưu tham số tiền bắt buộc xác nhận 3 lần (P10).
          </p>
        </div>
        <Link to="/m/config" className="btn-back">
          ← Cấu Hình
        </Link>
      </div>

      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      {loading ? (
        <p>Đang tải…</p>
      ) : (
        <form className="policy-form" onSubmit={onSubmit}>
          <label className="field">
            <span>Gói policy</span>
            <select value={selectedId} onChange={(e) => onSelect(e.target.value)}>
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} (v{p.version}){p.is_active ? "" : " — tắt"}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Tên gói</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>

          {selected && (
            <p className="field-hint">
              Hiệu lực: {formatDateDDMMYYYY(selected.effective_from)}
              {selected.effective_to ? ` → ${selected.effective_to}` : " → hiện tại"} · phiên bản{" "}
              {selected.version}
            </p>
          )}

          <label className="field">
            <span>Nội dung JSON (khối kiểm soát — không SQL/công thức tự do)</span>
            <textarea
              className="policy-json"
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              spellCheck={false}
              rows={22}
            />
          </label>

          <button type="submit" className="btn-primary" disabled={busy || !selectedId}>
            Lưu (xác nhận 3 lần)…
          </button>
        </form>
      )}

      <ConfirmThreeStepModal
        open={confirmOpen}
        step={confirmStep}
        detail={confirmDetail}
        moneyFields={moneyFields}
        busy={busy}
        onCancel={() => {
          setConfirmOpen(false);
          setPendingPayload(null);
        }}
        onConfirm={onConfirmNext}
      />
    </div>
  );
}
