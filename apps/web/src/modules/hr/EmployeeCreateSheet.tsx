import { FormEvent, useEffect, useState } from "react";
import { createEmployee, fetchDepartments, fetchTeams, type Department, type Employee, type Team } from "../../shared/api";
import { FullScreenSheet } from "../../shared/FullScreenSheet";
import { emptyEmployeeForm, formToPayload } from "./employeeFormState";
import { EmployeeCreateFields } from "./EmployeeProfileFields";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: (employee: Employee) => void;
};

/** Pilot full-screen overlay — tạo NV từ hub Nhân Sự. */
export function EmployeeCreateSheet({ open, onClose, onCreated }: Props) {
  const [form, setForm] = useState(emptyEmployeeForm);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(emptyEmployeeForm);
    setError(null);
    setSaving(false);
    void fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    void fetchTeams().then(setTeams).catch(() => setTeams([]));
  }, [open]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const created = await createEmployee({
        employee_code: form.employee_code.trim(),
        ...formToPayload(form, true),
      });
      onCreated(created);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tạo được nhân viên.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <FullScreenSheet
      open={open}
      title="Tạo nhân viên"
      subtitle="Nhập tối thiểu — danh sách NV vẫn hiển thị phía sau. Esc hoặc × để đóng."
      onClose={onClose}
      actions={
        <button
          type="submit"
          form="emp-create-sheet-form"
          className="btn-primary"
          disabled={saving}
        >
          {saving ? "Đang lưu…" : "Tạo nhân viên"}
        </button>
      }
    >
      {error && <p className="banner-warn">{error}</p>}
      <form id="emp-create-sheet-form" className="fs-sheet-form" onSubmit={(ev) => void onSubmit(ev)}>
        <EmployeeCreateFields
          form={form}
          setForm={setForm}
          tab="work"
          isNew
          departments={departments}
          teams={teams}
        />
      </form>
    </FullScreenSheet>
  );
}
