import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import {
  fetchDepartments,
  fetchSimulatePolicyOptions,
  fetchTeams,
  runPayrollSimulate,
  type Department,
  type PolicyOption,
  type SimulateRow,
  type Team,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import {
  activeTeams,
  departmentsWithActiveTeams,
  formatDepartmentLabel,
  formatDeptTeam,
  formatTeamLabel,
} from "../../shared/formatOrg";
import { formatVnd, NET_DELTA_WARN_THRESHOLD } from "./payrollGridColumns";

type Scope = "all" | "department" | "team" | "employees";

type Props = {
  period: string;
};

export function PayrollSimulateSection({ period }: Props) {
  const [policies, setPolicies] = useState<PolicyOption[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [scope, setScope] = useState<Scope>("all");
  const [departmentId, setDepartmentId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [employeeCodes, setEmployeeCodes] = useState("");
  const [rows, setRows] = useState<SimulateRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void fetchSimulatePolicyOptions()
      .then((list) => {
        setPolicies(list);
        const active = list.find((p) => p.is_active);
        setPolicyId(active?.id ?? list[0]?.id ?? "");
      })
      .catch(() => setPolicies([]));
    void fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    void fetchTeams().then(setTeams).catch(() => setTeams([]));
  }, []);

  const activeTeamList = useMemo(() => activeTeams(teams), [teams]);
  const departmentOptions = useMemo(
    () => departmentsWithActiveTeams(departments, teams),
    [departments, teams],
  );

  const teamOptions = useMemo(
    () =>
      departmentId
        ? activeTeamList.filter((t) => t.department_id === departmentId)
        : activeTeamList,
    [activeTeamList, departmentId],
  );

  const onRun = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      setBusy(true);
      setError(null);
      setMessage(null);
      try {
        const codes =
          scope === "employees"
            ? employeeCodes
                .split(/[\s,;]+/)
                .map((c) => c.trim())
                .filter(Boolean)
            : undefined;
        const result = await runPayrollSimulate({
          period,
          policy_package_id: policyId || null,
          scope,
          department_id: scope === "department" && departmentId ? departmentId : null,
          team_id: scope === "team" && teamId ? teamId : null,
          employee_codes: codes,
        });
        setRows(result.rows);
        setMessage(result.message);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Chạy thử thất bại.");
        setRows([]);
      } finally {
        setBusy(false);
      }
    },
    [period, policyId, scope, departmentId, teamId, employeeCodes],
  );

  const cols = useMemo<ColDef<SimulateRow>[]>(
    () => [
      { field: "employee_code", headerName: "MSNV", width: 88, pinned: "left" },
      { field: "full_name", headerName: "Họ tên", flex: 1, minWidth: 130, pinned: "left" },
      {
        colId: "current_net",
        headerName: "Thực lãnh hiện tại",
        width: 130,
        valueGetter: (p) => p.data?.current?.net ?? null,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        colId: "sim_net",
        headerName: "Thực lãnh mô phỏng",
        width: 130,
        valueGetter: (p) => p.data?.simulated?.net ?? null,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        field: "delta_net",
        headerName: "Δ Thực lãnh",
        width: 118,
        valueFormatter: (p) => {
          if (p.value === null || p.value === undefined || p.value === "") return "—";
          const n = Number(p.value);
          if (Number.isNaN(n)) return String(p.value);
          const prefix = n > 0 ? "+" : "";
          return prefix + n.toLocaleString("vi-VN");
        },
        cellClass: (p) => {
          const n = Number(p.value);
          if (Number.isNaN(n) || n === 0) return undefined;
          return Math.abs(n) >= NET_DELTA_WARN_THRESHOLD ? "payroll-delta-warn" : "payroll-delta-ok";
        },
      },
      {
        colId: "current_gross",
        headerName: "Tổng TN hiện tại",
        width: 124,
        valueGetter: (p) => p.data?.current?.gross ?? null,
        valueFormatter: (p) => formatVnd(p.value),
      },
      {
        colId: "sim_gross",
        headerName: "Tổng TN mô phỏng",
        width: 124,
        valueGetter: (p) => p.data?.simulated?.gross ?? null,
        valueFormatter: (p) => formatVnd(p.value),
      },
    ],
    [],
  );

  return (
    <div className="payroll-simulate-split">
      <form className="users-form-card payroll-simulate-form" onSubmit={(e) => void onRun(e)}>
        <h2>Chạy thử</h2>
        <p className="field-hint">
          Chọn gói chính sách và phạm vi — so sánh với số đã tính trên kỳ {period}. Không ghi CSDL.
        </p>

        <label className="field">
          <span>Gói chính sách</span>
          <select value={policyId} onChange={(e) => setPolicyId(e.target.value)} required>
            {policies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.is_active ? " (đang dùng)" : ""} · {formatDateDDMMYYYY(p.effective_from)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Phạm vi</span>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as Scope)}
          >
            <option value="all">Toàn kỳ</option>
            <option value="department">Theo bộ phận</option>
            <option value="team">Theo tổ</option>
            <option value="employees">Theo MSNV</option>
          </select>
        </label>

        {scope === "department" && (
          <label className="field">
            <span>Bộ phận</span>
            <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} required>
              <option value="">— Chọn —</option>
              {departmentOptions.map((d) => (
                <option key={d.id} value={d.id}>
                  {formatDepartmentLabel(d)}
                </option>
              ))}
            </select>
          </label>
        )}

        {scope === "team" && (
          <label className="field">
            <span>Tổ</span>
            <select value={teamId} onChange={(e) => setTeamId(e.target.value)} required>
              <option value="">— Chọn —</option>
              {teamOptions.map((t) => (
                <option key={t.id} value={t.id}>
                  {formatTeamLabel(t, { showDepartment: true })}
                </option>
              ))}
            </select>
          </label>
        )}

        {scope === "employees" && (
          <label className="field">
            <span>MSNV (cách nhau dấu phẩy hoặc xuống dòng)</span>
            <textarea
              value={employeeCodes}
              onChange={(e) => setEmployeeCodes(e.target.value)}
              rows={3}
              placeholder="5290, 1519"
              required
            />
          </label>
        )}

        <button type="submit" className="btn-primary" disabled={busy || !policyId}>
          {busy ? "Đang mô phỏng…" : "Chạy thử"}
        </button>
      </form>

      <section className="users-list-card payroll-simulate-result">
        <h2>Kết quả so sánh</h2>
        {error && <p className="banner-warn">{error}</p>}
        {message && <p className="banner-ok">{message}</p>}
        {!rows.length && !busy && (
          <p className="field-hint">Chọn gói chính sách rồi bấm «Chạy thử» để xem chênh lệch.</p>
        )}
        <div className="ag-theme-quartz payroll-grid payroll-grid-tall">
          <AgGridReact<SimulateRow>
            rowData={rows}
            columnDefs={cols}
            domLayout="autoHeight"
            suppressCellFocus
            getRowId={(p) => p.data.employee_id}
          />
        </div>
      </section>
    </div>
  );
}
