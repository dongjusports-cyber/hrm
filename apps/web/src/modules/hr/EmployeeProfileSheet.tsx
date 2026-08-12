import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  createEmployeeDocument,
  createEmployeeViolation,
  deleteAllowanceAssignment,
  deleteEmployeeDocument,
  deleteEmployeeViolation,
  fetchAllowanceAssignments,
  fetchAllowanceTypes,
  fetchDepartments,
  fetchDocumentFileObjectUrl,
  fetchEmployee,
  fetchEmployeeDocuments,
  fetchEmployeePhotoObjectUrl,
  fetchEmployeeViolations,
  fetchTeams,
  printEmployeeContract,
  printEmployeeDecision,
  printEmployeeProbation,
  updateEmployee,
  uploadEmployeePhoto,
  upsertAllowanceAssignment,
  type AllowanceAssignment,
  type AllowanceType,
  type Department,
  type Employee,
  type EmployeeDocument,
  type EmployeeViolation,
  type Team,
} from "../../shared/api";
import { formatDateTimeDDMMYYYY } from "../../shared/formatDate";
import { FullScreenSheet } from "../../shared/FullScreenSheet";
import { labelEmpStatus } from "../../shared/viLabels";
import { digitsOnlyMoney, emptyEmployeeForm, employeeToForm, formToPayload, type EmployeeFormState } from "./employeeFormState";
import { EmployeeExperiencePanel } from "./EmployeeExperiencePanel";
import { EmployeeProfileCompactFields } from "./EmployeeProfileFields";

const DOC_TYPE_LABELS: Record<string, string> = {
  contract: "Hợp đồng",
  id_card: "CCCD / giấy tờ",
  resume: "Sơ yếu lý lịch",
  certificate: "Chứng chỉ / bằng",
  other: "Khác",
};

const STATUS_ACTIONS: { status: string; label: string }[] = [
  { status: "active", label: "Chính thức" },
  { status: "probation", label: "Thử việc" },
  { status: "maternity", label: "Thai sản" },
  { status: "resigned", label: "Thôi việc" },
];

type ExtraTab = "experience" | "violations" | "documents";

function toDateInput(v: string | null | undefined): string {
  if (!v) return "";
  const s = String(v).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  return "";
}

function formatMoney(v: unknown): string {
  if (v === null || v === undefined || v === "") return "";
  try {
    return Number(v).toLocaleString("vi-VN");
  } catch {
    return String(v);
  }
}

type Props = {
  employeeId: string;
  open: boolean;
  onClose: () => void;
  onUpdated?: () => void;
};

type UndoSnapshot = {
  form: EmployeeFormState;
  allowances: AllowanceAssignment[];
};

const UNDO_MAX = 25;
const UNDO_DEBOUNCE_MS = 450;

