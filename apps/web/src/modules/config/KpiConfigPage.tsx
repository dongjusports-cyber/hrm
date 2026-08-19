import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchPolicyPackages,
  updatePolicyPackage,
  type PolicyConfirmPreview,
  type PolicyPackage,
} from "../../shared/api";
import { ConfirmThreeStepModal } from "./ConfirmThreeStepModal";

/** Cấu Hình → KPI ngưỡng (02§2.4, 04§4.6) — lưu vào policy active. */
export function KpiConfigPage() {
  const [pkg, setPkg] = useState<PolicyPackage | null>(null);
  const [b3, setB3] = useState("");
  const [hours, setHours] = useState("8");
  const [attMin, setAttMin] = useState("90");
  const [otMax, setOtMax] = useState("20");
  const [turnMax, setTurnMax] = useState("5");
  const [deptOtMax, setDeptOtMax] = useState("30");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmStep, setConfirmStep] = useState(1);
  const [confirmDetail, setConfirmDetail] = useState("");
  const [moneyFields, setMoneyFields] = useState<string[]>([]);
  const [pendingPayload, setPendingPayload] = useState<Record<string, unknown> | null>(
    null,
  );
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const list = await fetchPolicyPackages();
        const active = list.find((p) => p.is_active) ?? list[0];
        if (!active) {
          setError("Trợ Lý AI: chưa có gói policy.");
          return;
        }
        setPkg(active);
        const p = active.payload;
        setB3(p.kpi_manpower_factor == null ? "" : String(p.kpi_manpower_factor));
        setHours(String(p.kpi_hours_per_day ?? 8));
        setAttMin(String(p.kpi_attendance_min_pct ?? 90));
        setOtMax(String(p.kpi_ot_rate_max_pct ?? 20));
        setTurnMax(String(p.kpi_turnover_max_pct ?? 5));
        setDeptOtMax(String(p.kpi_ot_dept_max_pct ?? 30));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tải KPI policy.");
      }
    })();
  }, []);

  function buildPayload(): Record<string, unknown> | null {
    if (!pkg) return null;
    const next = { ...pkg.payload };
    const b3Trim = b3.trim();
    next.kpi_manpower_factor = b3Trim === "" ? null : Number(b3Trim);
    next.kpi_hours_per_day = Number(hours);
    next.kpi_attendance_min_pct = Number(attMin);
    next.kpi_ot_rate_max_pct = Number(otMax);
    next.kpi_turnover_max_pct = Number(turnMax);
    next.kpi_ot_dept_max_pct = Number(deptOtMax);
    return next;
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    const payload = buildPayload();
    if (!payload || !pkg) return;
    setPendingPayload(payload);
    setConfirmStep(1);
    setConfirmDetail("Đang chuẩn bị bước 1/3…");
    setMoneyFields([]);
    setConfirmOpen(true);
    void runStep(1, payload);
  }

  async function runStep(step: number, payload: Record<string, unknown>) {
    if (!pkg) return;
    setBusy(true);
    setError(null);
    try {
      const result: PolicyConfirmPreview = await updatePolicyPackage(
        pkg.id,
        { name: pkg.name, payload },
        step,
      );
      setConfirmStep(result.step);
      setConfirmDetail(result.detail);
      setMoneyFields(result.changed_money_fields);
      if (result.status === "saved" && result.package) {
        setConfirmOpen(false);
        setOk(result.detail);
        setPkg(result.package);
        setPendingPayload(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
      setConfirmOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="config-section-page">
      <p className="field-hint">
        <Link to="/m/config" className="hr-layer-btn">
          ← Cấu Hình
        </Link>
      </p>
      <h1>KPI — ngưỡng cảnh báo</h1>
      <p className="field-hint">
        Công thức chuyên cần / OT / nghỉ việc theo 04§4.6. Vượt ngưỡng → badge Trợ Lý AI (0
        token). B3 trống = dùng số ngày công chính thức của kỳ.
      </p>
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}
      {!pkg ? (
        <p className="field-hint">Đang tải…</p>
      ) : (
        <form className="ai-settings-form" onSubmit={onSubmit}>
          <p className="field-hint">
            Gói: <strong>{pkg.name}</strong>
          </p>
          <label>
            Hệ số B3 nhân lực (kpi_manpower_factor)
            <input
              type="number"
              min={0}
              max={31}
              step="0.5"
              placeholder="Để trống = ngày công kỳ"
              value={b3}
              onChange={(e) => setB3(e.target.value)}
            />
          </label>
          <label>
            Giờ chuẩn mỗi ngày (kpi_hours_per_day)
            <input
              type="number"
              min={1}
              max={24}
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              required
            />
          </label>
          <label>
            Chuyên cần tối thiểu % (kpi_attendance_min_pct)
            <input
              type="number"
              min={0}
              max={100}
              value={attMin}
              onChange={(e) => setAttMin(e.target.value)}
              required
            />
          </label>
          <label>
            Tỷ lệ OT tối đa % (kpi_ot_rate_max_pct)
            <input
              type="number"
              min={0}
              max={100}
              value={otMax}
              onChange={(e) => setOtMax(e.target.value)}
              required
            />
          </label>
          <label>
            Tỷ lệ nghỉ việc tối đa % (kpi_turnover_max_pct)
            <input
              type="number"
              min={0}
              max={100}
              value={turnMax}
              onChange={(e) => setTurnMax(e.target.value)}
              required
            />
          </label>
          <label>
            Tỷ lệ OT bộ phận tối đa % (kpi_ot_dept_max_pct)
            <input
              type="number"
              min={0}
              max={100}
              value={deptOtMax}
              onChange={(e) => setDeptOtMax(e.target.value)}
              required
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            Lưu (xác nhận 3 bước)
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
          if (pendingPayload && confirmStep < 3) {
            void runStep(confirmStep + 1, pendingPayload);
          }
        }}
      />
    </div>
  );
}
