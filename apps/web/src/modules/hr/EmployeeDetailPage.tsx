import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  createEmployee,
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
  fetchViolationAttachmentObjectUrl,
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
import { formatDeptTeam } from "../../shared/formatOrg";
import {
  emptyEmployeeForm,
  employeeToForm,
  formToPayload,
  parseEmpTab,
  PROFILE_TABS,
  type EmpTab,
  type ProfileTab,
} from "./employeeFormState";
import { EmployeeCreateFields, EmployeeProfileAllFields, EmployeeProfileTabFields } from "./EmployeeProfileFields";
import { EmployeeExperiencePanel } from "./EmployeeExperiencePanel";
import { labelEmpStatus } from "../../shared/viLabels";
import {
  printEmployeeContract,
  printEmployeeDecision,
  printEmployeeProbation,
} from "../../shared/api";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";
import { type HrNavState } from "../../shared/hrNavState";

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

const emptyForm = emptyEmployeeForm;

/** Hồ sơ NV Lv4 — bố cục dày kiểu HRM vận hành (MISA-like). */
export function EmployeeDetailPage() {
  const { empId } = useParams();
  const isNew = empId === "new";
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const listBack =
    (location.state as HrNavState | null)?.hrListBack ??
    (isNew ? "/m/hr" : "/m/hr/lists/active");
  useHrSubpageEsc({ backTo: listBack });
  const tab: EmpTab = parseEmpTab(searchParams.get("tab"), isNew);
  const profileTab: ProfileTab =
    tab === "violations" || tab === "documents" || tab === "experience"
      ? "work"
      : (tab as ProfileTab);
  const fileRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState(emptyForm);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [allowTypes, setAllowTypes] = useState<AllowanceType[]>([]);
  const [allowances, setAllowances] = useState<AllowanceAssignment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [emp, setEmp] = useState<Employee | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [pendingPhoto, setPendingPhoto] = useState<File | null>(null);
  const [newAllowCode, setNewAllowCode] = useState("");
  const [newAllowAmount, setNewAllowAmount] = useState("0");
  const [violations, setViolations] = useState<EmployeeViolation[]>([]);
  const [documents, setDocuments] = useState<EmployeeDocument[]>([]);
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

  function setTab(next: EmpTab) {
    if (next === "all") {
      setSearchParams({}, { replace: true });
    } else {
      setSearchParams({ tab: next }, { replace: true });
    }
  }

  useEffect(() => {
    void fetchDepartments()
      .then(setDepartments)
      .catch(() => setDepartments([]));
    void fetchTeams()
      .then(setTeams)
      .catch(() => setTeams([]));
    void fetchAllowanceTypes()
      .then((list) => {
        setAllowTypes(list);
        setNewAllowCode((prev) => prev || list[0]?.code || "");
      })
      .catch(() => setAllowTypes([]));
  }, []);

  useEffect(() => {
    if (isNew || !empId) {
      setLoading(false);
      setForm(emptyForm);
      setAllowances([]);
      setViolations([]);
      setDocuments([]);
      setEmp(null);
      setPendingPhoto(null);
      setPhotoUrl((prev) => {
        if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
        return null;
      });
      return;
    }
    let cancelled = false;
    setLoading(true);
    void (async () => {
      try {
        const e = await fetchEmployee(empId);
        if (cancelled) return;
        setEmp(e);
        setForm(employeeToForm(e, toDateInput));
        setAllowances(await fetchAllowanceAssignments(e.employee_code));
        setViolations(await fetchEmployeeViolations(e.id));
        setDocuments(await fetchEmployeeDocuments(e.id));
        setError(null);
        if (e.has_photo) {
          const url = await fetchEmployeePhotoObjectUrl(e.id);
          if (!cancelled) {
            setPhotoUrl((prev) => {
              if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
              return url;
            });
          } else if (url) {
            URL.revokeObjectURL(url);
          }
        } else {
          setPhotoUrl((prev) => {
            if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
            return null;
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Không tải hồ sơ.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [empId, isNew]);

  useEffect(() => {
    return () => {
      if (photoUrl?.startsWith("blob:")) URL.revokeObjectURL(photoUrl);
    };
  }, [photoUrl]);

  function openPhotoPicker() {
    fileRef.current?.click();
  }

  async function onPhotoPicked(file: File | null) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Trợ Lý AI: vui lòng chọn file ảnh (JPG/PNG/WEBP).");
      return;
    }
    setError(null);
    setOk(null);
    const localUrl = URL.createObjectURL(file);
    setPhotoUrl((prev) => {
      if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
      return localUrl;
    });

    if (isNew || !empId) {
      setPendingPhoto(file);
      setOk("Đã chọn ảnh — sẽ lưu kèm khi tạo nhân viên.");
      return;
    }

    try {
      setSaving(true);
      const updated = await uploadEmployeePhoto(empId, file);
      setEmp(updated);
      setPendingPhoto(null);
      setOk("Đã cập nhật ảnh hồ sơ.");
      const url = await fetchEmployeePhotoObjectUrl(updated.id);
      setPhotoUrl((prev) => {
        if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
        return url;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải ảnh lên được.");
    } finally {
      setSaving(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    setSaving(true);
    const payload = formToPayload(form, isNew);
    try {
      if (isNew) {
        const created = await createEmployee({
          employee_code: form.employee_code,
          ...payload,
        });
        if (pendingPhoto) {
          await uploadEmployeePhoto(created.id, pendingPhoto);
          setPendingPhoto(null);
        }
        setOk("Đã tạo nhân viên.");
        navigate(`/m/hr/employees/${created.id}`, { replace: true, state: location.state });
      } else if (empId) {
        const updated = await updateEmployee(empId, payload);
        setEmp(updated);
        setOk("Đã lưu hồ sơ.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại.");
    } finally {
      setSaving(false);
    }
  }

  async function reloadAllowances(code: string) {
    setAllowances(await fetchAllowanceAssignments(code));
  }

  async function onAddAllow() {
    if (!form.employee_code || isNew) return;
    setSaving(true);
    setError(null);
    setOk(null);
    try {
      await upsertAllowanceAssignment({
        employee_code: form.employee_code,
        allowance_code: newAllowCode,
        amount: newAllowAmount.trim() || "0",
      });
      await reloadAllowances(form.employee_code);
      setOk(`Đã gán phụ cấp ${newAllowCode}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gán phụ cấp được.");
    } finally {
      setSaving(false);
    }
  }

  async function onDeleteAllow(id: string) {
    if (!window.confirm("Xóa phụ cấp này khỏi hồ sơ?")) return;
    setSaving(true);
    setError(null);
    setOk(null);
    try {
      await deleteAllowanceAssignment(id);
      if (form.employee_code) await reloadAllowances(form.employee_code);
      setOk("Đã xóa phụ cấp.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa phụ cấp được.");
    } finally {
      setSaving(false);
    }
  }

  async function reloadViolations(id: string) {
    setViolations(await fetchEmployeeViolations(id));
  }

  async function reloadDocuments(id: string) {
    setDocuments(await fetchEmployeeDocuments(id));
  }

  async function onAddViolation() {
    if (!empId || isNew) return;
    if (!vTitle.trim()) {
      setError("Trợ Lý AI: cần tiêu đề / loại vi phạm.");
      return;
    }
    setSaving(true);
    setError(null);
    setOk(null);
    try {
      await createEmployeeViolation(empId, {
        occurred_at: new Date(vWhen).toISOString(),
        title: vTitle.trim(),
        description: vDesc.trim(),
        penalty: vPenalty.trim(),
        file: vFile,
      });
      await reloadViolations(empId);
      setVTitle("");
      setVPenalty("");
      setVDesc("");
      setVFile(null);
      setOk("Đã ghi biên bản vi phạm.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không ghi vi phạm được.");
    } finally {
      setSaving(false);
    }
  }

  async function onDeleteViolation(id: string) {
    if (!empId || !window.confirm("Xóa biên bản vi phạm này?")) return;
    setSaving(true);
    setError(null);
    try {
      await deleteEmployeeViolation(empId, id);
      await reloadViolations(empId);
      setOk("Đã xóa biên bản.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    } finally {
      setSaving(false);
    }
  }

  async function onViewOrPrintViolation(v: EmployeeViolation, print: boolean) {
    if (!empId) return;
    try {
      if (v.has_attachment) {
        const url = await fetchViolationAttachmentObjectUrl(empId, v.id);
        const w = window.open(url, "_blank");
        if (print && w) {
          w.addEventListener("load", () => {
            try {
              w.print();
            } catch {
              /* trình duyệt có thể chặn */
            }
          });
        }
        return;
      }
      const w = window.open("", "_blank");
      if (!w) return;
      w.document.write(`<!doctype html><html lang="vi"><head><meta charset="utf-8"/><title>${v.title}</title>
        <style>body{font-family:sans-serif;padding:24px;line-height:1.5} h1{font-size:1.2rem}</style></head><body>
        <h1>Biên bản / vi phạm</h1>
        <p><strong>NV:</strong> ${form.employee_code} — ${form.full_name}</p>
        <p><strong>Thời gian:</strong> ${formatDateTimeDDMMYYYY(v.occurred_at)}</p>
        <p><strong>Loại:</strong> ${v.title}</p>
        <p><strong>Hình thức / phạt:</strong> ${v.penalty || "—"}</p>
        <p><strong>Chi tiết:</strong><br/>${(v.description || "—").replace(/\n/g, "<br/>")}</p>
        </body></html>`);
      w.document.close();
      if (print) w.print();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không mở biên bản được.");
    }
  }

  async function onAddDocument() {
    if (!empId || isNew) return;
    if (!dFile) {
      setError("Trợ Lý AI: cần ảnh hoặc PDF hồ sơ giấy.");
      return;
    }
    const t = dTitle.trim() || DOC_TYPE_LABELS[dType] || "Hồ sơ giấy";
    setSaving(true);
    setError(null);
    setOk(null);
    try {
      await createEmployeeDocument(empId, {
        title: t,
        doc_type: dType,
        note: dNote.trim(),
        file: dFile,
      });
      await reloadDocuments(empId);
      setDTitle("");
      setDNote("");
      setDFile(null);
      setOk("Đã lưu hồ sơ giấy.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu hồ sơ được.");
    } finally {
      setSaving(false);
    }
  }

  async function onDeleteDocument(id: string) {
    if (!empId || !window.confirm("Xóa hồ sơ giấy này?")) return;
    setSaving(true);
    setError(null);
    try {
      await deleteEmployeeDocument(empId, id);
      await reloadDocuments(empId);
      setOk("Đã xóa hồ sơ giấy.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    } finally {
      setSaving(false);
    }
  }

  async function onViewDocument(doc: EmployeeDocument) {
    if (!empId) return;
    try {
      const url = await fetchDocumentFileObjectUrl(empId, doc.id);
      window.open(url, "_blank");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không mở file được.");
    }
  }

  async function changeStatus(next: string) {
    if (isNew || !empId) return;
    if (form.status === next) {
      setOk(`Đang ở trạng thái ${labelEmpStatus(next)}.`);
      return;
    }
    const label = labelEmpStatus(next);
    if (!window.confirm(`Chuyển ${form.full_name || form.employee_code} sang «${label}»?`)) {
      return;
    }

    let resignDate = form.resign_date;
    if (next === "resigned" && !resignDate) {
      const today = new Date();
      resignDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    }
    if (next !== "resigned") {
      resignDate = "";
    }

    setSaving(true);
    setError(null);
    setOk(null);
    try {
      const updated = await updateEmployee(empId, {
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đổi trạng thái được.");
    } finally {
      setSaving(false);
    }
  }

  const title = isNew
    ? "NV mới"
    : form.employee_code
      ? `MSNV ${form.employee_code}`
      : "Hồ sơ";

  if (isNew) {
    return (
      <div className="emp-detail-page emp-create-page">
        <nav className="breadcrumb emp-detail-crumb">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <Link to="/m/hr">Nhân Sự</Link>
          <span aria-hidden> › </span>
          <span>{title}</span>
        </nav>

        <div className="emp-detail-head">
          <h1>Tạo nhân viên</h1>
          <div className="emp-detail-head-actions">
            <Link to={listBack} className="btn-ghost-dark">
              ← Quay lại
            </Link>
            <button
              type="submit"
              form="emp-profile-form"
              className="btn-primary"
              disabled={saving}
            >
              {saving ? "Đang lưu…" : "Tạo nhân viên"}
            </button>
          </div>
        </div>

        {error && <p className="banner-warn">{error}</p>}
        {ok && <p className="banner-ok">{ok}</p>}

        <form
          id="emp-profile-form"
          className="users-form-card emp-create-card"
          onSubmit={(ev) => void onSubmit(ev)}
        >
          <EmployeeCreateFields
            form={form}
            setForm={setForm}
            tab="work"
            isNew
            departments={departments}
            teams={teams}
          />
        </form>
      </div>
    );
  }

  return (
    <div className="emp-detail-page">
      <nav className="breadcrumb emp-detail-crumb">
        <Link to="/">Portal</Link>
        <span aria-hidden> › </span>
        <Link to="/m/hr">Nhân Sự</Link>
        {!isNew && listBack !== "/m/hr" && (
          <>
            <span aria-hidden> › </span>
            <Link to={listBack}>Danh sách</Link>
          </>
        )}
        <span aria-hidden> › </span>
        <span>{title}</span>
      </nav>

      <div className="emp-detail-head">
        <h1>{isNew ? "Tạo nhân viên" : form.full_name || "Hồ sơ nhân viên"}</h1>
        <div className="emp-detail-head-actions">
          <Link to={listBack} className="btn-ghost-dark">
            ← {listBack === "/m/hr" ? "Nhân Sự" : "Danh sách"}
          </Link>
          {tab !== "violations" && tab !== "documents" && tab !== "experience" && (
            <button
              type="submit"
              form="emp-profile-form"
              className="btn-primary"
              disabled={loading || saving}
            >
              {isNew ? "Tạo nhân viên" : "Lưu hồ sơ"}
            </button>
          )}
          {!isNew && empId && (
            <>
              <Link
                to={`/m/hr/contracts?employee_id=${empId}`}
                className="btn-ghost-dark"
              >
                Hợp đồng
              </Link>
              <button
                type="button"
                className="btn-ghost-dark"
                disabled={saving}
                onClick={() => void printEmployeeContract(empId).catch((e) => setError(String(e)))}
              >
                In HĐ
              </button>
              {form.status === "probation" && (
                <button
                  type="button"
                  className="btn-ghost-dark"
                  disabled={saving}
                  onClick={() => void printEmployeeProbation(empId).catch((e) => setError(String(e)))}
                >
                  In thử việc
                </button>
              )}
              <button
                type="button"
                className="btn-ghost-dark"
                disabled={saving}
                onClick={() => void printEmployeeDecision(empId).catch((e) => setError(String(e)))}
              >
                In QĐ
              </button>
            </>
          )}
        </div>
      </div>

      {!isNew && (
        <div className="emp-subtabs" role="tablist" aria-label="Phần hồ sơ">
          {PROFILE_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              className={tab === t.id ? "emp-subtab active" : "emp-subtab"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
          <button
            type="button"
            role="tab"
            aria-selected={tab === "violations"}
            className={tab === "violations" ? "emp-subtab active" : "emp-subtab"}
            onClick={() => setTab("violations")}
          >
            Vi phạm{violations.length ? ` (${violations.length})` : ""}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "documents"}
            className={tab === "documents" ? "emp-subtab active" : "emp-subtab"}
            onClick={() => setTab("documents")}
          >
            Hồ sơ giấy{documents.length ? ` (${documents.length})` : ""}
          </button>
        </div>
      )}

      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}
      {loading ? (
        <p className="field-hint">Đang tải hồ sơ…</p>
      ) : tab === "experience" && !isNew && empId ? (
        <section className="emp-panel emp-panel-lg users-form-card" aria-label="Kinh nghiệm">
          <h2>Kinh nghiệm / đào tạo / khám SK</h2>
          <EmployeeExperiencePanel empId={empId} />
        </section>
      ) : tab === "violations" && !isNew ? (
        <section className="emp-panel emp-panel-lg users-form-card" aria-label="Vi phạm">
          <h2>Vi phạm / biên bản</h2>
          <p className="field-hint emp-panel-hint">
            Nhập liệu chữ lớn — không cần kéo tìm trong hồ sơ thông tin.
          </p>
          <div className="emp-viol-form emp-panel-form">
            <label className="field">
              <span>Thời gian vi phạm</span>
              <input
                type="datetime-local"
                value={vWhen}
                onChange={(e) => setVWhen(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Loại / tiêu đề</span>
              <input
                value={vTitle}
                onChange={(e) => setVTitle(e.target.value)}
                placeholder="VD: Đi trễ nhiều lần"
              />
            </label>
            <label className="field">
              <span>Hình thức / phạt</span>
              <input
                value={vPenalty}
                onChange={(e) => setVPenalty(e.target.value)}
                placeholder="VD: Phạt 200.000đ / khiển cáo"
              />
            </label>
            <label className="field emp-field-wide">
              <span>Chi tiết</span>
              <input
                value={vDesc}
                onChange={(e) => setVDesc(e.target.value)}
                placeholder="Mô tả ngắn"
              />
            </label>
            <label className="field emp-field-wide">
              <span>Scan biên bản (PDF/ảnh ≤ 10MB)</span>
              <input
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                capture="environment"
                onChange={(e) => setVFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <button
              type="button"
              className="btn-primary"
              disabled={saving}
              onClick={() => void onAddViolation()}
            >
              Ghi biên bản
            </button>
          </div>

          <ul className="emp-viol-list emp-panel-list">
            {violations.length === 0 && (
              <li className="module-placeholder">Chưa có biên bản vi phạm.</li>
            )}
            {violations.map((v) => (
              <li key={v.id}>
                <div>
                  <strong>{v.title}</strong>
                  <span className="field-hint">
                    {formatDateTimeDDMMYYYY(v.occurred_at)}
                    {v.penalty ? ` · ${v.penalty}` : ""}
                    {v.has_attachment ? " · có file scan" : ""}
                  </span>
                  {v.description && <p>{v.description}</p>}
                </div>
                <div className="emp-viol-actions">
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => void onViewOrPrintViolation(v, false)}
                  >
                    Xem
                  </button>
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => void onViewOrPrintViolation(v, true)}
                  >
                    In
                  </button>
                  <button
                    type="button"
                    className="link-btn danger"
                    disabled={saving}
                    onClick={() => void onDeleteViolation(v.id)}
                  >
                    Xóa
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : tab === "documents" && !isNew ? (
        <section className="emp-panel emp-panel-lg users-form-card" aria-label="Hồ sơ giấy">
          <h2>Hồ sơ giấy đã lưu</h2>
          <p className="field-hint emp-panel-hint">
            Chụp từ điện thoại hoặc chọn file — hoặc dùng ô «Lưu hồ sơ» trên Nhân Sự.
          </p>
          <div className="emp-viol-form emp-panel-form">
            <label className="field">
              <span>Loại hồ sơ</span>
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
              <input
                value={dTitle}
                onChange={(e) => setDTitle(e.target.value)}
                placeholder="VD: HĐLĐ lần 1"
              />
            </label>
            <label className="field">
              <span>Ghi chú</span>
              <input value={dNote} onChange={(e) => setDNote(e.target.value)} />
            </label>
            <label className="field emp-field-wide">
              <span>Chụp / chọn file (PDF, ảnh ≤ 10MB)</span>
              <input
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                capture="environment"
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
            {documents.length === 0 && (
              <li className="module-placeholder">Chưa có hồ sơ giấy.</li>
            )}
            {documents.map((d) => (
              <li key={d.id}>
                <div>
                  <strong>{d.title}</strong>
                  <span className="field-hint">
                    {DOC_TYPE_LABELS[d.doc_type] || d.doc_type}
                    {d.created_at
                      ? ` · ${formatDateTimeDDMMYYYY(d.created_at)}`
                      : ""}
                  </span>
                  {d.note && <p>{d.note}</p>}
                </div>
                <div className="emp-viol-actions">
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => void onViewDocument(d)}
                  >
                    Xem
                  </button>
                  <button
                    type="button"
                    className="link-btn danger"
                    disabled={saving}
                    onClick={() => void onDeleteDocument(d.id)}
                  >
                    Xóa
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <div className="emp-detail-layout emp-detail-layout-profile">
          {!isNew && (
            <section className="users-form-card emp-status-bar">
              <div className="emp-status-bar-head">
                <strong>Chuyển trạng thái</strong>
                <span className="field-hint">
                  Hiện tại: <strong>{labelEmpStatus(form.status)}</strong>
                </span>
              </div>
              <div className="emp-status-actions">
                {STATUS_ACTIONS.map((a) => (
                  <button
                    key={a.status}
                    type="button"
                    className={
                      form.status === a.status ? "btn-primary" : "btn-ghost-dark"
                    }
                    disabled={saving || form.status === a.status}
                    onClick={() => void changeStatus(a.status)}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </section>
          )}

          <form
            id="emp-profile-form"
            className="users-form-card emp-profile-card"
            onSubmit={(ev) => void onSubmit(ev)}
          >
            {!isNew && (
              <div className="emp-profile-identity">
                <button
                  type="button"
                  className="emp-photo"
                  onClick={openPhotoPicker}
                  disabled={saving}
                  title="Bấm để chọn ảnh từ máy / điện thoại"
                >
                  {photoUrl ? (
                    <img src={photoUrl} alt={form.full_name || "Ảnh NV"} />
                  ) : (
                    <span className="emp-photo-empty">
                      <strong>Ảnh NV</strong>
                      <small>Bấm để tải</small>
                    </span>
                  )}
                </button>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/*"
                  capture="environment"
                  hidden
                  onChange={(e) => void onPhotoPicked(e.target.files?.[0] ?? null)}
                />
                <div className="emp-identity-fields">
                  <label className="field">
                    <span>MSNV</span>
                    <input value={form.employee_code} readOnly className="emp-readonly" />
                  </label>
                  <label className="field emp-identity-name">
                    <span>Họ tên</span>
                    <input
                      value={form.full_name}
                      onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                      required
                    />
                  </label>
                  {emp && (
                    <p className="field-hint emp-identity-meta">
                      {formatDeptTeam(
                        emp.department_name,
                        emp.department_code,
                        emp.team_name,
                        emp.team_code,
                      )}
                      {form.position_title ? ` · ${form.position_title}` : ""}
                    </p>
                  )}
                </div>
              </div>
            )}

            <div className="emp-profile-body">
              {profileTab === "all" ? (
                <EmployeeProfileAllFields
                  form={form}
                  setForm={setForm}
                  departments={departments}
                  teams={teams}
                />
              ) : (
                <EmployeeProfileTabFields
                  form={form}
                  setForm={setForm}
                  tab={profileTab}
                  isNew={false}
                  departments={departments}
                  teams={teams}
                />
              )}
              {(profileTab === "salary" || profileTab === "all") && (
                    <section className="emp-allow-section" aria-label="Phụ cấp">
                      <h3 className="emp-allow-heading">Phụ cấp</h3>
                      <ul className="dept-list emp-allow-list">
                        {allowances.length === 0 && (
                          <li className="module-placeholder">Chưa có gán phụ cấp.</li>
                        )}
                        {allowances.map((a) => (
                          <li key={a.id}>
                            <span>
                              <strong>{a.allowance_name}</strong> {formatMoney(a.amount)}
                            </span>
                            <button
                              type="button"
                              className="link-btn danger"
                              disabled={saving}
                              onClick={() => void onDeleteAllow(a.id)}
                            >
                              Xóa
                            </button>
                          </li>
                        ))}
                      </ul>
                      <div className="emp-allow-add emp-fields-grid">
                        <label className="field">
                          <span>Loại phụ cấp</span>
                          <select
                            value={newAllowCode}
                            onChange={(e) => setNewAllowCode(e.target.value)}
                          >
                            {allowTypes.map((t) => (
                              <option key={t.code} value={t.code}>
                                {t.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="field">
                          <span>Số tiền</span>
                          <input
                            value={newAllowAmount}
                            onChange={(e) => setNewAllowAmount(e.target.value)}
                          />
                        </label>
                        <div className="field emp-allow-add-btn">
                          <span aria-hidden="true">&nbsp;</span>
                          <button
                            type="button"
                            className="btn-primary"
                            disabled={saving || !newAllowCode}
                            onClick={() => void onAddAllow()}
                          >
                            Thêm / cập nhật
                          </button>
                        </div>
                      </div>
                    </section>
              )}
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
