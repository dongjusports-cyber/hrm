import { FormEvent, useEffect, useRef, useState } from "react";

import {

  rehireEmployee,

  type Employee,

  type Team,

} from "../../shared/api";

import { formatTeamLabel } from "../../shared/formatOrg";

import {

  digitsOnlyMoney,

  formatMoneyTyping,

  sanitizeMoneyInput,

} from "./employeeFormState";

import { useSheetKeyboard } from "../../shared/formFieldEsc";

function todayIso(): string {
  const d = new Date();

  const m = String(d.getMonth() + 1).padStart(2, "0");

  const day = String(d.getDate()).padStart(2, "0");

  return `${d.getFullYear()}-${m}-${day}`;

}



type Props = {

  employee: Employee;

  teams: Team[];

  onClose: () => void;

  onDone: (message: string) => void;

};



/** Tái tuyển NV đã nghỉ — thường (reset TN/PC) hoặc giữ quyền lợi (ưu ái). */

export function RehireSheet({ employee, teams, onClose, onDone }: Props) {

  const [rehireDate, setRehireDate] = useState(todayIso());

  const [mode, setMode] = useState<"fresh_start" | "continuity">("fresh_start");

  const [reason, setReason] = useState("");

  const [teamId, setTeamId] = useState("");

  const [status, setStatus] = useState<"probation" | "active">("probation");

  const [contractSalary, setContractSalary] = useState("");

  const [error, setError] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);
  const formShellRef = useRef<HTMLFormElement>(null);

  useSheetKeyboard({ open: true, containerRef: formShellRef });

  useEffect(() => {

    if (employee.team_id) setTeamId(employee.team_id);

    const sal = employee.contract_salary;

    if (sal != null && sal !== "") {

      setContractSalary(formatMoneyTyping(String(sal)));

    }

  }, [employee.team_id, employee.contract_salary]);



  async function onSubmit(e: FormEvent) {

    e.preventDefault();

    setError(null);

    if (!teamId) {

      setError("Trợ Lý AI: chọn Tổ.");

      return;

    }

    const salaryDigits = digitsOnlyMoney(contractSalary);

    if (mode === "fresh_start" && (!salaryDigits || salaryDigits === "0")) {

      setError("Trợ Lý AI: tái tuyển thường cần lương HĐ mới > 0.");

      return;

    }

    if (mode === "continuity" && !reason.trim()) {

      setError("Trợ Lý AI: tái tuyển giữ quyền lợi cần ghi lý do.");

      return;

    }

    if (

      mode === "continuity" &&

      !window.confirm(

        "Xác nhận tái tuyển GIỮ quyền lợi (thâm niên & phụ cấp như trước nghỉ)?\n\nChỉ dùng khi sếp/BGD quyết.",

      )

    ) {

      return;

    }

    setBusy(true);

    try {

      const res = await rehireEmployee(employee.id, {

        rehire_date: rehireDate,

        rehire_mode: mode,

        rehire_reason: mode === "continuity" ? reason.trim() : undefined,

        team_id: teamId,

        status,

        contract_salary: mode === "fresh_start" ? salaryDigits : undefined,

      });

      onDone(res.message);

    } catch (err) {

      setError(err instanceof Error ? err.message : "Không tái tuyển được.");

    } finally {

      setBusy(false);

    }

  }



  return (

    <div className="modal-backdrop" role="presentation" onClick={onClose}>

      <div

        className="modal-panel modal-panel-wide rehire-panel"

        role="dialog"

        aria-labelledby="rehire-title"

        onClick={(ev) => ev.stopPropagation()}

      >

        <header className="rehire-head">

          <div>

            <h2 id="rehire-title">Tái tuyển — MSNV {employee.employee_code}</h2>

            <p className="field-hint rehire-sub">

              {employee.full_name} · Giữ MSNV cũ · <strong>Thường</strong> = tính lại thâm niên & PC ·{" "}

              <strong>Giữ quyền lợi</strong> = ưu ái

            </p>

          </div>

          <button type="button" className="btn-ghost-dark btn-sm" onClick={onClose} disabled={busy}>

            × Đóng

          </button>

        </header>



        {error && <p className="banner-warn rehire-banner">{error}</p>}



        <form ref={formShellRef} className="rehire-form" onSubmit={(ev) => void onSubmit(ev)}>

          <fieldset className="emp-form-section rehire-mode-section">

            <legend>Kiểu tái tuyển</legend>

            <label className="rehire-radio">

              <input

                type="radio"

                name="rehire_mode"

                checked={mode === "fresh_start"}

                onChange={() => setMode("fresh_start")}

              />

              Thường — thâm niên & phụ cấp tính lại (mặc định)

            </label>

            <label className="rehire-radio">

              <input

                type="radio"

                name="rehire_mode"

                checked={mode === "continuity"}

                onChange={() => setMode("continuity")}

              />

              Giữ quyền lợi — tiếp tục mọi thông số

            </label>

            {mode === "continuity" && (

              <label className="field rehire-reason">

                <span>Lý do ưu ái *</span>

                <input value={reason} onChange={(e) => setReason(e.target.value)} required />

              </label>

            )}

          </fieldset>



          <div className="emp-fields-grid rehire-fields">

            <label className="field">

              <span>Ngày vào lại *</span>

              <input

                type="date"

                value={rehireDate}

                onChange={(e) => setRehireDate(e.target.value)}

                required

              />

            </label>

            <label className="field">

              <span>Tổ *</span>

              <select value={teamId} onChange={(e) => setTeamId(e.target.value)} required>

                <option value="">— Chọn —</option>

                {teams.map((t) => (

                  <option key={t.id} value={t.id}>

                    {formatTeamLabel(t)}

                  </option>

                ))}

              </select>

            </label>

            <label className="field">

              <span>Trạng thái</span>

              <select

                value={status}

                onChange={(e) => setStatus(e.target.value as "probation" | "active")}

              >

                <option value="probation">Thử việc</option>

                <option value="active">Chính thức</option>

              </select>

            </label>

            {mode === "fresh_start" && (

              <label className="field emp-field-money">

                <span>Lương HĐ mới *</span>

                <input

                  value={contractSalary}

                  onChange={(e) => setContractSalary(sanitizeMoneyInput(e.target.value))}

                  onBlur={(e) => setContractSalary(formatMoneyTyping(e.target.value))}

                  inputMode="numeric"

                  required

                />

              </label>

            )}

          </div>



          <div className="modal-actions rehire-actions">

            <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>

              Hủy

            </button>

            <button type="submit" className="btn-primary" disabled={busy}>

              {busy ? "Đang lưu…" : "Tái tuyển"}

            </button>

          </div>

        </form>

      </div>

    </div>

  );

}

