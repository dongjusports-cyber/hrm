import { useLayoutEffect, useRef, type ChangeEvent } from "react";
import type { AllowanceAssignment, AllowanceType, Department, Position, Team } from "../../shared/api";
import { LookupSelect } from "../../shared/LookupSelect";
import {
  activeTeams,
  departmentsWithActiveTeams,
  formatDepartmentLabel,
  formatTeamLabel,
} from "../../shared/formatOrg";
import {
  formatAllowanceDefaultAmount,
  formatMoneyTyping,
  sanitizeMoneyInput,
  type EmployeeFormState,
  type ProfileTab,
} from "./employeeFormState";
import { WtRegimePanel } from "./WtRegimePanel";

type Props = {
  form: EmployeeFormState;
  setForm: (next: EmployeeFormState) => void;
  tab: ProfileTab;
  isNew: boolean;
  departments: Department[];
  teams: Team[];
  positions?: Position[];
  /** column = 1 cột trong panel hồ sơ overlay */
  fieldLayout?: "grid" | "column";
  fieldErrors?: Record<string, string>;
};

function fieldErrorMsg(fieldErrors: Record<string, string> | undefined, field: string) {
  const msg = fieldErrors?.[field];
  if (!msg) return null;
  return <span className="field-error">{msg}</span>;
}

function teamSelect(
  form: EmployeeFormState,
  setForm: (next: EmployeeFormState) => void,
  departments: Department[],
  teams: Team[],
  fieldErrors?: Record<string, string>,
) {
  const deptOptions = departmentsWithActiveTeams(departments, teams);
  const teamOptions = activeTeams(teams).filter(
    (t) => !form.department_code || t.department_code === form.department_code,
  );
  const selectedTeam = teamOptions.find((t) => t.id === form.team_id);

  return (
    <>
      <label className="field">
        <span>Bộ phận</span>
        <select
          value={form.department_code}
          onChange={(e) => {
            const nextDept = e.target.value;
            const stillValid = teams.some(
              (t) => t.id === form.team_id && t.department_code === nextDept,
            );
            setForm({
              ...form,
              department_code: nextDept,
              team_id: stillValid ? form.team_id : "",
            });
          }}
        >
          <option value="">— Tất cả —</option>
          {deptOptions.map((d) => (
            <option key={d.id} value={d.code}>
              {formatDepartmentLabel(d)}
            </option>
          ))}
        </select>
      </label>
      <label className="field emp-field-team">
        <span>Tổ *</span>
        <select
          value={form.team_id}
          onChange={(e) => setForm({ ...form, team_id: e.target.value })}
          required
          title={
            selectedTeam
              ? formatTeamLabel(selectedTeam, { showDepartment: !form.department_code })
              : undefined
          }
        >
          <option value="">— Chọn tổ —</option>
          {teamOptions.map((t) => (
            <option key={t.id} value={t.id}>
              {formatTeamLabel(t, { showDepartment: !form.department_code })}
            </option>
          ))}
        </select>
        {fieldErrorMsg(fieldErrors, "team_id")}
      </label>
    </>
  );
}