/** Overlay full màn — hồ sơ một trang, không cuộn tab chính. */
export function EmployeeProfileSheet({ employeeId, open, onClose, onUpdated }: Props) {
  const [extraTab, setExtraTab] = useState<ExtraTab | null>(null);
  const [form, setForm] = useState(emptyEmployeeForm);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [allowTypes, setAllowTypes] = useState<AllowanceType[]>([]);
  const [allowances, setAllowances] = useState<AllowanceAssignment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [emp, setEmp] = useState<Employee | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [newAllowCode, setNewAllowCode] = useState("");
  const [newAllowAmount, setNewAllowAmount] = useState("0");
  const [violations, setViolations] = useState<EmployeeViolation[]>([]);
  const [documents, setDocuments] = useState<EmployeeDocument[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const [vTitle, setVTitle] = useState("");
  const [vWhen, setVWhen] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}T08:00`;
  });
  const [vPenalty, setVPenalty] = useState("");
  const [vDesc, setVDesc] = useState("");
  const [vFile, setVFile] = useState<File | null>(null);
  const [dType, setDType] = useState("id_card");
  const [dTitle, setDTitle] = useState("");
  const [dNote, setDNote] = useState("");
  const [dFile, setDFile] = useState<File | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const undoStackRef = useRef<UndoSnapshot[]>([]);
  const undoDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const skipUndoPushRef = useRef(false);
  const formRef = useRef(form);
  const allowancesRef = useRef(allowances);
  formRef.current = form;
  allowancesRef.current = allowances;

  const pushUndoSnapshot = useCallback(() => {
    if (skipUndoPushRef.current) return;
    undoStackRef.current.push({
      form: { ...formRef.current },
      allowances: allowancesRef.current.map((a) => ({ ...a })),
    });
    if (undoStackRef.current.length > UNDO_MAX) undoStackRef.current.shift();
    setCanUndo(true);
  }, []);

  const setFormUndoable = useCallback(
    (next: EmployeeFormState | ((prev: EmployeeFormState) => EmployeeFormState)) => {
      if (!skipUndoPushRef.current) {
        if (!undoDebounceRef.current) pushUndoSnapshot();
        if (undoDebounceRef.current) clearTimeout(undoDebounceRef.current);
        undoDebounceRef.current = setTimeout(() => {
          undoDebounceRef.current = null;
        }, UNDO_DEBOUNCE_MS);
      }
      setForm(next);
    },
    [pushUndoSnapshot],
  );

  const onUndoRef = useRef<() => void>(() => undefined);

  function onUndo() {
    const prev = undoStackRef.current.pop();
    if (!prev) {
      setCanUndo(false);
      return;
    }
    skipUndoPushRef.current = true;
    if (undoDebounceRef.current) {
      clearTimeout(undoDebounceRef.current);
      undoDebounceRef.current = null;
    }
    setForm(prev.form);
    setAllowances(prev.allowances);
    skipUndoPushRef.current = false;
    setCanUndo(undoStackRef.current.length > 0);
    setOk("Đã hoàn tác.");
    setError(null);
  }

  onUndoRef.current = onUndo;

  useEffect(() => {
    if (!ok) return;
    const t = window.setTimeout(() => setOk(null), 2800);
    return () => window.clearTimeout(t);
  }, [ok]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        onUndoRef.current();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (!open) {
      setExtraTab(null);
      undoStackRef.current = [];
      setCanUndo(false);
      return;
    }
    void fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    void fetchTeams().then(setTeams).catch(() => setTeams([]));
    void fetchAllowanceTypes()
      .then((list) => {
        setAllowTypes(list);
      })
      .catch(() => setAllowTypes([]));
  }, [open]);

  useEffect(() => {
    if (!open || !employeeId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const e = await fetchEmployee(employeeId);
        if (cancelled) return;
        setEmp(e);
        setForm(employeeToForm(e, toDateInput));
        const loadedAllowances = await fetchAllowanceAssignments(e.employee_code);
        setAllowances(loadedAllowances);
        undoStackRef.current = [];
        setCanUndo(false);
        setViolations(await fetchEmployeeViolations(e.id));
        setDocuments(await fetchEmployeeDocuments(e.id));
        if (e.has_photo) {
          const url = await fetchEmployeePhotoObjectUrl(e.id);
          if (!cancelled) {
            setPhotoUrl((prev) => {
              if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
              return url;
            });
          } else if (url) URL.revokeObjectURL(url);
        } else {
          setPhotoUrl(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không tải hồ sơ.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, employeeId]);

  useEffect(() => {
    return () => {
      if (photoUrl?.startsWith("blob:")) URL.revokeObjectURL(photoUrl);
    };
  }, [photoUrl]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    setSaving(true);
    try {
      const updated = await updateEmployee(employeeId, formToPayload(form, false));
      setEmp(updated);
      setOk("Đã lưu hồ sơ.");
      undoStackRef.current = [];
      setCanUndo(false);
      onUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại.");
    } finally {
      setSaving(false);
    }
  }

  async function onPhotoPicked(file: File | null) {
    if (!file?.type.startsWith("image/")) {
      setError("Vui lòng chọn file ảnh (JPG/PNG/WEBP).");
      return;
    }
    setSaving(true);
    try {
      const updated = await uploadEmployeePhoto(employeeId, file);
      setEmp(updated);
      const url = await fetchEmployeePhotoObjectUrl(updated.id);
      setPhotoUrl((prev) => {
        if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
        return url;
      });
      setOk("Đã cập nhật ảnh.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải ảnh.");
    } finally {
      setSaving(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function changeStatus(next: string) {
    if (form.status === next) return;
    const label = labelEmpStatus(next);
    if (!window.confirm(`Chuyển ${form.full_name || form.employee_code} sang «${label}»?`)) return;
    let resignDate = form.resign_date;
    if (next === "resigned" && !resignDate) {
      const t = new Date();
      resignDate = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    }
    setSaving(true);
    try {
      const updated = await updateEmployee(employeeId, {
        status: next,
        resign_date: next === "resigned" ? resignDate || null : null,
      });
      setEmp(updated);
      setForm((prev) => ({
        ...prev,
        status: updated.status,
        resign_date: toDateInput(updated.resign_date),
      }));
      setOk(`Đã chuyển sang «${labelEmpStatus(updated.status)}».`);
      onUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đổi trạng thái.");
    } finally {
      setSaving(false);
    }
  }

  async function onAddAllow() {
    pushUndoSnapshot();
    setSaving(true);
    try {
      await upsertAllowanceAssignment({
        employee_code: form.employee_code,
        allowance_code: newAllowCode,
        amount: digitsOnlyMoney(newAllowAmount.trim()),
      });
      setAllowances(await fetchAllowanceAssignments(form.employee_code));
      setNewAllowAmount("0");
      setOk(`Đã gán phụ cấp ${newAllowCode}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gán phụ cấp.");
    } finally {
      setSaving(false);
    }
  }

  async function onDeleteAllow(id: string) {
    if (!window.confirm("Xóa phụ cấp này?")) return;
    pushUndoSnapshot();
    setSaving(true);
    try {
      await deleteAllowanceAssignment(id);
      setAllowances(await fetchAllowanceAssignments(form.employee_code));
      setOk("Đã xóa phụ cấp.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa phụ cấp.");
    } finally {
      setSaving(false);
    }
  }

  async function onAddViolation() {
    if (!vTitle.trim()) {
      setError("Cần tiêu đề vi phạm.");
      return;
    }
    setSaving(true);
    try {
      await createEmployeeViolation(employeeId, {
        occurred_at: new Date(vWhen).toISOString(),
        title: vTitle.trim(),
        description: vDesc.trim(),
        penalty: vPenalty.trim(),
        file: vFile,
      });
      setViolations(await fetchEmployeeViolations(employeeId));
      setVTitle("");
      setVPenalty("");
      setVDesc("");
      setVFile(null);
      setOk("Đã ghi biên bản.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không ghi vi phạm.");
    } finally {
      setSaving(false);
    }
  }

  async function onAddDocument() {
    if (!dFile) {
      setError("Cần file hồ sơ giấy.");
      return;
    }
    setSaving(true);
    try {
      await createEmployeeDocument(employeeId, {
        title: dTitle.trim() || DOC_TYPE_LABELS[dType] || "Hồ sơ giấy",
        doc_type: dType,
        note: dNote.trim(),
        file: dFile,
      });
      setDocuments(await fetchEmployeeDocuments(employeeId));
      setDTitle("");
      setDNote("");
      setDFile(null);
      setOk("Đã lưu hồ sơ giấy.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu hồ sơ.");
    } finally {
      setSaving(false);
    }
  }

  const title = form.full_name
    ? `${form.employee_code} · ${form.full_name}`
    : loading
      ? "Đang tải…"
      : "Hồ sơ nhân viên";

  const extraTabs: { id: ExtraTab; label: string; count?: number }[] = [
    { id: "experience", label: "Kinh nghiệm" },
    { id: "violations", label: "Vi phạm", count: violations.length },
    { id: "documents", label: "Hồ sơ giấy", count: documents.length },
  ];

  return (
    <FullScreenSheet open={open} title={title} hideHeader onClose={onClose} onBeforeClose={() => {
      if (extraTab !== null) {
        setExtraTab(null);
        return true;
      }
      return false;
    }}>
      <div className="fs-sheet-layout">
        {loading ? (
          <p className="field-hint fs-sheet-loading">Đang tải hồ sơ…</p>
        ) : (
          <form
            id="emp-sheet-form"
            className={`emp-sheet-form-shell${extraTab === null ? " emp-sheet-form-shell--fixed" : ""}`}
            onSubmit={(ev) => void onSubmit(ev)}
          >
            <div className="fs-sheet-pinned">
              <div className="emp-sheet-header">
                <div className="emp-sheet-header-main">
                  <div className="emp-sheet-identity-top">
                    <label className="field emp-sheet-msnv">
                      <span>MSNV</span>
                      <input value={form.employee_code} readOnly className="emp-readonly" />
                    </label>
                    <label className="field emp-sheet-name">
                      <span>Họ tên</span>
                      <input
                        value={form.full_name}
                        onChange={(e) => setFormUndoable({ ...form, full_name: e.target.value })}
                        required
                      />
                    </label>
                  </div>

                  <div className="emp-sheet-toolbar">
                    <nav className="emp-sheet-subtabs" role="tablist" aria-label="Phần hồ sơ">
                      <button
                        type="button"
                        role="tab"
                        aria-selected={extraTab === null}
                        className={extraTab === null ? "emp-subtab active" : "emp-subtab"}
                        onClick={() => setExtraTab(null)}
                      >
                        Hồ sơ chính
                      </button>
                      {extraTabs.map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          role="tab"
                          aria-selected={extraTab === t.id}
                          className={extraTab === t.id ? "emp-subtab active" : "emp-subtab"}
                          onClick={() => setExtraTab(t.id)}
                        >
                          {t.label}
                          {t.count ? ` (${t.count})` : ""}
                        </button>
                      ))}
                      <Link
                        to={`/m/hr/contracts?employee_id=${employeeId}`}
                        className="emp-subtab emp-subtab-link"
                      >
                        Hợp đồng
                      </Link>
                    </nav>
                    {extraTab === null && (
                      <>
                        <button
                          type="button"
                          className="btn-ghost-dark btn-sm"
                          disabled={saving}
                          onClick={() =>
                            void printEmployeeContract(employeeId).catch((e) => setError(String(e)))
                          }
                        >
                          In HĐ
                        </button>
                        {form.status === "probation" && (
                          <button
                            type="button"
                            className="btn-ghost-dark btn-sm"
                            disabled={saving}
                            onClick={() =>
                              void printEmployeeProbation(employeeId).catch((e) => setError(String(e)))
                            }
                          >
                            In TV
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn-ghost-dark btn-sm"
                          disabled={saving}
                          onClick={() =>
                            void printEmployeeDecision(employeeId).catch((e) => setError(String(e)))
                          }
                        >
                          In QĐ
                        </button>
                      </>
                    )}
                    <label className="emp-sheet-status-field">
                      <span>Trạng thái:</span>
                      <select
                        value={form.status}
                        disabled={saving}
                        onChange={(e) => void changeStatus(e.target.value)}
                      >
                        {STATUS_ACTIONS.map((a) => (
                          <option key={a.status} value={a.status}>
                            {a.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    {extraTab === null && (
                      <button type="submit" className="btn-primary btn-sm" disabled={saving}>
                        {saving ? "Đang lưu…" : "Lưu hồ sơ"}
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-ghost-dark btn-sm"
                      disabled={saving || !canUndo}
                      title="Hoàn tác thay đổi chưa lưu (Ctrl+Z) · Đóng: Esc hoặc bấm nền tối"
                      onClick={() => onUndo()}
                    >
                      ↶ Hoàn tác
                    </button>
                    <button
                      type="button"
                      className="btn-ghost-dark btn-sm"
                      disabled={saving}
                      onClick={onClose}
                    >
                      × Đóng
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  className="emp-photo emp-photo-sheet"
                  onClick={() => fileRef.current?.click()}
                  disabled={saving}
                  title="Bấm để đổi ảnh"
                >
                  {photoUrl ? (
                    <img src={photoUrl} alt={form.full_name || "Ảnh NV"} />
                  ) : (
                    <span className="emp-photo-empty">
                      <strong>Ảnh</strong>
                    </span>
                  )}
                </button>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/*"
                  hidden
                  onChange={(e) => void onPhotoPicked(e.target.files?.[0] ?? null)}
                />
              </div>
            </div>

            {(error || ok) && (
              <div className="fs-sheet-toast-host" role="status" aria-live="polite">
                {error && <p className="banner-warn fs-sheet-banner">{error}</p>}
                {ok && <p className="banner-ok fs-sheet-banner">{ok}</p>}
              </div>
            )}

            {extraTab === "experience" ? (
              <div className="fs-sheet-scroll emp-sheet-fields-scroll">
            <section className="emp-sheet-extra users-form-card">
              <EmployeeExperiencePanel empId={employeeId} />
            </section>
          </div>
        ) : extraTab === "violations" ? (
              <div className="fs-sheet-scroll emp-sheet-fields-scroll">
            <section className="emp-sheet-extra users-form-card">
          <h2>Vi phạm / biên bản</h2>
          <div className="emp-viol-form emp-panel-form">
            <label className="field">
              <span>Thời gian</span>
              <input type="datetime-local" value={vWhen} onChange={(e) => setVWhen(e.target.value)} />
            </label>
            <label className="field">
              <span>Tiêu đề</span>
              <input value={vTitle} onChange={(e) => setVTitle(e.target.value)} />
            </label>
            <label className="field">
              <span>Hình thức / phạt</span>
              <input value={vPenalty} onChange={(e) => setVPenalty(e.target.value)} />
            </label>
            <label className="field emp-field-full">
              <span>Chi tiết</span>
              <input value={vDesc} onChange={(e) => setVDesc(e.target.value)} />
            </label>
            <label className="field emp-field-full">
              <span>File scan</span>
              <input
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                onChange={(e) => setVFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <button type="button" className="btn-primary" disabled={saving} onClick={() => void onAddViolation()}>
              Ghi biên bản
            </button>
          </div>
          <ul className="emp-viol-list emp-panel-list">
            {violations.length === 0 && <li className="module-placeholder">Chưa có biên bản.</li>}
            {violations.map((v) => (
              <li key={v.id}>
                <div>
                  <strong>{v.title}</strong>
                  <span className="field-hint">
                    {formatDateTimeDDMMYYYY(v.occurred_at)}
                    {v.penalty ? ` · ${v.penalty}` : ""}
                  </span>
                </div>
                <button
                  type="button"
                  className="link-btn danger"
                  disabled={saving}
                  onClick={() =>
                    void deleteEmployeeViolation(employeeId, v.id).then(() =>
                      fetchEmployeeViolations(employeeId).then(setViolations),
                    )
                  }
                >
                  Xóa
                </button>
              </li>
            ))}
          </ul>
            </section>
          </div>
        ) : extraTab === "documents" ? (
              <div className="fs-sheet-scroll emp-sheet-fields-scroll">
            <section className="emp-sheet-extra users-form-card">
          <h2>Hồ sơ giấy</h2>
          <div className="emp-viol-form emp-panel-form">
            <label className="field">
              <span>Loại</span>
              <select value={dType} onChange={(e) => setDType(e.target.value)}>
                {Object.entries(DOC_TYPE_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Tiêu đề</span>
              <input value={dTitle} onChange={(e) => setDTitle(e.target.value)} />
            </label>
            <label className="field emp-field-full">
              <span>File</span>
              <input
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                onChange={(e) => setDFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <button
              type="button"
              className="btn-primary"
              disabled={saving || !dFile}
              onClick={() => void onAddDocument()}
            >
              Lưu hồ sơ giấy
            </button>
          </div>
          <ul className="emp-viol-list emp-panel-list">
            {documents.length === 0 && <li className="module-placeholder">Chưa có hồ sơ giấy.</li>}
            {documents.map((d) => (
              <li key={d.id}>
                <div>
                  <strong>{d.title}</strong>
                  <span className="field-hint">{DOC_TYPE_LABELS[d.doc_type] || d.doc_type}</span>
                </div>
                <div className="emp-viol-actions">
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() =>
                      void fetchDocumentFileObjectUrl(employeeId, d.id).then((url) =>
                        window.open(url, "_blank"),
                      )
                    }
                  >
                    Xem
                  </button>
                  <button
                    type="button"
                    className="link-btn danger"
                    disabled={saving}
                    onClick={() =>
                      void deleteEmployeeDocument(employeeId, d.id).then(() =>
                        fetchEmployeeDocuments(employeeId).then(setDocuments),
                      )
                    }
                  >
                    Xóa
                  </button>
                </div>
              </li>
            ))}
          </ul>
            </section>
          </div>
        ) : (
          <div className="emp-sheet-fields-fixed">
            <EmployeeProfileCompactFields
              form={form}
              setForm={setFormUndoable}
              departments={departments}
              teams={teams}
              allowancePanel={{
                allowances,
                allowTypes,
                newAllowCode,
                setNewAllowCode,
                newAllowAmount,
                setNewAllowAmount,
                saving,
                onAdd: () => void onAddAllow(),
                onDelete: (id) => void onDeleteAllow(id),
                formatMoney,
              }}
            />
          </div>
        )}
          </form>
        )}
      </div>
    </FullScreenSheet>
  );
}
