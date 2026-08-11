import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  fetchLabourContractRenewPreview,
  printEmployeeContract,
  printEmployeeProbation,
  renewLabourContract,
  type Employee,
  type LabourContract,
  type LabourContractRenewPreview,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";

const CONTRACT_TYPE_LABELS: Record<string, string> = {
  TV: "Thử việc (TV)",
  HD1: "HĐ lần 1 (HD1)",
  HD2: "HĐ lần 2 (HD2)",
  VTH: "Vô thời hạn (VTH)",
};

type PanelTab = "timeline" | "sign";

function labelContractStatus(code: string): string {
  switch (code.toLowerCase()) {
    case "draft":
      return "Nháp";
    case "active":
      return "Hiệu lực";
    case "expired":
      return "Hết hạn";
    case "terminated":
      return "Chấm dứt";
    default:
      return code;
  }
}

function contractTypeLabel(row: LabourContract): string {
  return row.contract_type_label || CONTRACT_TYPE_LABELS[row.contract_type_code] || row.contract_type_code;
}

function fmtSalary(v: string | number): string {
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString("vi-VN") : String(v);
}

type Props = {
  employee: Employee | undefined;
  employeeId: string | null;
  contracts: LabourContract[];
  busy: boolean;
  setBusy: (v: boolean) => void;
  onError: (msg: string | null) => void;
  onOk: (msg: string | null) => void;
  onContractsChanged: () => Promise<void>;
  tab: PanelTab;
  onTabChange: (tab: PanelTab) => void;
};

