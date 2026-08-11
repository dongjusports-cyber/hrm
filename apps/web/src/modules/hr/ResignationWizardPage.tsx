import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createResignation,
  fetchEmployees,
  fetchResignationPreview,
  type Employee,
  type ResignationPreview,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { navigateSmooth } from "../../shared/navigateSmooth";

const RESIGN_TYPES = [
  { value: "DPR", label: "DPR — Trong thời gian thử việc" },
  { value: "AFL", label: "AFL — Nộp đơn xin nghỉ" },
  { value: "LWA", label: "LWA — Tự ý bỏ việc" },
  { value: "CID", label: "CID — Hết hạn hợp đồng" },
  { value: "DIS", label: "DIS — Sa thải" },
];

/** Nhân Sự → Thủ tục thôi việc — wizard 3 bước (5.4). */
export function ResignationWizardPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [empQ, setEmpQ] = useState("");
  const [empId, setEmpId] = useState("");
  const [resignType, setResignType] = useState("AFL");
  const [lastWorkingDate, setLastWorkingDate] = useState("");
  const [reason, setReason] = useState("");
  const [preview, setPreview] = useState<ResignationPreview | null>(null);
  const [severanceMonths, setSeveranceMonths] = useState(0);
  const [severanceAmount, setSeveranceAmount] = useState("0");
  const [handoverDone, setHandoverDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void fetchEmployees({ status: "active" })
      .then(setEmployees)
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Không tải nhân viên.");
      });
  }, []);

  const filteredEmployees = useMemo(() => {
    const needle = empQ.trim().toLowerCase();
    if (!needle) return employees;
    return employees.filter(
      (e) =>
        e.employee_code.toLowerCase().includes(needle) ||
        e.full_name.toLowerCase().includes(needle),
    );
  }, [employees, empQ]);

  const selectedEmployee = employees.find((e) => e.id === empId);

  async function goStep2() {
    if (!empId || !lastWorkingDate) {
      setError("Chọn nhân viên và ngày làm việc cuối.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const pv = await fetchResignationPreview(empId, resignType, lastWorkingDate);
      setPreview(pv);
      setSeveranceMonths(pv.severance_months);
      setSeveranceAmount(String(pv.severance_amount));
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tính được trợ cấp / phép tồn.");
    } finally {
      setBusy(false);
    }
  }

  function goStep3() {
    setError(null);
    setStep(3);
  }

  async function onConfirm(e: FormEvent) {
    e.preventDefault();
    if (!empId || !lastWorkingDate) return;
    setBusy(true);
    setError(null);
    try {
      await createResignation(empId, {
        resign_type_code: resignType,
        last_working_date: lastWorkingDate,
        reason: reason.trim() || null,
        severance_months: severanceMonths,
        severance_amount: severanceAmount.trim() || "0",
        handover_done: handoverDone,
        finalize: true,
      });
      navigateSmooth(navigate, "/m/hr");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không ghi thôi việc được.");
    } finally {
      setBusy(false);
    }
  }

  const resignLabel =
    RESIGN_TYPES.find((t) => t.value === resignType)?.label ?? resignType;

  const leaveRemaining = preview ? Number(preview.annual_leave_remaining) : null;

  return (
    <div className="config-section-page">
      <p className="field-hint">
        <Link to="/m/hr">← Nhân Sự</Link>
      </p>
      <h1>Thủ tục thôi việc</h1>
      <p className="field-hint">
        Bước {step}/3 —{" "}
        {step === 1 ? "Thông tin nghỉ" : step === 2 ? "Trợ cấp & phép tồn" : "Xác nhận"}
      </p>
      {error && <p className="banner-warn">{error}</p>}

      {step === 1 && (
        <form
          className="users-form-card"
          onSubmit={(e) => {
            e.preventDefault();
            void goStep2();
          }}
        >
          <h2>Bước 1 — Thông tin nghỉ việc</h2>
          <label className="field">
            <span>Tìm nhân viên</span>
            <input
              className="hr-search"
              value={empQ}
              onChange={(e) => setEmpQ(e.target.value)}
              placeholder="MSNV / họ tên"
            />
          </label>
          <label className="field">
            <span>Nhân viên</span>
            <select value={empId} onChange={(e) => setEmpId(e.target.value)} required>
              <option value="">— Chọn —</option>
              {filteredEmployees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.employee_code} — {e.full_name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Lý do thôi việc (5 mã)</span>
            <select value={resignType} onChange={(e) => setResignType(e.target.value)} required>
              {RESIGN_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Ngày làm việc cuối</span>
            <input
              type="date"
              value={lastWorkingDate}
              onChange={(e) => setLastWorkingDate(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Ghi chú / lý do chi tiết</span>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" }}
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Đang tính…" : "Tiếp →"}
          </button>
        </form>
      )}

      {step === 2 && preview && (
        <form
          className="users-form-card"
          onSubmit={(e) => {
            e.preventDefault();
            goStep3();
          }}
        >
          <h2>Bước 2 — Trợ cấp thôi việc &amp; phép năm còn lại</h2>
          <div className="kpi-cards" style={{ marginBottom: 16 }}>
            <article className="kpi-card">
              <p>Thâm niên</p>
              <strong>{preview.tenure_years} năm</strong>
            </article>
            <article className="kpi-card">
              <p>Phép năm còn lại</p>
              <strong>
                {leaveRemaining !== null ? leaveRemaining.toLocaleString("vi-VN") : "—"} ngày
              </strong>
            </article>
            <article className="kpi-card">
              <p>Tài khoản Worker</p>
              <strong>{preview.account_will_lock ? "Sẽ khóa" : "Giữ nguyên"}</strong>
            </article>
          </div>
          <p className="field-hint">
            AFL: 0,5 tháng lương × số năm thâm niên. CID: ước tính theo thâm niên. Có thể chỉnh tay
            trước khi chốt.
          </p>
          <label className="field">
            <span>Số tháng trợ cấp (ước tính)</span>
            <input
              type="number"
              step={1}
              min={0}
              value={severanceMonths}
              onChange={(e) => setSeveranceMonths(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span>Số tiền trợ cấp (VND)</span>
            <input
              value={severanceAmount}
              onChange={(e) => setSeveranceAmount(e.target.value)}
              inputMode="numeric"
            />
          </label>
          <label className="field">
            <span>
              <input
                type="checkbox"
                checked={handoverDone}
                onChange={(e) => setHandoverDone(e.target.checked)}
              />{" "}
              Đã bàn giao công việc xong
            </span>
          </label>
          <div className="hr-dept-row">
            <button type="button" className="btn-ghost-dark" onClick={() => setStep(1)}>
              ← Quay lại
            </button>
            <button type="submit" className="btn-primary">
              Tiếp →
            </button>
          </div>
        </form>
      )}

      {step === 3 && selectedEmployee && preview && (
        <form className="users-form-card" onSubmit={(ev) => void onConfirm(ev)}>
          <h2>Bước 3 — Xác nhận</h2>
          <ul className="field-hint" style={{ lineHeight: 1.8, marginBottom: 16 }}>
            <li>
              <strong>Nhân viên:</strong> {selectedEmployee.employee_code} —{" "}
              {selectedEmployee.full_name}
            </li>
            <li>
              <strong>Lý do:</strong> {resignLabel}
            </li>
            <li>
              <strong>Ngày làm việc cuối:</strong> {formatDateDDMMYYYY(lastWorkingDate)}
            </li>
            {reason.trim() && (
              <li>
                <strong>Ghi chú:</strong> {reason.trim()}
              </li>
            )}
            <li>
              <strong>Phép năm còn lại:</strong>{" "}
              {leaveRemaining !== null ? leaveRemaining.toLocaleString("vi-VN") : "—"} ngày
            </li>
            <li>
              <strong>Trợ cấp:</strong> {severanceMonths} tháng (ước tính) —{" "}
              {Number(severanceAmount || 0).toLocaleString("vi-VN")} VND
            </li>
            <li>
              <strong>Bàn giao:</strong> {handoverDone ? "Đã xong" : "Chưa xong"}
            </li>
          </ul>
          <p className="banner-warn">
            Sau khi xác nhận: ghi bản thôi việc (seq_no tự tăng — cho phép nghỉ nhiều lần), đặt
            trạng thái «Thôi việc», khóa tài khoản Worker.
          </p>
          <div className="hr-dept-row">
            <button type="button" className="btn-ghost-dark" onClick={() => setStep(2)}>
              ← Quay lại
            </button>
            <button type="submit" className="btn-primary" disabled={busy}>
              Xác nhận thôi việc
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
