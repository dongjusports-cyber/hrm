import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  createEmployee,
  fetchDepartments,
  fetchPositions,
  fetchTeams,
  suggestEmployeeCode,
  uploadEmployeePhoto,
  validateEmployee,
  type Department,
  type Employee,
  type Position,
  type Team,
  type ValidationIssue,
} from "../../shared/api";
import { FullScreenSheet } from "../../shared/FullScreenSheet";
import { useSheetKeyboard } from "../../shared/formFieldEsc";
import { emptyEmployeeForm, formToPayload } from "./employeeFormState";
import { EmployeeCreateFields } from "./EmployeeProfileFields";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: (employee: Employee) => void;
};

/** Pilot full-screen overlay — tạo NV từ hub Nhân Sự. */
export function EmployeeCreateSheet({ open, onClose, onCreated }: Props) {
  const formShellRef = useRef<HTMLFormElement>(null);
  const [form, setForm] = useState(emptyEmployeeForm);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [saving, setSaving] = useState(false);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  const fieldErrors = useMemo(() => {
    const map: Record<string, string> = {};
    for (const i of issues) {
      if (i.level === "error" && !map[i.field]) map[i.field] = i.message;
    }
    return map;
  }, [issues]);

  useEffect(() => {
    if (!open) return;
    setForm(emptyEmployeeForm);
    setError(null);
    setIssues([]);
    setSaving(false);
    setPhotoFile(null);
    setPhotoPreview((prev) => {
      if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
      return null;
    });
    void fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    void fetchTeams().then(setTeams).catch(() => setTeams([]));
    void fetchPositions().then(setPositions).catch(() => setPositions([]));
    void suggestEmployeeCode()
      .then((code) => setForm((f) => ({ ...f, employee_code: code })))
      .catch(() => undefined);
  }, [open]);

  useEffect(() => {
    return () => {
      if (photoPreview?.startsWith("blob:")) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  useSheetKeyboard({ open, containerRef: formShellRef });

  function onPhotoPick(file: File | null) {
    if (file && !file.type.startsWith("image/")) {
      setError("Vui lòng chọn file ảnh (JPG/PNG/WEBP).");
      return;
    }
    setPhotoFile(file);
    setPhotoPreview((prev) => {
      if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
      return file ? URL.createObjectURL(file) : null;
    });
  }

  async function runValidate(): Promise<ValidationIssue[]> {
    const payload = {
      employee_code: form.employee_code.trim(),
      ...formToPayload(form, true),
    };
    const res = await validateEmployee({ is_new: true, payload });
    setIssues(res.issues);
    return res.issues;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const found = await runValidate();
      const errors = found.filter((i) => i.level === "error");
      if (errors.length > 0) {
        setError(errors[0].message);
        return;
      }
      const warns = found.filter((i) => i.level === "warn");
      if (
        warns.length > 0 &&
        !window.confirm(`${warns[0].message}\n\nVẫn tạo nhân viên?`)
      ) {
        return;
      }
      const created = await createEmployee({
        employee_code: form.employee_code.trim(),
        ...formToPayload(form, true),
      });
      if (photoFile) {
        await uploadEmployeePhoto(created.id, photoFile);
      }
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
      subtitle="* bắt buộc · MSNV gợi ý tự động · Esc: hoàn tác ô nhập · Đóng: nút ×"
      onClose={onClose}
      bodyClassName="fs-sheet-body-create"
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
      {issues.some((i) => i.level === "warn") && (
        <ul className="emp-validate-warns">
          {issues
            .filter((i) => i.level === "warn")
            .map((i) => (
              <li key={`${i.field}-${i.code}`}>{i.message}</li>
            ))}
        </ul>
      )}
      <form
        id="emp-create-sheet-form"
        ref={formShellRef}
        className="fs-sheet-form emp-create-form"
        onSubmit={(ev) => void onSubmit(ev)}
      >
        <EmployeeCreateFields
          form={form}
          setForm={setForm}
          departments={departments}
          teams={teams}
          positions={positions}
          fieldErrors={fieldErrors}
          photoPreview={photoPreview}
          onPhotoPick={onPhotoPick}
          photoDisabled={saving}
        />
      </form>
    </FullScreenSheet>
  );
}
