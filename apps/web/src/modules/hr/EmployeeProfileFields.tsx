import type { Department, Team } from "../../shared/api";
import { LookupSelect } from "../../shared/LookupSelect";
import {
  activeTeams,
  departmentsWithActiveTeams,
  formatDepartmentLabel,
  formatTeamLabel,
} from "../../shared/formatOrg";
import type { EmployeeFormState, ProfileTab } from "./employeeFormState";

type Props = {
  form: EmployeeFormState;
  setForm: (next: EmployeeFormState) => void;
  tab: ProfileTab;
  isNew: boolean;
  departments: Department[];
  teams: Team[];
};

function teamSelect(
  form: EmployeeFormState,
  setForm: (next: EmployeeFormState) => void,
  departments: Department[],
  teams: Team[],
) {
  const deptOptions = departmentsWithActiveTeams(departments, teams);
  const teamOptions = activeTeams(teams).filter(
    (t) => !form.department_code || t.department_code === form.department_code,
  );

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
      <label className="field">
        <span>Tổ *</span>
        <select
          value={form.team_id}
          onChange={(e) => setForm({ ...form, team_id: e.target.value })}
          required
        >
          <option value="">— Chọn tổ —</option>
          {teamOptions.map((t) => (
            <option key={t.id} value={t.id}>
              {formatTeamLabel(t, { showDepartment: !form.department_code })}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

/** Form tạo mới — 9 trường bắt buộc, một màn, 3 nhóm (không cần chuyển tab). */
export function EmployeeCreateFields({ form, setForm, departments, teams }: Props) {
  return (
    <div className="emp-create-sections">
      <p className="field-hint emp-create-lead">
        Nhập <strong>một lần</strong> rồi bấm «Tạo nhân viên». CCCD, BHXH, phụ cấp… bổ sung sau ở hồ sơ
        (tab Tổng hợp).
      </p>

      <fieldset className="emp-form-section">
        <legend>Định danh</legend>
        <div className="emp-fields-grid emp-fields-dense">
          <label className="field">
            <span>MSNV *</span>
            <input
              value={form.employee_code}
              onChange={(e) => setForm({ ...form, employee_code: e.target.value })}
              required
              autoFocus
            />
          </label>
          <label className="field emp-field-span-2">
            <span>Họ tên *</span>
            <input
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="emp-form-section">
        <legend>Công việc</legend>
        <div className="emp-fields-grid emp-fields-dense">
          {teamSelect(form, setForm, departments, teams)}
          <label className="field">
            <span>Chức vụ</span>
            <input
              value={form.position_title}
              onChange={(e) => setForm({ ...form, position_title: e.target.value })}
            />
          </label>
          <label className="field">
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
          <label className="field">
            <span>Ngày vào</span>
            <input
              type="date"
              value={form.join_date}
              onChange={(e) => setForm({ ...form, join_date: e.target.value })}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="emp-form-section">
        <legend>Lương</legend>
        <div className="emp-fields-grid emp-fields-dense">
          <label className="field">
            <span>Lương HĐ *</span>
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
      </fieldset>
    </div>
  );
}

const PROFILE_SECTIONS: { id: ProfileTab; title: string }[] = [
  { id: "work", title: "Công việc" },
  { id: "personal", title: "Cá nhân" },
  { id: "address", title: "Cư trú & giấy tờ" },
  { id: "insurance", title: "Bảo hiểm" },
  { id: "salary", title: "Lương" },
];

/** Một trang cuộn — sửa hồ sơ không cần chuyển tab. */
export function EmployeeProfileAllFields({ form, setForm, departments, teams }: Omit<Props, "tab" | "isNew">) {
  return (
    <div className="emp-profile-all">
      {PROFILE_SECTIONS.map((sec) => (
        <section key={sec.id} className="emp-form-section" aria-labelledby={`emp-sec-${sec.id}`}>
          <h3 id={`emp-sec-${sec.id}`} className="emp-form-section-title">
            {sec.title}
          </h3>
          <EmployeeProfileTabFields
            form={form}
            setForm={setForm}
            tab={sec.id}
            isNew={false}
            departments={departments}
            teams={teams}
          />
        </section>
      ))}
    </div>
  );
}

export function EmployeeProfileTabFields({ form, setForm, tab, departments, teams }: Props) {
  if (tab === "personal") {
    return (
      <div className="emp-fields-grid">
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
          <span>Tình trạng hôn nhân</span>
          <input
            value={form.marital_status}
            onChange={(e) => setForm({ ...form, marital_status: e.target.value })}
          />
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
      <div className="emp-fields-grid">
        <label className="field emp-field-full">
          <span>Địa chỉ thường trú</span>
          <input
            value={form.permanent_address}
            onChange={(e) => setForm({ ...form, permanent_address: e.target.value })}
          />
        </label>
        <label className="field emp-field-full">
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
        <label className="field emp-field-full">
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
    return (
      <div className="emp-fields-grid">
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
        <label className="field">
          <span>Người phụ thuộc (tự tính)</span>
          <input
            className="emp-readonly"
            value={form.tax_dependent_count}
            readOnly
            title="Cập nhật qua màn Thân nhân & giảm trừ"
          />
        </label>
        <p className="field-hint emp-field-full">
          Giảm trừ gia cảnh tính từ bảng thân nhân — không nhập tay (21§21.3).
        </p>
        <label className="field emp-check-row">
          <input
            type="checkbox"
            checked={form.si_enrolled}
            onChange={(e) => setForm({ ...form, si_enrolled: e.target.checked })}
          />
          <span>Tham gia BHXH</span>
        </label>
        <label className="field emp-check-row">
          <input
            type="checkbox"
            checked={form.pit_enrolled}
            onChange={(e) => setForm({ ...form, pit_enrolled: e.target.checked })}
          />
          <span>Đóng thuế TNCN</span>
        </label>
      </div>
    );
  }

  if (tab === "work") {
    return (
      <div className="emp-fields-grid">
        {teamSelect(form, setForm, departments, teams)}
        <label className="field">
          <span>Chức vụ</span>
          <input
            value={form.position_title}
            onChange={(e) => setForm({ ...form, position_title: e.target.value })}
          />
        </label>
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