/** Cột phải — lịch sử HĐ, ký tiếp, in mẫu theo từng HĐ (5.2 / 5.9). */
export function EmployeeContractPanel({
  employee,
  employeeId,
  contracts,
  busy,
  setBusy,
  onError,
  onOk,
  onContractsChanged,
  tab,
  onTabChange,
}: Props) {
  const [renewPreview, setRenewPreview] = useState<LabourContractRenewPreview | null>(null);
  const [contractType, setContractType] = useState("HD1");
  const [allowedTypes, setAllowedTypes] = useState<string[]>(["HD1", "HD2", "VTH"]);
  const [signDate, setSignDate] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [baseSalary, setBaseSalary] = useState("");
  const [previewMessage, setPreviewMessage] = useState("");

  const timeline = useMemo(
    () => [...contracts].sort((a, b) => a.seq_no - b.seq_no),
    [contracts],
  );

  function switchTab(next: PanelTab) {
    onTabChange(next);
  }

  useEffect(() => {
    onTabChange("timeline");
    setRenewPreview(null);
  }, [employeeId, onTabChange]);

  async function loadRenewPreview() {
    if (!employeeId) return;
    setBusy(true);
    onError(null);
    onOk(null);
    try {
      const preview = await fetchLabourContractRenewPreview(employeeId);
      setRenewPreview(preview);
      setContractType(preview.suggested_contract_type_code);
      setAllowedTypes(preview.allowed_contract_type_codes);
      setSignDate(preview.suggested_sign_date);
      setStartDate(preview.suggested_start_date);
      setEndDate(preview.suggested_end_date ?? "");
      setBaseSalary(String(preview.suggested_base_salary));
      setPreviewMessage(preview.message);
      switchTab("sign");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Không tải gợi ý ký tiếp.");
    } finally {
      setBusy(false);
    }
  }

  async function onRenewContract(e: FormEvent) {
    e.preventDefault();
    if (!employeeId) return;
    setBusy(true);
    onError(null);
    onOk(null);
    try {
      const created = await renewLabourContract({
        employee_id: employeeId,
        contract_type_code: contractType,
        sign_date: signDate || null,
        start_date: startDate,
        end_date: endDate || null,
        base_salary: baseSalary.trim() || undefined,
      });
      onOk(
        `Đã ký ${created.contract_no || created.contract_type_code} — ${created.times_label || ""}.`.trim(),
      );
      setRenewPreview(null);
      switchTab("timeline");
      await onContractsChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Không ký HĐ tiếp được.");
    } finally {
      setBusy(false);
    }
  }

  async function onPrintContract(c: LabourContract) {
    if (!employeeId) return;
    setBusy(true);
    onError(null);
    try {
      if (c.contract_type_code === "TV") {
        await printEmployeeProbation(employeeId, c.id);
      } else {
        await printEmployeeContract(employeeId, c.id);
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : "Không mở mẫu in được.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="hr-contracts-panel">
      <div className="hr-contracts-head">
        <h2>
          {employee
            ? `${employee.employee_code} — ${employee.full_name}`
            : "Chọn nhân viên bên trái"}
        </h2>
        {employeeId && (
          <button
            type="button"
            className="btn-primary btn-sm"
            onClick={() => void loadRenewPreview()}
            disabled={busy}
          >
            Ký HĐ tiếp
          </button>
        )}
      </div>

      {employeeId && (
        <div className="hr-contracts-tabs" role="tablist" aria-label="Hợp đồng">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "timeline"}
            className={tab === "timeline" ? "hr-contracts-tab active" : "hr-contracts-tab"}
            onClick={() => switchTab("timeline")}
          >
            Lịch sử HĐ
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "sign"}
            className={tab === "sign" ? "hr-contracts-tab active" : "hr-contracts-tab"}
            onClick={() => {
              switchTab("sign");
              if (!renewPreview) void loadRenewPreview();
            }}
          >
            Ký HĐ tiếp
          </button>
        </div>
      )}

      <div className="hr-contracts-scroll">
        {!employeeId && (
          <p className="module-placeholder">Chọn MSNV ở danh sách bên trái.</p>
        )}

        {employeeId && tab === "timeline" && (
          <>
            {timeline.length === 0 && (
              <p className="module-placeholder">
                Chưa có HĐ nào — chuyển sang tab «Ký HĐ tiếp» để tạo.
              </p>
            )}
            <ul className="hr-board-list hr-contracts-timeline" aria-label="Dòng thời gian hợp đồng">
              {timeline.map((c) => (
                <li key={c.id}>
                  <div className="hr-board-row hr-contract-row">
                    <span className="hr-board-main">
                      <strong>
                        {c.contract_no || `#${c.seq_no}`} · {contractTypeLabel(c)} —{" "}
                        {labelContractStatus(c.status)}
                      </strong>
                      {c.times_label ? <span className="field-hint">{c.times_label}</span> : null}
                      <span className="field-hint">
                        {formatDateDDMMYYYY(c.start_date)}
                        {c.end_date ? ` → ${formatDateDDMMYYYY(c.end_date)}` : " → VTH"}
                        {c.sign_date ? ` · ký ${formatDateDDMMYYYY(c.sign_date)}` : ""}
                      </span>
                      <span className="field-hint">Lương HĐ: {fmtSalary(c.base_salary)} VND</span>
                    </span>
                    <button
                      type="button"
                      className="btn-ghost-dark btn-sm"
                      disabled={busy}
                      onClick={() => void onPrintContract(c)}
                      title={
                        c.contract_type_code === "TV"
                          ? "In thỏa thuận thử việc"
                          : "In hợp đồng lao động"
                      }
                    >
                      {c.contract_type_code === "TV" ? "In thử việc" : "In HĐ"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <p className="field-hint hr-contracts-print-hint">
              Mỗi dòng in đúng loại HĐ đã ký (TV / HD1 / HD2 / VTH). Không in nhầm HĐ cũ nếu chọn
              đúng dòng.
            </p>
          </>
        )}

        {employeeId && tab === "sign" && (
          <form className="hr-contract-sign-form" onSubmit={(ev) => void onRenewContract(ev)}>
            {!renewPreview && !busy && (
              <p className="field-hint">Đang tải gợi ý ký tiếp…</p>
            )}
            {renewPreview && (
              <>
                <p className="field-hint">{previewMessage}</p>
              <p className="field-hint">
                Thứ tự mặc định: TV → HD1 → HD2 → VTH. Dropdown «Loại HĐ» cho phép sếp chỉ định
                loại khác trong phạm vi hợp lệ.
              </p>
                <p className="field-hint">
                  Số HĐ dự kiến: <strong>{renewPreview.suggested_contract_no}</strong> · Lần{" "}
                  {renewPreview.suggested_seq_no}
                </p>
                <div className="hr-contract-form-grid">
                  <label className="field field-span-2">
                    <span>Loại HĐ</span>
                    <select
                      value={contractType}
                      onChange={(e) => setContractType(e.target.value)}
                    >
                      {allowedTypes.map((code) => (
                        <option key={code} value={code}>
                          {CONTRACT_TYPE_LABELS[code] || code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Ngày ký</span>
                    <input
                      type="date"
                      value={signDate}
                      onChange={(e) => setSignDate(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>Ngày bắt đầu</span>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      required
                    />
                  </label>
                  <label className="field">
                    <span>Ngày hết hạn</span>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                    />
                    <span className="field-hint">Để trống nếu VTH.</span>
                  </label>
                  <label className="field">
                    <span>Lương cơ bản (HĐ)</span>
                    <input
                      value={baseSalary}
                      onChange={(e) => setBaseSalary(e.target.value)}
                      inputMode="numeric"
                      placeholder="0"
                    />
                  </label>
                </div>
                <div className="hr-dept-row">
                  <button type="submit" className="btn-primary btn-sm" disabled={busy}>
                    Lưu HĐ
                  </button>
                  <button
                    type="button"
                    className="btn-ghost-dark btn-sm"
                    onClick={() => switchTab("timeline")}
                  >
                    Quay lại lịch sử
                  </button>
                </div>
              </>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
