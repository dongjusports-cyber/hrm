import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  createEmployee,
  downloadEmployeeImportTemplate,
  fetchAllowanceTypes,
  fetchDepartments,
  fetchPositions,
  fetchTeams,
  importEmployeesExcel,
  suggestEmployeeCode,
  uploadEmployeePhoto,
  validateEmployee,
  type AllowanceAssignment,
  type AllowanceType,
  type Department,
  type Employee,
  type Position,
  type Team,
  type ValidationIssue,
} from "../../shared/api";
import { FullScreenSheet } from "../../shared/FullScreenSheet";
import { useSheetKeyboard } from "../../shared/formFieldEsc";
import { digitsOnlyMoney, emptyEmployeeForm, formToPayload } from "./employeeFormState";
import { EmployeeCreateFields } from "./EmployeeProfileFields";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: (employee: Employee) => void;
  onImported?: (detail: string) => void;
};

function formatAllowMoney(v: unknown): string {
  if (v === null || v === undefined || v === "") return "";
  try {
    return Number(v).toLocaleString("vi-VN");
  } catch {
    return String(v);
  }
}

/** Pilot full-screen overlay — tạo NV từ hub Nhân Sự. */
export function EmployeeCreateSheet({ open, onClose, onCreated, onImported }: Props) {
  const formShellRef = useRef<HTMLFormElement>(null);
  const [form, setForm] = useState(emptyEmployeeForm);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [allowTypes, setAllowTypes] = useState<AllowanceType[]>([]);
  const [allowances, setAllowances] = useState<AllowanceAssignment[]>([]);
  const [newAllowCode, setNewAllowCode] = useState("");
  const [newAllowAmount, setNewAllowAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
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
    setOk(null);
    setIssues([]);
    setSaving(false);
    setPhotoFile(null);
    setAllowTypes([]);
    setAllowances([]);
    setNewAllowCode("");
    setNewAllowAmount("");
    setPhotoPreview((prev) => {
      if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
      return null;
    });
    void fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    void fetchTeams().then(setTeams).catch(() => setTeams([]));
    void fetchPositions().then(setPositions).catch(() => setPositions([]));
    void fetchAllowanceTypes().then(setAllowTypes).catch(() => setAllowTypes([]));
    void suggestEmployeeCode()
      .then((code) => setForm((f) => ({ ...f, employee_code: code })))
      .catch(() => undefined);
  }, [open]);

  useEffect(() => {
    return () => {
      if (photoPreview?.startsWith("blob:")) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  useSheetKeyboard({ open, containerRef: formShellRef, onClose });

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

  function onAddAllow() {
    const code = newAllowCode.trim().toUpperCase();
    if (!code) return;
    const t = allowTypes.find((x) => x.code === code);
    const amount = digitsOnlyMoney(newAllowAmount.trim());
    const row: AllowanceAssignment = {
      id: `draft:${code}`,
      employee_code: form.employee_code.trim() || "new",
      full_name: form.full_name.trim(),
      allowance_code: code,
      allowance_name: t?.name ?? code,
      amount,
      include_in_si_base: Boolean(t?.include_in_si_base),
      include_in_ot_base: Boolean(t?.include_in_ot_base),
    };
    setAllowances((prev) => {
      const rest = prev.filter((a) => a.allowance_code !== code);
      return [...rest, row];
    });
    setNewAllowCode("");
    setNewAllowAmount("");
  }

  function onDeleteAllow(id: string) {
    setAllowances((prev) => prev.filter((a) => a.id !== id));
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
        allowances: allowances.map((a) => ({
          allowance_code: a.allowance_code,
          amount: digitsOnlyMoney(String(a.amount ?? "0")),
        })),
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

  async function onDownloadTemplate() {
    setError(null);
    try {
      await downloadEmployeeImportTemplate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được file mẫu.");
    }
  }

  async function onImportExcel(file: File | null) {
    if (!file) return;
    setError(null);
    setOk(null);
    setSaving(true);
    try {
      const result = await importEmployeesExcel(file);
      const extra = result.errors[0] ? ` — ${result.errors[0]}` : "";
      setOk(result.detail + extra);
      onImported?.(result.detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nhập Excel thất bại.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <FullScreenSheet
      open={open}
      title="Tạo nhân viên"
      subtitle="Đủ trường như Hồ sơ NV · Tải mẫu Excel rồi nạp hàng loạt · Esc: hoàn tác ô / đóng"
      onClose={onClose}
      closeOnEsc={false}
      bodyClassName="fs-sheet-body-create"
      actions={
        <>
          <button
            type="button"
            className="btn-secondary"
            disabled={saving}
            onClick={() => void onDownloadTemplate()}
          >
            Tải mẫu Excel
          </button>
          <label className={`btn-secondary emp-create-import${saving ? " is-disabled" : ""}`}>
            Nhập Excel
            <input
              type="file"
              accept=".xlsx,.xlsm"
              hidden
              disabled={saving}
              onChange={(e) => {
                void onImportExcel(e.target.files?.[0] ?? null);
                e.target.value = "";
              }}
            />
          </label>
          <button
            type="submit"
            form="emp-create-sheet-form"
            className="btn-primary"
            disabled={saving}
          >
            {saving ? "Đang lưu…" : "Tạo nhân viên"}
          </button>
        </>
      }
    >
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}
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
        noValidate
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
          allowancePanel={{
            allowances,
            allowTypes,
            newAllowCode,
            setNewAllowCode,
            newAllowAmount,
            setNewAllowAmount,
            saving,
            onAdd: onAddAllow,
            onDelete: onDeleteAllow,
            formatMoney: formatAllowMoney,
          }}
        />
      </form>
    </FullScreenSheet>
  );
}