function positionSelect(
  form: EmployeeFormState,
  setForm: (next: EmployeeFormState) => void,
  positions: Position[],
) {
  const activePositions = positions.filter((p) => p.is_active);
  return (
    <label className="field">
      <span>Chức vụ</span>
      <select
        value={form.position_code}
        onChange={(e) => {
          const code = e.target.value;
          const pos = activePositions.find((p) => p.code === code);
          setForm({
            ...form,
            position_code: code,
            position_title: pos?.name ?? "",
          });
        }}
      >
        <option value="">— Chọn chức vụ —</option>
        {activePositions.map((p) => (
          <option key={p.code} value={p.code}>
            {p.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function moneyFieldHandlers(
  form: EmployeeFormState,
  setForm: (next: EmployeeFormState) => void,
  key: "contract_salary" | "probation_salary",
) {
  return {
    value: form[key],
    onChange: (e: ChangeEvent<HTMLInputElement>) =>
      setForm({ ...form, [key]: sanitizeMoneyInput(e.target.value) }),
    onBlur: (e: ChangeEvent<HTMLInputElement>) =>
      setForm({ ...form, [key]: formatMoneyTyping(e.target.value) }),
  };
}

type CreateFieldsProps = Omit<Props, "tab" | "isNew"> & {
  fieldErrors?: Record<string, string>;
  photoPreview: string | null;
  onPhotoPick: (file: File | null) => void;
  photoDisabled?: boolean;
};

/** Form tạo mới — ảnh + header gọn + 5 cột vừa một màn (không cuộn). */
export function EmployeeCreateFields({
  form,
  setForm,
  departments,
  teams,
  positions = [],
  fieldErrors,
  photoPreview,
  onPhotoPick,
  photoDisabled,
}: CreateFieldsProps) {
  const photoRef = useRef<HTMLInputElement>(null);

  return (
    <div className="emp-create-layout">
      <header className="emp-create-header">
        <button
          type="button"
          className="emp-photo emp-photo-create"
          onClick={() => photoRef.current?.click()}
          disabled={photoDisabled}
          title="Bấm để chọn ảnh chân dung"
        >
          {photoPreview ? (
            <img src={photoPreview} alt="Ảnh xem trước" />
          ) : (
            <span className="emp-photo-empty">
              <strong>Ảnh</strong>
              <small>Bấm thêm</small>
            </span>
          )}
        </button>
        <input
          ref={photoRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/*"
          hidden
          onChange={(e) => {
            onPhotoPick(e.target.files?.[0] ?? null);
            e.target.value = "";
          }}
        />
        <div className="emp-create-header-fields">
          <label className="field emp-create-msnv">
            <span>MSNV *</span>
            <input
              value={form.employee_code}
              onChange={(e) => setForm({ ...form, employee_code: e.target.value })}
              required
              autoFocus
              aria-invalid={Boolean(fieldErrors?.employee_code)}
            />
            {fieldErrorMsg(fieldErrors, "employee_code")}
          </label>
          <label className="field emp-create-name">
            <span>Họ và tên *</span>
            <input
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
              placeholder="Nhập họ tên đầy đủ"
              aria-invalid={Boolean(fieldErrors?.full_name)}
            />
            {fieldErrorMsg(fieldErrors, "full_name")}
          </label>
          <label className="field emp-create-status">
            <span>Trạng thái</span>
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
            >
              <option value="active">Chính thức</option>
              <option value="probation">Thử việc</option>
              <option value="maternity">Thai sản</option>
            </select>
          </label>
        </div>
      </header>

      <div className="emp-profile-cols emp-profile-cols-weighted emp-create-cols">
        <section className="emp-form-section emp-form-section-col" aria-labelledby="emp-create-work">
          <h3 id="emp-create-work" className="emp-form-section-title">
            Công việc
          </h3>
          <div className="emp-fields-col emp-fields-compact">
            {teamSelect(form, setForm, departments, teams, fieldErrors)}
            {positionSelect(form, setForm, positions)}
            <label className="field">
              <span>Ngày vào</span>
              <input
                type="date"
                value={form.join_date}
                onChange={(e) => setForm({ ...form, join_date: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Ngày ký HĐ</span>
              <input
                type="date"
                value={form.contract_signed_at}
                onChange={(e) => setForm({ ...form, contract_signed_at: e.target.value })}
              />
            </label>
          </div>
        </section>

        <section className="emp-form-section emp-form-section-col" aria-labelledby="emp-create-salary">
          <h3 id="emp-create-salary" className="emp-form-section-title">
            Lương
          </h3>
          <div className="emp-fields-col emp-fields-compact">
            <label className="field emp-field-money">
              <span>Lương HĐ *</span>
              <input
                {...moneyFieldHandlers(form, setForm, "contract_salary")}
                required
                inputMode="numeric"
                placeholder="0"
                aria-invalid={Boolean(fieldErrors?.contract_salary)}
              />
              {fieldErrorMsg(fieldErrors, "contract_salary")}
            </label>
            <label className="field emp-field-money">
              <span>Lương thử việc</span>
              <input
                {...moneyFieldHandlers(form, setForm, "probation_salary")}
                inputMode="numeric"
                placeholder="0"
              />
            </label>
            <label className="field">
              <span>Kênh lương</span>
              <select
                value={form.pay_channel}
                onChange={(e) => setForm({ ...form, pay_channel: e.target.value })}
              >
                <option value="CASH">Tiền mặt</option>
                <option value="ATM">ATM</option>
              </select>
            </label>
          </div>
        </section>

        <section className="emp-form-section emp-form-section-col" aria-labelledby="emp-create-personal">
          <h3 id="emp-create-personal" className="emp-form-section-title">
            Cá nhân
          </h3>
          <div className="emp-fields-col emp-fields-compact">
            <label className="field">
              <span>Giới tính</span>
              <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                <option value="">—</option>
                <option value="male">Nam</option>
                <option value="female">Nữ</option>
              </select>
            </label>
            <label className="field">
              <span>Ngày sinh</span>
              <input
                type="date"
                value={form.birth_date}
                onChange={(e) => setForm({ ...form, birth_date: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Điện thoại</span>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </label>
            <label className="field">
              <span>Số con</span>
              <input
                type="number"
                min={0}
                value={form.children_count}
                onChange={(e) => setForm({ ...form, children_count: e.target.value })}
              />
            </label>
          </div>
        </section>

        <section className="emp-form-section emp-form-section-col" aria-labelledby="emp-create-address">
          <h3 id="emp-create-address" className="emp-form-section-title">
            Cư trú & giấy tờ
          </h3>
          <div className="emp-fields-col emp-fields-compact">
            <label className="field">
              <span>Số CCCD</span>
              <input
                value={form.id_number}
                onChange={(e) => setForm({ ...form, id_number: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Ngày cấp CCCD</span>
              <input
                type="date"
                value={form.id_issue_date}
                onChange={(e) => setForm({ ...form, id_issue_date: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Địa chỉ thường trú</span>
              <input
                value={form.permanent_address}
                onChange={(e) => setForm({ ...form, permanent_address: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Liên hệ khẩn</span>
              <input
                value={form.urgent_contact}
                onChange={(e) => setForm({ ...form, urgent_contact: e.target.value })}
              />
            </label>
          </div>
        </section>

        <section className="emp-form-section emp-form-section-col" aria-labelledby="emp-create-insurance">
          <h3 id="emp-create-insurance" className="emp-form-section-title">
            Bảo hiểm & NH
          </h3>
          <div className="emp-fields-col emp-fields-compact emp-fields-insurance">
            <div className="emp-insurance-checks">
              <label className="field emp-check-row">
                <input
                  type="checkbox"
                  checked={form.si_enrolled}
                  onChange={(e) => setForm({ ...form, si_enrolled: e.target.checked })}
                />
                <span>BHXH</span>
              </label>
              <label className="field emp-check-row">
                <input
                  type="checkbox"
                  checked={form.pit_enrolled}
                  onChange={(e) => setForm({ ...form, pit_enrolled: e.target.checked })}
                />
                <span>Thuế TNCN</span>
              </label>
            </div>
            <label className="field">
              <span>Số sổ BHXH</span>
              <input
                value={form.si_book_no}
                onChange={(e) => setForm({ ...form, si_book_no: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Tài khoản NH</span>
              <input
                value={form.bank_account}
                onChange={(e) => setForm({ ...form, bank_account: e.target.value })}
              />
            </label>
          </div>
        </section>
      </div>
    </div>
  );
}

type AllowanceColProps = {
  allowances: AllowanceAssignment[];
  allowTypes: AllowanceType[];
  newAllowCode: string;
  setNewAllowCode: (v: string) => void;
  newAllowAmount: string;
  setNewAllowAmount: (v: string) => void;
  saving: boolean;
  onAdd: () => void;
  onDelete: (id: string) => void;
  formatMoney: (v: unknown) => string;
};

/** Mã khoản lương / điều chỉnh — không gán qua form phụ cấp hồ sơ. */
const PROFILE_ALLOWANCE_EXCLUDE = new Set(["ADJUST"]);

function profileAllowanceTypes(types: AllowanceType[]): AllowanceType[] {
  return types.filter((t) => !PROFILE_ALLOWANCE_EXCLUDE.has(t.code));
}

function AllowanceAddForm({
  allowTypes,
  newAllowCode,
  setNewAllowCode,
  newAllowAmount,
  setNewAllowAmount,
  saving,
  onAdd,
}: Pick<
  AllowanceColProps,
  "allowTypes" | "newAllowCode" | "setNewAllowCode" | "newAllowAmount" | "setNewAllowAmount" | "saving" | "onAdd"
>) {
  const selectableTypes = profileAllowanceTypes(allowTypes);

  function onTypeChange(code: string) {
    setNewAllowCode(code);
    const t = selectableTypes.find((x) => x.code === code);
    const defaultAmt = formatAllowanceDefaultAmount(t?.default_amount);
    if (defaultAmt) setNewAllowAmount(defaultAmt);
  }

  return (
    <div className="emp-allow-add-block" aria-label="Thêm phụ cấp">
      <h4 className="emp-allow-block-title">Thêm phụ cấp</h4>
      <div className="emp-allow-add emp-allow-add-col">
        <label className="field">
          <span>Loại</span>
          <select value={newAllowCode} onChange={(e) => onTypeChange(e.target.value)}>
            <option value="">— Chọn loại phụ cấp —</option>
            {selectableTypes.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field emp-field-money">
          <span>Số tiền</span>
          <input
            value={newAllowAmount}
            onChange={(e) => setNewAllowAmount(formatMoneyTyping(e.target.value))}
            inputMode="numeric"
            placeholder="0"
          />
        </label>
        <button
          type="button"
          className="btn-primary btn-sm"
          disabled={saving || !newAllowCode}
          onClick={onAdd}
        >
          Thêm
        </button>
      </div>
    </div>
  );
}

function AllowanceListDisplay({
  allowances,
  saving,
  onDelete,
  formatMoney,
}: Pick<AllowanceColProps, "allowances" | "saving" | "onDelete" | "formatMoney">) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(allowances.length);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) {
      prevCountRef.current = allowances.length;
      return;
    }
    if (allowances.length > prevCountRef.current) {
      el.scrollTop = el.scrollHeight;
    }
    prevCountRef.current = allowances.length;
  }, [allowances]);

  return (
    <div className="emp-allow-list-block" aria-label="Danh sách phụ cấp">
      <h4 className="emp-allow-block-title">Phụ cấp</h4>
      <div className="emp-allow-list-scroll" ref={scrollRef}>
        <ul className="dept-list emp-allow-list emp-allow-list-compact">
          {allowances.length === 0 && <li className="module-placeholder">Chưa có gán phụ cấp.</li>}
          {allowances.map((a) => (
            <li key={a.id}>
              <span className="emp-allow-line">
                <strong>{a.allowance_name}</strong> {formatMoney(a.amount)}
              </span>
              <button
                type="button"
                className="link-btn danger"
                disabled={saving}
                onClick={() => onDelete(a.id)}
              >
                Xóa
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** Hồ sơ gọn — 5 cột; thêm PC ở cột 1, danh sách PC ở cột 2. */
export function EmployeeProfileCompactFields({
  form,
  setForm,
  departments,
  teams,
  positions = [],
  allowancePanel,
  employeeId,
}: Omit<Props, "tab" | "isNew" | "fieldLayout"> & {
  allowancePanel?: AllowanceColProps;
  employeeId?: string;
}) {
  const col = "column" as const;
  return (
    <div className="emp-profile-compact">
      <div className="emp-profile-cols emp-profile-cols-weighted">
        <section
          className="emp-form-section emp-form-section-col emp-form-section-row-sync"
          aria-labelledby="emp-sec-work"
        >
          <h3 id="emp-sec-work" className="emp-form-section-title">
            Công việc
          </h3>
          <div className="emp-fields-col">
            {teamSelect(form, setForm, departments, teams)}
            {positionSelect(form, setForm, positions)}
            <label className="field">
              <span>Ngày vào</span>
              <input
                type="date"
                value={form.join_date}
                onChange={(e) => setForm({ ...form, join_date: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Ngày nghỉ</span>
              <input
                type="date"
                value={form.resign_date}
                onChange={(e) => setForm({ ...form, resign_date: e.target.value })}
              />
            </label>
          </div>
          {allowancePanel ? (
            <AllowanceAddForm
              allowTypes={allowancePanel.allowTypes}
              newAllowCode={allowancePanel.newAllowCode}
              setNewAllowCode={allowancePanel.setNewAllowCode}
              newAllowAmount={allowancePanel.newAllowAmount}
              setNewAllowAmount={allowancePanel.setNewAllowAmount}
              saving={allowancePanel.saving}
              onAdd={allowancePanel.onAdd}
            />
          ) : null}
        </section>

        <section
          className="emp-form-section emp-form-section-col emp-form-section-row-sync emp-form-section-salary"
          aria-labelledby="emp-sec-salary"
        >
          <h3 id="emp-sec-salary" className="emp-form-section-title">
            Lương
          </h3>
          <div className="emp-fields-col">
            <label className="field">
              <span>Ngày ký HĐ</span>
              <input
                type="date"
                value={form.contract_signed_at}
                onChange={(e) => setForm({ ...form, contract_signed_at: e.target.value })}
              />
            </label>
            <label className="field emp-field-money">
              <span>Lương HĐ</span>
              <input
                value={form.contract_salary}
                onChange={(e) => setForm({ ...form, contract_salary: e.target.value })}
                required
              />
            </label>
            <label className="field emp-field-money">
              <span>Lương thử việc</span>
              <input
                value={form.probation_salary}
                onChange={(e) => setForm({ ...form, probation_salary: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Kênh lương</span>
              <select
                value={form.pay_channel}
                onChange={(e) => setForm({ ...form, pay_channel: e.target.value })}
              >
                <option value="ATM">ATM</option>
                <option value="CASH">Tiền mặt</option>
              </select>
            </label>
          </div>
          {allowancePanel ? (
            <AllowanceListDisplay
              allowances={allowancePanel.allowances}
              saving={allowancePanel.saving}
              onDelete={allowancePanel.onDelete}
              formatMoney={allowancePanel.formatMoney}
            />
          ) : null}
        </section>

        <section
          className="emp-form-section emp-form-section-col emp-form-section-row-sync"
          aria-labelledby="emp-sec-personal"
        >
          <h3 id="emp-sec-personal" className="emp-form-section-title">
            Cá nhân
          </h3>
          <EmployeeProfileTabFields
            form={form}
            setForm={setForm}
            tab="personal"
            isNew={false}
            departments={departments}
            teams={teams}
            fieldLayout={col}
          />
        </section>

        <section className="emp-form-section emp-form-section-col" aria-labelledby="emp-sec-address">
          <h3 id="emp-sec-address" className="emp-form-section-title">
            Cư trú & giấy tờ
          </h3>
          <EmployeeProfileTabFields
            form={form}
            setForm={setForm}
            tab="address"
            isNew={false}
            departments={departments}
            teams={teams}
            fieldLayout={col}
          />
        </section>

        <section
          className="emp-form-section emp-form-section-col emp-form-section-row-sync"
          aria-labelledby="emp-sec-insurance"
        >
          <h3 id="emp-sec-insurance" className="emp-form-section-title">
            Bảo hiểm & Ngân hàng
          </h3>
          <EmployeeProfileTabFields
            form={form}
            setForm={setForm}
            tab="insurance"
            isNew={false}
            departments={departments}
            teams={teams}
            fieldLayout={col}
            insuranceChecksFirst
          />
          {employeeId ? <WtRegimePanel employeeId={employeeId} embedded /> : null}
        </section>
      </div>
    </div>
  );
}

/** @deprecated Dùng EmployeeProfileCompactFields trong overlay hồ sơ. */
export function EmployeeProfileAllFields({ form, setForm, departments, teams }: Omit<Props, "tab" | "isNew">) {
  return (
    <EmployeeProfileCompactFields
      form={form}
      setForm={setForm}
      departments={departments}
      teams={teams}
    />
  );
}

export function EmployeeProfileTabFields({
  form,
  setForm,
  tab,
  departments,
  teams,
  positions = [],
  fieldLayout = "grid",
  insuranceChecksFirst = false,
}: Props & { insuranceChecksFirst?: boolean }) {
  const fieldsClass = fieldLayout === "column" ? "emp-fields-col" : "emp-fields-grid";
  if (tab === "personal") {
    return (
      <div className={fieldsClass}>
        <label className="field">
          <span>Giới tính</span>
          <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
            <option value="">—</option>
            <option value="male">Nam</option>
            <option value="female">Nữ</option>
          </select>
        </label>
        <label className="field">
          <span>Ngày sinh</span>
          <input
            type="date"
            value={form.birth_date}
            onChange={(e) => setForm({ ...form, birth_date: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Điện thoại</span>
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </label>
        <LookupSelect
          groupCode="marital_status"
          label="Tình trạng hôn nhân"
          value={form.marital_status}
          onChange={(code) => setForm({ ...form, marital_status: code })}
          emptyLabel="— Chọn —"
        />
        <label className="field">
          <span>Số con</span>
          <input
            type="number"
            min={0}
            value={form.children_count}
            onChange={(e) => setForm({ ...form, children_count: e.target.value })}
          />
        </label>
        <LookupSelect
          groupCode="nationality"
          label="Quốc tịch"
          value={form.nationality_code}
          onChange={(code) => setForm({ ...form, nationality_code: code })}
        />
        <LookupSelect
          groupCode="ethnicity"
          label="Dân tộc"
          value={form.ethnicity_code}
          onChange={(code) => setForm({ ...form, ethnicity_code: code })}
        />
        <LookupSelect
          groupCode="religion"
          label="Tôn giáo"
          value={form.religion_code}
          onChange={(code) => setForm({ ...form, religion_code: code })}
        />
        <LookupSelect
          groupCode="education_level"
          label="Trình độ"
          value={form.education_code}
          onChange={(code) => setForm({ ...form, education_code: code })}
        />
      </div>
    );
  }

  if (tab === "address") {
    return (
      <div className={fieldsClass}>
        <label className="field">
          <span>Địa chỉ thường trú</span>
          <input
            value={form.permanent_address}
            onChange={(e) => setForm({ ...form, permanent_address: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Địa chỉ tạm trú</span>
          <input
            value={form.temporary_address}
            onChange={(e) => setForm({ ...form, temporary_address: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Số CCCD</span>
          <input
            value={form.id_number}
            onChange={(e) => setForm({ ...form, id_number: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Ngày cấp CCCD</span>
          <input
            type="date"
            value={form.id_issue_date}
            onChange={(e) => setForm({ ...form, id_issue_date: e.target.value })}
          />
        </label>
        <LookupSelect
          groupCode="id_issue_place"
          label="Nơi cấp CCCD"
          value={form.id_issue_place_code}
          onChange={(code) => setForm({ ...form, id_issue_place_code: code })}
        />
        <LookupSelect
          groupCode="birth_place"
          label="Nơi sinh"
          value={form.birth_place_code}
          onChange={(code) => setForm({ ...form, birth_place_code: code })}
        />
        <label className="field">
          <span>Liên hệ khẩn</span>
          <input
            value={form.urgent_contact}
            onChange={(e) => setForm({ ...form, urgent_contact: e.target.value })}
          />
        </label>
      </div>
    );
  }

  if (tab === "insurance") {
    const checks = (
      <div className="emp-insurance-checks">
        <label className="field emp-check-row" title="Tham gia BHXH">
          <input
            type="checkbox"
            checked={form.si_enrolled}
            onChange={(e) => setForm({ ...form, si_enrolled: e.target.checked })}
          />
          <span>BHXH</span>
        </label>
        <label className="field emp-check-row" title="Đóng thuế TNCN">
          <input
            type="checkbox"
            checked={form.pit_enrolled}
            onChange={(e) => setForm({ ...form, pit_enrolled: e.target.checked })}
          />
          <span>Thuế TNCN</span>
        </label>
      </div>
    );

    return (
      <div className={`${fieldsClass} emp-fields-insurance`}>
        {insuranceChecksFirst ? checks : null}
        <label className="field">
          <span>Số sổ BHXH</span>
          <input
            value={form.si_book_no}
            onChange={(e) => setForm({ ...form, si_book_no: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Tài khoản ngân hàng</span>
          <input
            value={form.bank_account}
            onChange={(e) => setForm({ ...form, bank_account: e.target.value })}
          />
        </label>
        {!insuranceChecksFirst ? checks : null}
        <label className="field">
          <span>Người phụ thuộc (tự tính)</span>
          <input
            className="emp-readonly"
            value={form.tax_dependent_count}
            readOnly
            title="Cập nhật qua màn Thân nhân & giảm trừ · Giảm trừ gia cảnh không nhập tay (21§21.3)"
          />
        </label>
        {insuranceChecksFirst ? (
          <details className="emp-insurance-advanced">
            <summary>Mức đóng / công đoàn (nâng cao)</summary>
            <label className="field">
              <span>Mức đóng BH (ghi đè)</span>
              <input
                value={form.si_base_override}
                onChange={(e) => setForm({ ...form, si_base_override: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Phí công đoàn (ghi đè)</span>
              <input
                value={form.union_fee_override}
                onChange={(e) => setForm({ ...form, union_fee_override: e.target.value })}
              />
            </label>
          </details>
        ) : (
          <>
            <label className="field">
              <span>Mức đóng BH (ghi đè)</span>
              <input
                value={form.si_base_override}
                onChange={(e) => setForm({ ...form, si_base_override: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Phí công đoàn (ghi đè)</span>
              <input
                value={form.union_fee_override}
                onChange={(e) => setForm({ ...form, union_fee_override: e.target.value })}
              />
            </label>
          </>
        )}
      </div>
    );
  }

  if (tab === "work") {
    return (
      <div className="emp-fields-grid">
        {teamSelect(form, setForm, departments, teams)}
        {positionSelect(form, setForm, positions)}
        <label className="field">
          <span>Trạng thái</span>
          <input
            className="emp-readonly"
            value={
              form.status === "active"
                ? "Chính thức"
                : form.status === "probation"
                  ? "Thử việc"
                  : form.status === "maternity"
                    ? "Thai sản"
                    : form.status === "resigned"
                      ? "Thôi việc"
                      : form.status
            }
            readOnly
            title="Dùng thanh «Chuyển trạng thái» phía trên"
          />
        </label>
        <label className="field">
          <span>Ngày vào</span>
          <input
            type="date"
            value={form.join_date}
            onChange={(e) => setForm({ ...form, join_date: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Ngày ký HĐ</span>
          <input
            type="date"
            value={form.contract_signed_at}
            onChange={(e) => setForm({ ...form, contract_signed_at: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Ngày nghỉ</span>
          <input
            type="date"
            value={form.resign_date}
            onChange={(e) => setForm({ ...form, resign_date: e.target.value })}
          />
        </label>
      </div>
    );
  }

  if (tab === "salary") {
    return (
      <div className="emp-fields-grid">
        <label className="field">
          <span>Lương HĐ</span>
          <input
            value={form.contract_salary}
            onChange={(e) => setForm({ ...form, contract_salary: e.target.value })}
            required
          />
        </label>
        <label className="field">
          <span>Lương thử việc</span>
          <input
            value={form.probation_salary}
            onChange={(e) => setForm({ ...form, probation_salary: e.target.value })}
          />
        </label>
        <label className="field">
          <span>Kênh lương</span>
          <select
            value={form.pay_channel}
            onChange={(e) => setForm({ ...form, pay_channel: e.target.value })}
          >
            <option value="ATM">ATM</option>
            <option value="CASH">Tiền mặt</option>
          </select>
        </label>
      </div>
    );
  }

  return null;
}
