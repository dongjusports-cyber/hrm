import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  applySalaryRaise,
  fetchAllowanceTypes,
  fetchDepartments,
  fetchEmployees,
  previewSalaryRaise,
  printSalaryRaiseAppendix,
  type AllowanceType,
  type BulkSalaryRaisePreview,
  type Department,
  type Employee,
} from "../../shared/api";
import { labelEmpStatus } from "../../shared/viLabels";
import { textMatchesQuery } from "../../shared/employeeSearch";
import { ToolbarSearchInput } from "../../shared/ToolbarSearchInput";
import {
  formatDepartmentLabel,
  formatOrgName,
  isOrgUnitActive,
} from "../../shared/formatOrg";

type Target = "contract_salary" | "probation_salary" | "allowance";
type Scope = "all" | "department" | "employees";

type SalaryRaiseLocationState = {
  employeeIds?: string[];
};

const RAISE_STATUSES = new Set(["active", "probation", "maternity"]);

function empRaiseStatus(e: Employee): string {
  return e.effective_status ?? e.status;
}

function fmtVnd(v: string | number | null | undefined): string {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n.toLocaleString("vi-VN") : "—";
}

function parseTargetKey(key: string): { target: Target; allowanceCode: string } {
  if (key.startsWith("allowance:")) {
    return { target: "allowance", allowanceCode: key.slice("allowance:".length) };
  }
  if (key === "probation_salary") {
    return { target: "probation_salary", allowanceCode: "" };
  }
  return { target: "contract_salary", allowanceCode: "" };
}

