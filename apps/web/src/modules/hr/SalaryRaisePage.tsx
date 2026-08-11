import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
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
import {
  formatDepartmentLabel,
  isOrgUnitActive,
} from "../../shared/formatOrg";

type Target = "contract_salary" | "probation_salary" | "allowance";
type Scope = "all" | "department" | "employees";

type SalaryRaiseLocationState = {
  employeeIds?: string[];
};

const RAISE_STATUSES = new Set(["active", "probation"]);

function fmtVnd(v: string | number | null | undefined): string {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n.toLocaleString("vi-VN") : "—";
}

export function SalaryRaisePage() {
  const navigate = useNavigate();
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
    void fetchAllowanceTypes()
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
        const picked = rows.filter((e) => presetIds.includes(e.id) && RAISE_STATUSES.has(e.status));
        if (picked[0]?.department_code) {
          setDept(picked[0].department_code);
        }
        setSelectedIds(new Set(picked.map((e) => e.id)));
        setScope("employees");
      })
      .catch(() => undefined);
  }, [presetIds]);

  useEffect(() => {
    if (scope !== "employees" || !deptRow?.id) {
      setDeptEmployees([]);
      return;
    }
    setLoadingEmployees(true);
    void fetchEmployees({ department_id: deptRow.id, status: "all" })
      .then((rows) => {
        const eligible = rows.filter((e) => RAISE_STATUSES.has(e.status));
        setDeptEmployees(eligible);
        setSelectedIds((prev) => {
          const next = new Set<string>();
          for (const id of prev) {
            if (eligible.some((e) => e.id === id)) next.add(id);
          }
          return next;
        });
      })
      .catch(() => setDeptEmployees([]))
      .finally(() => setLoadingEmployees(false));
  }, [scope, deptRow?.id]);

  const filteredEmployees = useMemo(() => {
    const q = employeeSearch.trim().toLowerCase();
    if (!q) return deptEmployees;
    return deptEmployees.filter(
      (e) =>
        e.employee_code.toLowerCase().includes(q) ||
        e.full_name.toLowerCase().includes(q) ||
        (e.team_code ?? "").toLowerCase().includes(q),
    );
  }, [deptEmployees, employeeSearch]);

  const selectedCount = selectedIds.size;

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
      navigate("/m/hr");
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
              <option value="employees">Chọn một vài người trong bộ phận</option>
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
                  setSelectedIds(new Set());
                  setPreview(null);
                }}
                required
              >
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
              value={target}
              onChange={(e) => {
                setTarget(e.target.value as Target);
                setPreview(null);
              }}
            >
              <option value="contract_salary">Lương HĐ</option>
              <option value="probation_salary">Lương thử việc</option>
              <option value="allowance">Phụ cấp</option>
            </select>
          </label>
          {target === "allowance" && (
            <label className="field">
              <span>Loại phụ cấp</span>
              <select
                value={allowanceCode}
                onChange={(e) => {
                  setAllowanceCode(e.target.value);
                  setPreview(null);
                }}
                required
              >
                {allowTypes.map((a) => (
                  <option key={a.code} value={a.code}>
                    {a.name}
                  </option>
                ))}
              </select>
            </label>
          )}
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
                Danh sách công nhân
                {deptRow ? ` — ${deptRow.code}` : ""}
                {selectedCount > 0 ? ` · đã chọn ${selectedCount}` : ""}
              </h2>
              <input
                className="hr-search"
                value={employeeSearch}
                onChange={(e) => setEmployeeSearch(e.target.value)}
                placeholder="Tìm MSNV / họ tên / tổ"
                aria-label="Tìm trong bộ phận"
                style={{ minWidth: 200, flex: "1 1 180px", maxWidth: 280 }}
              />
              <button type="button" className="btn-ghost-dark" onClick={selectAllVisible}>
                Chọn tất cả
              </button>
              <button
                type="button"
                className="btn-ghost-dark"
                disabled={selectedCount === 0}
                onClick={clearSelection}
              >
                Bỏ chọn
              </button>
            </div>
            {loadingEmployees && <p className="field-hint">Đang tải danh sách…</p>}
            {!loadingEmployees && deptEmployees.length === 0 && (
              <p className="field-hint">Không có NV đang làm / thử việc trong bộ phận này.</p>
            )}
            {!loadingEmployees && deptEmployees.length > 0 && (
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
                            else clearSelection();
                          }}
                        />
                      </th>
                      <th>MSNV</th>
                      <th>Họ tên</th>
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
                          <td>{emp.team_code ?? "—"}</td>
                          <td className="num">{fmtVnd(emp.contract_salary)}</td>
                          <td>{labelEmpStatus(emp.status)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <p className="field-hint" style={{ marginTop: 8 }}>
              Chỉ hiện NV đang làm và thử việc. Tick một hoặc nhiều người rồi «Xem trước».
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
          «Cả bộ phận» = mọi NV đang làm trong bộ phận · «Chọn một vài người» = tick trong
          danh sách · In phụ lục GenusSuite — mỗi NV một trang.
        </p>
      </form>
    </div>
  );
}
