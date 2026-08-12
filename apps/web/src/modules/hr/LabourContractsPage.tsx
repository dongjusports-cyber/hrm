import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchEmployees,
  fetchLabourContracts,
  type Employee,
  type LabourContract,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import { formatDepartmentLabel } from "../../shared/formatOrg";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";
import { EmployeeContractPanel } from "./EmployeeContractPanel";

type ContractPanelTab = "timeline" | "sign";

function sortByEndDate(rows: LabourContract[]): LabourContract[] {
  return [...rows].sort((a, b) => {
    const ae = a.end_date ?? "9999-12-31";
    const be = b.end_date ?? "9999-12-31";
    return ae.localeCompare(be);
  });
}

/** Nhân Sự → Hợp đồng lao động (5.2) — chọn MSNV như GenusSuite. */
export function LabourContractsPage() {
  const [searchParams] = useSearchParams();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [empQ, setEmpQ] = useState(() => searchParams.get("q") ?? "");
  const [expiring, setExpiring] = useState<LabourContract[]>([]);
  const [employeeContracts, setEmployeeContracts] = useState<LabourContract[]>([]);
  const [selectedEmpId, setSelectedEmpId] = useState<string | null>(
    () => searchParams.get("employee_id"),
  );
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [panelTab, setPanelTab] = useState<ContractPanelTab>("timeline");

  useHrSubpageEsc({
    onDismiss: () => {
      if (panelTab === "sign") {
        setPanelTab("timeline");
        return true;
      }
      if (selectedEmpId) {
        setSelectedEmpId(null);
        return true;
      }
      return false;
    },
  });

  async function loadExpiring() {
    const list = await fetchLabourContracts({ expiring_within_days: 60 });
    setExpiring(sortByEndDate(list));
  }

  async function loadEmployeeContracts(empId: string) {
    const list = await fetchLabourContracts({ employee_id: empId });
    setEmployeeContracts(
      [...list].sort((a, b) => a.start_date.localeCompare(b.start_date)),
    );
  }

  useEffect(() => {
    void fetchEmployees()
      .then(setEmployees)
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Không tải danh sách nhân viên.");
      });
    void loadExpiring().catch((e: unknown) => {
      setError(e instanceof Error ? e.message : "Không tải HĐ sắp hết hạn.");
    });
  }, []);

  useEffect(() => {
    if (!selectedEmpId) {
      setEmployeeContracts([]);
      return;
    }
    void loadEmployeeContracts(selectedEmpId).catch((e: unknown) => {
      setError(e instanceof Error ? e.message : "Không tải lịch sử HĐ.");
    });
  }, [selectedEmpId]);

  const filteredEmployees = useMemo(() => {
    const needle = empQ.trim().toLowerCase();
    if (!needle) return employees;
    return employees.filter(
      (e) =>
        e.employee_code.toLowerCase().includes(needle) ||
        e.full_name.toLowerCase().includes(needle) ||
        (e.department_name || "").toLowerCase().includes(needle),
    );
  }, [employees, empQ]);

  /** Gõ đúng / còn 1 kết quả → chọn luôn, khỏi kéo scrollbar khổng lồ. */
  useEffect(() => {
    if (filteredEmployees.length !== 1) return;
    const only = filteredEmployees[0];
    if (only.id === selectedEmpId) return;
    const needle = empQ.trim().toLowerCase();
    if (!needle) return;
    if (
      only.employee_code.toLowerCase() === needle ||
      filteredEmployees.length === 1
    ) {
      setSelectedEmpId(only.id);
    }
  }, [filteredEmployees, empQ, selectedEmpId]);

  const selectedEmployee = employees.find((e) => e.id === selectedEmpId);

  function selectEmployeeById(empId: string) {
    setSelectedEmpId(empId);
    setError(null);
    setOk(null);
  }

  async function onContractsChanged() {
    await loadExpiring();
    if (selectedEmpId) await loadEmployeeContracts(selectedEmpId);
  }

  return (
    <div className="config-section-page hr-contracts-page">
      <p className="field-hint">
        <Link to="/m/hr">← Nhân Sự</Link>
        <span aria-hidden> · </span>
        <span className="field-hint">ESC — về hub Nhân Sự</span>
      </p>
      <h1>Hợp đồng lao động</h1>
      <p className="field-hint">
        Chọn MSNV bên trái — tab «Lịch sử HĐ» / «Ký HĐ tiếp». In từng dòng HĐ (TV / HD1 / HD2 /
        VTH).
      </p>
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      <div className="hr-split hr-contracts-split">
        <div className="users-form-card hr-contracts-left">
          <h2>
            {empQ.trim()
              ? `Kết quả (${filteredEmployees.length})`
              : "Tìm nhân viên"}
          </h2>
          <input
            className="hr-search"
            type="search"
            value={empQ}
            onChange={(e) => setEmpQ(e.target.value)}
            placeholder="MSNV / họ tên / bộ phận"
            aria-label="Tìm nhân viên"
            autoComplete="off"
          />
          <ul className="hr-board-list hr-contracts-emp-list" aria-label="Danh sách nhân viên">
            {empQ.trim() === "" && (
              <li className="field-hint hr-contracts-emp-hint">
                Gõ MSNV hoặc họ tên để lọc — danh sách gọn, tối đa ~6 dòng.
              </li>
            )}
            {empQ.trim() !== "" && filteredEmployees.length === 0 && (
              <li className="module-placeholder">Không tìm thấy nhân viên.</li>
            )}
            {empQ.trim() !== "" &&
              filteredEmployees.slice(0, 50).map((emp) => (
              <li key={emp.id}>
                <button
                  type="button"
                  className={`hr-board-row hr-contract-emp-row${selectedEmpId === emp.id ? " is-selected" : ""}`}
                  onClick={() => selectEmployeeById(emp.id)}
                >
                  <span className="hr-board-main">
                    <strong>
                      {emp.employee_code} — {emp.full_name}
                    </strong>
                    <span className="field-hint">
                      {emp.department_name
                        ? formatDepartmentLabel({ name: emp.department_name })
                        : "—"}
                      {emp.contract_type_label ? ` · ${emp.contract_type_label}` : ""}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>

          <h3>Sắp hết hạn — 60 ngày ({expiring.length})</h3>
          <div className="hr-contracts-expiring-wrap">
            <table className="users-table hr-contracts-expiring">
              <thead>
                <tr>
                  <th>MSNV</th>
                  <th>Hết hạn</th>
                  <th>Còn</th>
                </tr>
              </thead>
              <tbody>
                {expiring.length === 0 && (
                  <tr>
                    <td colSpan={3} className="field-hint">
                      Không có HĐ sắp hết hạn.
                    </td>
                  </tr>
                )}
                {expiring.map((row) => (
                  <tr
                    key={row.id}
                    className={selectedEmpId === row.employee_id ? "is-selected" : undefined}
                    onClick={() => selectEmployeeById(row.employee_id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <strong>{row.employee_code}</strong>
                    </td>
                    <td>{formatDateDDMMYYYY(row.end_date)}</td>
                    <td>
                      {row.days_until_expiry != null ? `${row.days_until_expiry} ngày` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="users-form-card hr-contracts-right">
          <EmployeeContractPanel
            employee={selectedEmployee}
            employeeId={selectedEmpId}
            contracts={employeeContracts}
            busy={busy}
            setBusy={setBusy}
            onError={setError}
            onOk={setOk}
            onContractsChanged={onContractsChanged}
            tab={panelTab}
            onTabChange={setPanelTab}
          />
        </div>
      </div>
    </div>
  );
}