export function SalaryRaisePage() {
  const location = useLocation();
  const presetIds = useMemo(
    () => (location.state as SalaryRaiseLocationState | null)?.employeeIds ?? [],
    [location.state],
  );

  const [departments, setDepartments] = useState<Department[]>([]);
  const [allowTypes, setAllowTypes] = useState<AllowanceType[]>([]);
  const [scope, setScope] = useState<Scope>(presetIds.length ? "employees" : "department");
  const [dept, setDept] = useState("");
  const [deptEmployees, setDeptEmployees] = useState<Employee[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set(presetIds));
  const [target, setTarget] = useState<Target>("contract_salary");
  const [allowanceCode, setAllowanceCode] = useState("");
  const [amount, setAmount] = useState("300000");
  const [effectiveFrom, setEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));
  const [preview, setPreview] = useState<BulkSalaryRaisePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const deptRow = departments.find((d) => d.code === dept);

  useEffect(() => {
    void fetchDepartments()
      .then((list) => {
        setDepartments(list);
        setDept((prev) => prev || list[0]?.code || "");
      })
      .catch(() => setDepartments([]));
    void fetchAllowanceTypes({ assignable: true })
      .then((list) => {
        setAllowTypes(list);
        setAllowanceCode((prev) => prev || list[0]?.code || "");
      })
      .catch(() => setAllowTypes([]));
  }, []);

  useEffect(() => {
    if (presetIds.length === 0) return;
    void fetchEmployees({ status: "all" })
      .then((rows) => {
        const picked = rows.filter(
          (e) => presetIds.includes(e.id) && RAISE_STATUSES.has(empRaiseStatus(e)),
        );
        if (picked[0]?.department_code) {
          setDept(picked[0].department_code);
        }
        setSelectedIds(new Set(picked.map((e) => e.id)));
        setScope("employees");
      })
      .catch(() => undefined);
  }, [presetIds]);

  useEffect(() => {
    if (scope !== "employees") {
      setDeptEmployees([]);
      return;
    }
    setLoadingEmployees(true);
    void fetchEmployees({ status: "all" })
      .then((rows) => {
        const eligible = rows.filter((e) => RAISE_STATUSES.has(empRaiseStatus(e)));
        setDeptEmployees(eligible);
        const allowed = new Set(eligible.map((e) => e.id));
        setSelectedIds((prev) => {
          const next = new Set<string>();
          for (const id of prev) {
            if (allowed.has(id)) next.add(id);
          }
          return next;
        });
      })
      .catch(() => setDeptEmployees([]))
      .finally(() => setLoadingEmployees(false));
  }, [scope]);

  const filteredEmployees = useMemo(() => {
    const q = employeeSearch.trim();
    let rows = deptEmployees;
    if (!q && dept) {
      rows = rows.filter((e) => e.department_code === dept);
    }
    return rows.filter((e) =>
      textMatchesQuery(
        q,
        e.employee_code,
        e.full_name,
        e.team_code,
        e.team_name,
        e.department_code,
        e.department_name,
      ),
    );
  }, [deptEmployees, employeeSearch, dept]);

  const selectedCount = selectedIds.size;
  const selectedEmployees = useMemo(() => {
    const byId = new Map(deptEmployees.map((e) => [e.id, e]));
    return Array.from(selectedIds)
      .map((id) => byId.get(id))
      .filter((e): e is Employee => Boolean(e))
      .sort((a, b) => a.employee_code.localeCompare(b.employee_code, "vi"));
  }, [deptEmployees, selectedIds]);

  function bodyBase() {
    return {
      scope,
      department_code: scope === "department" ? dept : undefined,
      employee_ids:
        scope === "employees" ? Array.from(selectedIds) : undefined,
      target,
      allowance_code: target === "allowance" ? allowanceCode : undefined,
      amount: amount.trim(),
      effective_from: effectiveFrom || undefined,
    };
  }

  function toggleEmployee(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setPreview(null);
  }

  function selectAllVisible() {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      for (const e of filteredEmployees) next.add(e.id);
      return next;
    });
    setPreview(null);
  }

  function unselectVisible() {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      for (const e of filteredEmployees) next.delete(e.id);
      return next;
    });
    setPreview(null);
  }

  function clearSelection() {
    setSelectedIds(new Set());
    setPreview(null);
  }

  async function onPreview(e: FormEvent) {
    e.preventDefault();
    if (scope === "employees" && selectedCount === 0) {
      setError("Trợ Lý AI: chọn ít nhất một công nhân trong danh sách.");
      return;
    }
    if (target === "allowance" && !allowanceCode) {
      setError("Trợ Lý AI: chọn loại phụ cấp cần tăng.");
      return;
    }
    setBusy(true);
    setError(null);
    setOk(null);
    setPreview(null);
    try {
      setPreview(await previewSalaryRaise(bodyBase()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xem trước được.");
    } finally {
      setBusy(false);
    }
  }

  async function onPrint() {
    if (!preview) {
      setError("Trợ Lý AI: bấm «Xem trước» trước khi in phụ lục.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await printSalaryRaiseAppendix(bodyBase());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không in được phụ lục.");
    } finally {
      setBusy(false);
    }
  }

  async function onApply() {
    if (!preview) {
      setError("Trợ Lý AI: bấm «Xem trước» trước khi lưu.");
      return;
    }
    const scopeText =
      scope === "all"
        ? "TOÀN BỘ công ty"
        : scope === "employees"
          ? `${selectedCount} NV được chọn`
          : `bộ phận ${preview.department_code ?? dept}`;
    const amountText = Number(preview.amount).toLocaleString("vi-VN");

    if (
      !window.confirm(
        `Xác nhận lần 1/2:\n\nTăng ${preview.target_label} thêm ${amountText} VND cho ${preview.affected_count} NV (${scopeText})?\n\nBấm OK để tiếp tục.`,
      )
    ) {
      return;
    }
    if (
      !window.confirm(
        `Xác nhận lần 2/2 — không hoàn tác tự động:\n\nThật sự tăng ${preview.target_label} +${amountText} VND cho ${preview.affected_count} NV?\n\nBấm OK để LƯU.`,
      )
    ) {
      return;
    }

    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const result = await applySalaryRaise({
        ...bodyBase(),
        confirm: true,
        confirm_again: true,
      });
      setOk(result.message);
      setPreview(null);
      setSelectedIds(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tăng lương được.");
    } finally {
      setBusy(false);
    }
  }

  const showDeptPicker = scope === "department" || scope === "employees";

  return (
    <div className="hr-raise-page">
      <div className="emp-detail-head">
        <h1>Tăng lương</h1>
        <div className="emp-detail-head-actions">
          <Link to="/m/hr" className="btn-ghost-dark">
            ← Danh sách
          </Link>
        </div>
      </div>

      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      <form className="users-form-card hr-raise-card" onSubmit={(e) => void onPreview(e)}>
        <div className="hr-raise-grid">
          <label className="field">
            <span>Phạm vi</span>
            <select
              value={scope}
              onChange={(e) => {
                setScope(e.target.value as Scope);
                setPreview(null);
              }}
            >
              <option value="department">Cả bộ phận</option>
              <option value="employees">Chọn từng người (gõ MSNV)</option>
              <option value="all">Toàn bộ công ty</option>
            </select>
          </label>
          {showDeptPicker && (
            <label className="field">
              <span>Bộ phận</span>
              <select
                value={dept}
                onChange={(e) => {
                  setDept(e.target.value);
                  if (scope === "department") setSelectedIds(new Set());
                  setPreview(null);
                }}
                required={scope === "department"}
              >
                {scope === "employees" && <option value="">Tất cả bộ phận</option>}
                {departments.filter(isOrgUnitActive).map((d) => (
                  <option key={d.id} value={d.code}>
                    {formatDepartmentLabel(d)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="field">
            <span>Thành phần tăng</span>
            <select
              value={
                target === "allowance" && allowanceCode
                  ? `allowance:${allowanceCode}`
                  : target
              }
              onChange={(e) => {
                const parsed = parseTargetKey(e.target.value);
                setTarget(parsed.target);
                if (parsed.allowanceCode) setAllowanceCode(parsed.allowanceCode);
                setPreview(null);
              }}
            >
              <optgroup label="Lương">
                <option value="contract_salary">Lương HĐ</option>
                <option value="probation_salary">Lương thử việc</option>
              </optgroup>
              <optgroup label="Phụ cấp">
                {allowTypes.length === 0 ? (
                  <option value="allowance" disabled>
                    (Chưa tải được danh mục phụ cấp)
                  </option>
                ) : (
                  allowTypes.map((a) => (
                    <option key={a.code} value={`allowance:${a.code}`}>
                      {a.name}
                    </option>
                  ))
                )}
              </optgroup>
            </select>
          </label>
          <label className="field">
            <span>Số tiền tăng (đồng)</span>
            <input
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value);
                setPreview(null);
              }}
              placeholder="vd 300000 hoặc 300.000"
              required
            />
          </label>
          <label className="field">
            <span>Ngày hiệu lực phụ lục</span>
            <input
              type="date"
              value={effectiveFrom}
              onChange={(e) => {
                setEffectiveFrom(e.target.value);
                setPreview(null);
              }}
              required
            />
          </label>
        </div>

        {scope === "employees" && (
          <div className="hr-raise-picker">
            <div className="hr-raise-picker-head">
              <h2>
                Tìm công nhân
                {employeeSearch.trim()
                  ? " · toàn công ty"
                  : deptRow
                    ? ` — ${formatDepartmentLabel(deptRow)}`
                    : " — tất cả"}
              </h2>
              <ToolbarSearchInput
                className="hr-search"
                placeholder="Gõ MSNV hoặc họ tên…"
                onQuery={setEmployeeSearch}
                style={{ minWidth: 200, flex: "1 1 180px", maxWidth: 280 }}
              />
              <button type="button" className="btn-ghost-dark" onClick={selectAllVisible}>
                Chọn tất cả đang hiện
              </button>
            </div>
            {selectedCount > 0 && (
              <div className="hr-raise-selected" aria-label="Danh sách đã tích">
                <div className="hr-raise-selected-head">
                  <strong>Đã chọn {selectedCount} người</strong>
                  <span className="field-hint">Luôn hiện đủ, không mất khi đổi bộ phận / ô tìm</span>
                  <button type="button" className="btn-ghost-dark" onClick={clearSelection}>
                    Bỏ hết
                  </button>
                </div>
                <ul className="hr-raise-selected-list">
                  {selectedEmployees.map((emp) => (
                    <li key={emp.id}>
                      <button
                        type="button"
                        className="hr-raise-chip"
                        title="Bỏ tích người này"
                        onClick={() => toggleEmployee(emp.id)}
                      >
                        <strong>{emp.employee_code}</strong>
                        <span>{emp.full_name}</span>
                        <small>
                          {formatOrgName(emp.department_name) || emp.department_code || "—"}
                        </small>
                        <span className="hr-raise-chip-x" aria-hidden>
                          ×
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {loadingEmployees && <p className="field-hint">Đang tải danh sách…</p>}
            {!loadingEmployees && deptEmployees.length === 0 && (
              <p className="field-hint">Không có NV đang làm / thử việc / thai sản.</p>
            )}
            {!loadingEmployees && deptEmployees.length > 0 && filteredEmployees.length === 0 && (
              <p className="field-hint">
                {employeeSearch.trim()
                  ? `Không thấy «${employeeSearch.trim()}». Kiểm tra MSNV hoặc NV đã thôi việc.`
                  : "Không có NV trong bộ phận đang lọc — gõ MSNV để tìm toàn công ty, hoặc chọn «Tất cả bộ phận»."}
              </p>
            )}
            {!loadingEmployees && filteredEmployees.length > 0 && (
              <div className="hr-raise-picker-table-wrap">
                <table className="hr-raise-picker-table">
                  <thead>
                    <tr>
                      <th style={{ width: 40 }}>
                        <input
                          type="checkbox"
                          aria-label="Chọn tất cả đang hiện"
                          checked={
                            filteredEmployees.length > 0 &&
                            filteredEmployees.every((e) => selectedIds.has(e.id))
                          }
                          onChange={(e) => {
                            if (e.target.checked) selectAllVisible();
                            else unselectVisible();
                          }}
                        />
                      </th>
                      <th>MSNV</th>
                      <th>Họ tên</th>
                      <th>Bộ phận</th>
                      <th>Tổ</th>
                      <th className="num">Lương HĐ</th>
                      <th>Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEmployees.map((emp) => {
                      const checked = selectedIds.has(emp.id);
                      return (
                        <tr
                          key={emp.id}
                          className={checked ? "is-selected" : undefined}
                          onClick={() => toggleEmployee(emp.id)}
                          style={{ cursor: "pointer" }}
                        >
                          <td onClick={(ev) => ev.stopPropagation()}>
                            <label>
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleEmployee(emp.id)}
                              />
                            </label>
                          </td>
                          <td>{emp.employee_code}</td>
                          <td>{emp.full_name}</td>
                          <td>{formatOrgName(emp.department_name) || emp.department_code || "—"}</td>
                          <td>{formatOrgName(emp.team_name) || emp.team_code || "—"}</td>
                          <td className="num">{fmtVnd(emp.contract_salary)}</td>
                          <td>{labelEmpStatus(empRaiseStatus(emp))}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <p className="field-hint" style={{ marginTop: 8 }}>
              Gõ MSNV → tick. Người đã tick nằm ở khung «Đã chọn» phía trên (không mất khi đổi bộ
              phận hay xóa ô tìm). Bấm chip để bỏ tích.
            </p>
          </div>
        )}

        {preview && <p className="hr-raise-preview">{preview.message}</p>}

        <div className="hr-raise-actions">
          <button type="submit" className="btn-ghost-dark" disabled={busy}>
            Xem trước
          </button>
          <button
            type="button"
            className="btn-ghost-dark"
            disabled={busy || !preview}
            onClick={() => void onPrint()}
          >
            In phụ lục
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={busy || !preview}
            onClick={() => void onApply()}
          >
            Lưu tăng lương
          </button>
        </div>
        <p className="field-hint">
          «Cả bộ phận» = mọi NV đang làm trong bộ phận · «Chọn từng người» = gõ MSNV (toàn công ty)
          rồi tick. Thành phần tăng gồm Lương HĐ và từng loại phụ cấp. In phụ lục — mỗi NV một trang.
        </p>
      </form>
    </div>
  );
}
