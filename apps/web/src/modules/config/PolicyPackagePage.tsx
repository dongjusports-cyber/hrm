import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchPolicyPackages,
  updatePolicyPackage,
  type PolicyConfirmPreview,
  type PolicyPackage,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { ConfirmThreeStepModal } from "./ConfirmThreeStepModal";
import { ConfigTabNav } from "./ConfigTabNav";

type EditorTab = "form" | "json";

function num(v: unknown, fallback: number): number {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string" && v.trim() !== "") return Number(v);
  return fallback;
}

export function PolicyPackagePage() {
  const [packages, setPackages] = useState<PolicyPackage[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [editorTab, setEditorTab] = useState<EditorTab>("form");
  const [jsonText, setJsonText] = useState("");
  const [attendMonthly, setAttendMonthly] = useState(600_000);
  const [transportMonthly, setTransportMonthly] = useState(800_000);
  const [lateHalf, setLateHalf] = useState(2);
  const [earlyHalf, setEarlyHalf] = useState(2);
  const [lateZero, setLateZero] = useState(5);
  const [earlyZero, setEarlyZero] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmStep, setConfirmStep] = useState(1);
  const [confirmDetail, setConfirmDetail] = useState("");
  const [moneyFields, setMoneyFields] = useState<string[]>([]);
  const [pendingPayload, setPendingPayload] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  function applyPkgToForm(pkg: PolicyPackage) {
    setName(pkg.name);
    setJsonText(JSON.stringify(pkg.payload, null, 2));
    const p = pkg.payload;
    setAttendMonthly(num(p.attendance_bonus_monthly, 600_000));
    setTransportMonthly(num(p.transport_monthly_default, 800_000));
    const pen = (p.attendance_penalties as Record<string, unknown>) || {};
    setLateHalf(num(pen.late_half, 2));
    setEarlyHalf(num(pen.early_half, 2));
    setLateZero(num(pen.late_zero, 5));
    setEarlyZero(num(pen.early_zero, 5));
  }

  function buildPayloadFromForm(base: Record<string, unknown>): Record<string, unknown> {
    const penalties = {
      ...((base.attendance_penalties as Record<string, unknown>) || {}),
      late_half: lateHalf,
      early_half: earlyHalf,
      late_zero: lateZero,
      early_zero: earlyZero,
    };
    return {
      ...base,
      attendance_bonus_monthly: attendMonthly,
      transport_monthly_default: transportMonthly,
      attendance_penalties: penalties,
    };
  }

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchPolicyPackages();
      setPackages(list);
      const current = list.find((p) => p.id === selectedId) ?? list[0];
      if (current) {
        setSelectedId(current.id);
        applyPkgToForm(current);
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

  const selected = useMemo(
    () => packages.find((p) => p.id === selectedId),
    [packages, selectedId],
  );

  function onSelect(id: string) {
    const pkg = packages.find((p) => p.id === id);
    if (!pkg) return;
    setSelectedId(id);
    applyPkgToForm(pkg);
    setOk(null);
    setError(null);
  }

  function resolvePayload(): Record<string, unknown> | null {
    if (!selected) return null;
    if (editorTab === "json") {
      try {
        const parsed = JSON.parse(jsonText) as unknown;
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          setError("Trợ Lý AI: payload phải là object JSON.");
          return null;
        }
        return parsed as Record<string, unknown>;
      } catch {
        setError("Trợ Lý AI: JSON không hợp lệ.");
        return null;
      }
    }
    let base: Record<string, unknown>;
    try {
      base = JSON.parse(jsonText) as Record<string, unknown>;
    } catch {
      base = { ...(selected.payload as Record<string, unknown>) };
    }
    return buildPayloadFromForm(base);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    const payload = resolvePayload();
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
        applyPkgToForm(result.package);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại.");
      setConfirmOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="policy-page">
      <ConfigTabNav />
      <div className="users-head">
        <div>
          <h1>Gói chính sách</h1>
          <p className="module-placeholder">
            Sửa biểu mẫu hoặc JSON — lưu bản nháp qua xác nhận 3 bước (policy_confirm_logs).
          </p>
        </div>
        <Link to="/m/config" className="hr-layer-btn">
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
            <span>Gói</span>
            <select value={selectedId} onChange={(e) => onSelect(e.target.value)}>
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} (v{p.version})
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
              Hiệu lực {formatDateDDMMYYYY(selected.effective_from)} · phiên bản {selected.version}
            </p>
          )}

          <div className="dispute-filters" role="tablist">
            <button
              type="button"
              role="tab"
              className={editorTab === "form" ? "filter-chip is-active" : "filter-chip"}
              onClick={() => setEditorTab("form")}
            >
              Biểu mẫu (chuyên cần)
            </button>
            <button
              type="button"
              role="tab"
              className={editorTab === "json" ? "filter-chip is-active" : "filter-chip"}
              onClick={() => setEditorTab("json")}
            >
              JSON đầy đủ
            </button>
          </div>

          {editorTab === "form" && (
            <div className="users-form-card">
              <h2>Tiền & ngưỡng phạt (22§22.3)</h2>
              <label className="field">
                Tiền chuyên cần / tháng
                <input
                  type="number"
                  value={attendMonthly}
                  onChange={(e) => setAttendMonthly(Number(e.target.value))}
                />
              </label>
              <label className="field">
                Đi lại mặc định / tháng
                <input
                  type="number"
                  value={transportMonthly}
                  onChange={(e) => setTransportMonthly(Number(e.target.value))}
                />
              </label>
              <div className="field-row">
                <label className="field">
                  Trễ → 50% (lần)
                  <input
                    type="number"
                    value={lateHalf}
                    onChange={(e) => setLateHalf(Number(e.target.value))}
                  />
                </label>
                <label className="field">
                  Về sớm → 50% (lần)
                  <input
                    type="number"
                    value={earlyHalf}
                    onChange={(e) => setEarlyHalf(Number(e.target.value))}
                  />
                </label>
              </div>
              <div className="field-row">
                <label className="field">
                  Trễ → 0% (lần)
                  <input
                    type="number"
                    value={lateZero}
                    onChange={(e) => setLateZero(Number(e.target.value))}
                  />
                </label>
                <label className="field">
                  Về sớm → 0% (lần)
                  <input
                    type="number"
                    value={earlyZero}
                    onChange={(e) => setEarlyZero(Number(e.target.value))}
                  />
                </label>
              </div>
              <p className="field-hint">
                Ví dụ nghiệm thu đợt 2: đổi 3/2 thành 4/3 rồi lưu 3 bước — tính lương đọc payload mới.
              </p>
            </div>
          )}

          {editorTab === "json" && (
            <label className="field">
              <span>Payload JSON</span>
              <textarea
                className="policy-json"
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                spellCheck={false}
                rows={20}
              />
            </label>
          )}

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
        onConfirm={() => {
          if (!pendingPayload || confirmStep >= 3) return;
          void runStep(confirmStep + 1, pendingPayload);
        }}
      />
    </div>
  );
}
