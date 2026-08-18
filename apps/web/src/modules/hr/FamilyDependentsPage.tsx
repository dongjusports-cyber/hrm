import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  createFamilyMember,
  deleteFamilyMember,
  fetchEmployees,
  fetchFamilyMembers,
  fetchTaxDependents,
  updateFamilyMember,
  type Employee,
  type EmployeeFamilyMember,
  type TaxDependents,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { textMatchesQuery } from "../../shared/employeeSearch";
import { ToolbarSearchInput } from "../../shared/ToolbarSearchInput";

const RELATIONSHIPS = [
  { value: "cha", label: "Cha" },
  { value: "me", label: "Mẹ" },
  { value: "con", label: "Con" },
  { value: "chi", label: "Chị / em gái" },
  { value: "anh", label: "Anh / em trai" },
  { value: "khac", label: "Khác" },
];

function labelRelationship(code: string): string {
  return RELATIONSHIPS.find((r) => r.value === code)?.label ?? code;
}

const EMPTY_FORM = {
  relationship_code: "con",
  full_name: "",
  birth_date: "",
  is_tax_dependent: false,
  dependent_from: "",
  dependent_to: "",
};

/** Nhân Sự → Người phụ thuộc / thân nhân (5.3). Cũng nhúng trong Bảo Hiểm Thuế → tab Thuế. */
export function FamilyDependentsPage({ embedded = false }: { embedded?: boolean }) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [q, setQ] = useState("");
  const [selectedEmpId, setSelectedEmpId] = useState<string | null>(null);
  const [members, setMembers] = useState<EmployeeFamilyMember[]>([]);
  const [taxInfo, setTaxInfo] = useState<TaxDependents | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    void fetchEmployees({ status: "active" })
      .then(setEmployees)
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Không tải nhân viên.");
      });
  }, []);

  async function reloadMembers(empId: string) {
    const [list, tax] = await Promise.all([
      fetchFamilyMembers(empId),
      fetchTaxDependents(empId),
    ]);
    setMembers(list);
    setTaxInfo(tax);
  }

  useEffect(() => {
    if (!selectedEmpId) {
      setMembers([]);
      setTaxInfo(null);
      return;
    }
    void reloadMembers(selectedEmpId).catch((e: unknown) => {
      setError(e instanceof Error ? e.message : "Không tải thân nhân.");
    });
  }, [selectedEmpId]);

  const filteredEmployees = useMemo(() => {
    return employees.filter((e) =>
      textMatchesQuery(q, e.employee_code, e.full_name, e.department_code),
    );
  }, [employees, q]);

  const selectedEmployee = employees.find((e) => e.id === selectedEmpId);

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  function startEdit(m: EmployeeFamilyMember) {
    setEditingId(m.id);
    setForm({
      relationship_code: m.relationship_code,
      full_name: m.full_name,
      birth_date: m.birth_date ?? "",
      is_tax_dependent: m.is_tax_dependent,
      dependent_from: m.dependent_from ?? "",
      dependent_to: m.dependent_to ?? "",
    });
    setOk(null);
    setError(null);
  }

  function memberBody() {
    return {
      relationship_code: form.relationship_code,
      full_name: form.full_name.trim(),
      birth_date: form.birth_date || null,
      is_tax_dependent: form.is_tax_dependent,
      dependent_from: form.is_tax_dependent && form.dependent_from ? form.dependent_from : null,
      dependent_to: form.is_tax_dependent && form.dependent_to ? form.dependent_to : null,
    };
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!selectedEmpId) return;
    setError(null);
    setOk(null);
    try {
      if (editingId) {
        await updateFamilyMember(selectedEmpId, editingId, memberBody());
        setOk("Đã cập nhật thân nhân.");
      } else {
        await createFamilyMember(selectedEmpId, memberBody());
        setOk("Đã thêm thân nhân.");
      }
      resetForm();
      await reloadMembers(selectedEmpId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    }
  }

  async function onDelete(m: EmployeeFamilyMember) {
    if (!selectedEmpId) return;
    if (!window.confirm(`Xóa ${m.full_name}?`)) return;
    setError(null);
    setOk(null);
    try {
      await deleteFamilyMember(selectedEmpId, m.id);
      setOk("Đã xóa.");
      if (editingId === m.id) resetForm();
      await reloadMembers(selectedEmpId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    }
  }

  return (
    <div className={embedded ? "insurance-tab-panel" : "config-section-page"}>
      {!embedded && (
        <>
          <p className="field-hint">
            <Link to="/m/hr">← Nhân Sự</Link>
          </p>
          <h1>Người phụ thuộc &amp; thân nhân</h1>
        </>
      )}
      {embedded && <h2>Người phụ thuộc &amp; thân nhân</h2>}
      <p className="field-hint">
        Chọn nhân viên đang làm việc — quản lý thân nhân và khai báo phụ thuộc thuế TNCN.
      </p>
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      <div className="hr-split">
        <div className="users-form-card">
          <h2>Nhân viên ({filteredEmployees.length})</h2>
          <ToolbarSearchInput
            className="hr-search"
            placeholder="Tìm MSNV / họ tên / bộ phận"
            onQuery={setQ}
            style={{ width: "100%", marginBottom: 8 }}
          />
          <ul className="hr-board-list" style={{ maxHeight: "min(520px, 60vh)", overflow: "auto" }}>
            {filteredEmployees.map((emp) => (
              <li key={emp.id}>
                <button
                  type="button"
                  className={`hr-board-row${selectedEmpId === emp.id ? " is-selected" : ""}`}
                  onClick={() => {
                    setSelectedEmpId(emp.id);
                    resetForm();
                    setError(null);
                    setOk(null);
                  }}
                >
                  <span className="hr-board-main">
                    <strong>
                      {emp.employee_code} — {emp.full_name}
                    </strong>
                    <span className="field-hint">{emp.department_code || "—"}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="users-form-card">
          <h2>
            {selectedEmployee
              ? `${selectedEmployee.employee_code} — ${selectedEmployee.full_name}`
              : "Chọn nhân viên"}
          </h2>
          {taxInfo && (
            <>
              <p className="banner-ok" style={{ marginBottom: 8 }}>
                Người phụ thuộc hiệu lực (tính {formatDateDDMMYYYY(taxInfo.as_of_date)}):{" "}
                <strong>{taxInfo.effective_count}</strong>
              </p>
              <p className="field-hint emp-field-wide" style={{ marginBottom: 12 }}>
                Giảm trừ gia cảnh ước tính kỳ lương:{" "}
                <strong>
                  {(11_000_000 + taxInfo.effective_count * 4_400_000).toLocaleString("vi-VN")} đ
                </strong>{" "}
                (= 11.000.000 + {taxInfo.effective_count} × 4.400.000 — 24§nghiệm thu 5.3).
              </p>
            </>
          )}

          <table className="users-table">
            <thead>
              <tr>
                <th>Quan hệ</th>
                <th>Họ tên</th>
                <th>Ngày sinh</th>
                <th>PT thuế</th>
                <th>Từ — đến</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {!selectedEmpId && (
                <tr>
                  <td colSpan={6} className="field-hint">
                    Chưa chọn nhân viên.
                  </td>
                </tr>
              )}
              {selectedEmpId && members.length === 0 && (
                <tr>
                  <td colSpan={6} className="field-hint">
                    Chưa có thân nhân.
                  </td>
                </tr>
              )}
              {members.map((m) => (
                <tr key={m.id} className={editingId === m.id ? "is-selected" : undefined}>
                  <td>{labelRelationship(m.relationship_code)}</td>
                  <td>
                    {m.full_name}
                    {m.is_effective && (
                      <span className="field-hint"> · hiệu lực</span>
                    )}
                  </td>
                  <td>{formatDateDDMMYYYY(m.birth_date)}</td>
                  <td>{m.is_tax_dependent ? "Có" : "Không"}</td>
                  <td>
                    {m.is_tax_dependent
                      ? `${formatDateDDMMYYYY(m.dependent_from)} — ${formatDateDDMMYYYY(m.dependent_to)}`
                      : "—"}
                  </td>
                  <td className="dept-actions">
                    <button type="button" className="btn-ghost-dark" onClick={() => startEdit(m)}>
                      Sửa
                    </button>
                    <button type="button" className="btn-ghost-dark" onClick={() => void onDelete(m)}>
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {selectedEmpId && (
            <form className="emp-allow-add" onSubmit={(ev) => void onSubmit(ev)}>
              <h3>{editingId ? "Sửa thân nhân" : "Thêm thân nhân"}</h3>
              <label className="field">
                <span>Quan hệ</span>
                <select
                  value={form.relationship_code}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, relationship_code: e.target.value }))
                  }
                >
                  {RELATIONSHIPS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Họ tên</span>
                <input
                  value={form.full_name}
                  onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                  required
                />
              </label>
              <label className="field">
                <span>Ngày sinh</span>
                <input
                  type="date"
                  value={form.birth_date}
                  onChange={(e) => setForm((f) => ({ ...f, birth_date: e.target.value }))}
                />
              </label>
              <label className="field">
                <span>
                  <input
                    type="checkbox"
                    checked={form.is_tax_dependent}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, is_tax_dependent: e.target.checked }))
                    }
                  />{" "}
                  Khai phụ thuộc thuế TNCN
                </span>
              </label>
              {form.is_tax_dependent && (
                <>
                  <label className="field">
                    <span>Phụ thuộc từ</span>
                    <input
                      type="date"
                      value={form.dependent_from}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, dependent_from: e.target.value }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span>Phụ thuộc đến</span>
                    <input
                      type="date"
                      value={form.dependent_to}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, dependent_to: e.target.value }))
                      }
                    />
                  </label>
                </>
              )}
              <div className="hr-dept-row">
                <button type="submit" className="btn-primary">
                  {editingId ? "Lưu" : "Thêm"}
                </button>
                {editingId && (
                  <button type="button" className="btn-ghost-dark" onClick={resetForm}>
                    Hủy
                  </button>
                )}
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
