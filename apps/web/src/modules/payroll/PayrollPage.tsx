import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  calculatePayroll,
  createPayAdjustment,
  deletePayAdjustment,
  downloadPayrollExport,
  fetchDepartments,
  fetchEmployees,
  fetchPayAdjustments,
  fetchPayrollPeriod,
  fetchPayslips,
  fetchTeams,
  lockPayroll,
  publishPayroll,
  reopenPayroll,
  unlockPayroll,
  type Department,
  type PayPeriodStatus,
  type Payslip,
  type PayslipAdjustment,
  type Team,
} from "../../shared/api";
import { useAuth } from "../../shared/authStore";
import { currentPayPeriod } from "../../shared/formatDate";
import {
  departmentsWithActiveTeams,
  formatDepartmentLabel,
} from "../../shared/formatOrg";
import { PayrollGridSection } from "./PayrollGridSection";
import { PayrollPayslipSection } from "./PayrollPayslipSection";
import { PayrollSimulateSection } from "./PayrollSimulateSection";
import type { PayrollViewMode } from "./payrollGridColumns";
import { useEscLayer } from "../../shared/useEscLayer";
import { ToolbarMoreMenu } from "../../shared/ToolbarMoreMenu";
import { EmployeeCodePicker } from "../../shared/EmployeeCodePicker";
import { disabledTitle } from "../../shared/disabledHint";

const STATUS_LABEL: Record<string, string> = {
  open: "Mở",
  calculating: "Đã tính",
  published: "Đã phát hành",
  locked: "Đã khóa",
};

type PayrollTab = "grid" | "payslip" | "simulate";

const VIEW_PREFS_KEY = "payroll_grid_view_mode";

function loadViewMode(): PayrollViewMode {
  try {
    const raw = localStorage.getItem(VIEW_PREFS_KEY);
    if (raw === "work" || raw === "allowance" || raw === "deduction" || raw === "full" || raw === "compact") {
      return raw;
    }
  } catch {
    /* ignore */
  }
  return "compact";
}

export function PayrollPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [period, setPeriod] = useState(currentPayPeriod);
  const [tab, setTab] = useState<PayrollTab>("grid");
  const [viewMode, setViewMode] = useState<PayrollViewMode>(loadViewMode);
  const [selected, setSelected] = useState<Payslip | null>(null);
  const [periodMeta, setPeriodMeta] = useState<PayPeriodStatus | null>(null);
  const [rows, setRows] = useState<Payslip[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportDeptId, setExportDeptId] = useState("");
  const [exportEmpCode, setExportEmpCode] = useState("");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [empDeptByCode, setEmpDeptByCode] = useState<Map<string, string>>(new Map());
  const [adjustments, setAdjustments] = useState<PayslipAdjustment[]>([]);
  const [adjOpen, setAdjOpen] = useState(false);
  const [adjKind, setAdjKind] = useState<"addon" | "deduction">("addon");
  const [adjEmp, setAdjEmp] = useState("5290");
  const [adjReason, setAdjReason] = useState("Truy lĩnh T9");
  const [adjAmount, setAdjAmount] = useState("100000");

  const periodStatus = periodMeta?.status ?? "open";
  const canCalculate = periodStatus === "open" || periodStatus === "calculating";
  const canPublish =
    (periodStatus === "open" || periodStatus === "calculating") && rows.length > 0;
  const canLock = periodStatus === "published";
  const canUnlock = isAdmin && periodStatus === "locked";
  const canReopen = isAdmin && (periodStatus === "published" || periodStatus === "locked");
  const canExport = rows.length > 0;
  const canAdjust = periodStatus === "open" || periodStatus === "calculating";

  useEffect(() => {
    localStorage.setItem(VIEW_PREFS_KEY, viewMode);
  }, [viewMode]);

  useEffect(() => {
    void fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
    void fetchTeams().then(setTeams).catch(() => setTeams([]));
    void fetchEmployees({ status: "all" })
      .then((emps) => {
        setEmpDeptByCode(
          new Map(emps.map((e) => [e.employee_code, e.department_id ?? ""])),
        );
      })
      .catch(() => setEmpDeptByCode(new Map()));
  }, []);

  const exportDepartmentOptions = useMemo(
    () => departmentsWithActiveTeams(departments, teams),
    [departments, teams],
  );

  const exportEmployeeOptions = useMemo(() => {
    const list = [...rows].sort((a, b) => a.employee_code.localeCompare(b.employee_code));
    if (!exportDeptId) return list;
    return list.filter((r) => empDeptByCode.get(r.employee_code) === exportDeptId);
  }, [rows, exportDeptId, empDeptByCode]);

  useEffect(() => {
    if (exportEmpCode && !exportEmployeeOptions.some((r) => r.employee_code === exportEmpCode)) {
      setExportEmpCode("");
    }
  }, [exportEmpCode, exportEmployeeOptions]);

  const exportScopeLabel = useMemo(() => {
    if (exportEmpCode) {
      const row = rows.find((r) => r.employee_code === exportEmpCode);
      return row ? `MSNV ${exportEmpCode} — ${row.full_name}` : `MSNV ${exportEmpCode}`;
    }
    if (exportDeptId) {
      const dept = exportDepartmentOptions.find((d) => d.id === exportDeptId);
      return dept ? formatDepartmentLabel(dept) : "bộ phận đã chọn";
    }
    return "cả công ty";
  }, [exportEmpCode, exportDeptId, exportDepartmentOptions, rows]);

  useEscLayer(adjOpen, () => setAdjOpen(false));

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [slips, meta, adj] = await Promise.all([
        fetchPayslips(period),
        fetchPayrollPeriod(period),
        fetchPayAdjustments(period),
      ]);
      setRows(slips);
      setPeriodMeta(meta);
      setAdjustments(adj);
      setSelected((prev) => {
        if (prev && slips.some((s) => s.id === prev.id)) {
          return slips.find((s) => s.id === prev.id) ?? null;
        }
        return slips[0] ?? null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải bảng lương.");
    }
  }, [period]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const onSelectSlip = useCallback((slip: Payslip) => {
    setSelected(slip);
  }, []);

  async function onCalculate() {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const r = await calculatePayroll(period);
      setOk(r.message);
      setRows(r.payslips);
      setPeriodMeta(await fetchPayrollPeriod(period));
      setSelected(r.payslips[0] ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tính lương được.");
    } finally {
      setBusy(false);
    }
  }

  async function onPublish() {
    if (!window.confirm(`Phát hành phiếu lương kỳ ${period} cho công nhân xem?`)) return;
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const r = await publishPayroll(period);
      setOk(r.message);
      setPeriodMeta(r.period);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không phát hành được.");
    } finally {
      setBusy(false);
    }
  }

  async function onLock() {
    if (!window.confirm(`Khóa kỳ ${period}? Sau khi khóa không tính lại / phát hành.`)) return;
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const r = await lockPayroll(period);
      setOk(r.message);
      setPeriodMeta(r.period);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không khóa kỳ được.");
    } finally {
      setBusy(false);
    }
  }

  async function onUnlock() {
    if (!window.confirm(`Mở khóa kỳ ${period}? (chỉ Admin — ghi hộp đen)`)) return;
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const r = await unlockPayroll(period);
      setOk(r.message);
      setPeriodMeta(r.period);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không mở khóa được.");
    } finally {
      setBusy(false);
    }
  }

  async function onReopen() {
    if (
      !window.confirm(
        `Mở lại kỳ ${period} để tính lương?\nPhiếu công nhân đã xác nhận được giữ; phiếu khác về nháp.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const r = await reopenPayroll(period);
      setOk(r.message);
      setPeriodMeta(r.period);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không mở lại kỳ được.");
    } finally {
      setBusy(false);
    }
  }

  async function onExport(channel: "ATM" | "CASH" | "ALL") {
    if (!canExport) return;
    setExporting(true);
    setError(null);
    try {
      await downloadPayrollExport(period, channel, {
        departmentId: exportEmpCode ? undefined : exportDeptId || undefined,
        employeeCode: exportEmpCode || undefined,
      });
      setOk(`Đã xuất Excel ${channel} kỳ ${period} — ${exportScopeLabel}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xuất được file.");
    } finally {
      setExporting(false);
    }
  }

  async function onAdjSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canAdjust) return;
    const code = adjEmp.trim();
    if (!code) {
      setError("Nhập MSNV cần điều chỉnh.");
      return;
    }
    if (!rows.some((r) => r.employee_code === code)) {
      setError(`MSNV ${code} không có trong bảng lương kỳ ${period}.`);
      return;
    }
    const amountRaw = adjAmount.trim().replace(/\./g, "").replace(/,/g, "");
    if (!/^\d+$/.test(amountRaw) || Number(amountRaw) <= 0) {
      setError("Số tiền điều chỉnh phải là số nguyên dương (VND).");
      return;
    }
    if (!adjReason.trim()) {
      setError("Nhập lý do điều chỉnh.");
      return;
    }
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      await createPayAdjustment({
        period,
        employee_code: code,
        kind: adjKind,
        reason: adjReason.trim(),
        amount: amountRaw,
      });
      setOk("Đã lưu điều chỉnh. Bấm Tính lương lại để áp vào phiếu.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu điều chỉnh.");
    } finally {
      setBusy(false);
    }
  }

  async function onAdjDelete(id: string) {
    setBusy(true);
    setError(null);
    try {
      await deletePayAdjustment(id);
      setOk("Đã xóa điều chỉnh.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    } finally {
      setBusy(false);
    }
  }

  const tabHint = useMemo(
    () =>
      tab === "grid"
        ? "5 chế độ xem · cột Δ so kỳ trước (đỏ nếu lệch ≥ 500.000đ)"
        : "3 khối ngang · Trước/Sau duyệt từng phiếu",
    [tab],
  );

  return (
    <div className="module-page payroll-shell">
      <header className="module-header">
        <Link to="/" className="btn-back">
          ← Portal
        </Link>
        <nav className="breadcrumb">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <span>Tính Lương</span>
          <span aria-hidden> › </span>
          <span>Kỳ {period}</span>
        </nav>
      </header>
      <main className="module-body payroll-main">
        {error && <p className="banner-warn">{error}</p>}
        {ok && <p className="banner-ok">{ok}</p>}

        <section className="users-form-card payroll-toolbar-card payroll-toolbar-compact">
          <div className="calendar-row payroll-toolbar-row">
            <label className="field payroll-field-period">
              <span>Kỳ</span>
              <input
                type="month"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                disabled={busy}
              />
            </label>
            {periodMeta && (
              <span className="payroll-period-badge">
                {STATUS_LABEL[periodStatus] ?? periodStatus}
                <span className="payroll-period-badge-sub">
                  ÷{periodMeta.salary_divisor} · {periodMeta.official_work_days}n
                </span>
              </span>
            )}
            <button
              type="button"
              className="btn-primary btn-compact"
              disabled={busy || !canCalculate}
              title={disabledTitle(!canCalculate, "Kỳ đã khóa hoặc không ở trạng thái mở")}
              onClick={() => void onCalculate()}
            >
              {busy ? "…" : "Tính lương"}
            </button>
            <button
              type="button"
              className="btn-primary btn-compact"
              disabled={busy || !canPublish || rows.length === 0}
              title={disabledTitle(
                !canPublish || rows.length === 0,
                rows.length === 0
                  ? "Chưa có phiếu lương"
                  : periodStatus === "published" || periodStatus === "locked"
                    ? "Kỳ đã phát hành hoặc đã khóa"
                    : "Chỉ phát hành khi kỳ đang mở / đã tính",
              )}
              onClick={() => void onPublish()}
            >
              Phát hành
            </button>
            <button
              type="button"
              className="btn-ghost-dark btn-compact"
              disabled={busy || !canLock}
              title={disabledTitle(!canLock, "Chỉ khóa sau khi đã phát hành")}
              onClick={() => void onLock()}
            >
              Khóa
            </button>
            <button type="button" className="btn-ghost-dark btn-compact" disabled={busy} onClick={() => void reload()}>
              Làm mới
            </button>
            <ToolbarMoreMenu disabled={busy}>
              {isAdmin && (
                <button
                  type="button"
                  className="toolbar-more-item"
                  disabled={!canUnlock}
                  onClick={() => void onUnlock()}
                >
                  Mở khóa kỳ
                </button>
              )}
              {isAdmin && (
                <button
                  type="button"
                  className="toolbar-more-item"
                  disabled={!canReopen}
                  onClick={() => void onReopen()}
                >
                  Mở lại kỳ
                </button>
              )}
              <div className="toolbar-more-field">
                <span>Xuất bộ phận</span>
                <select
                  value={exportDeptId}
                  onChange={(e) => setExportDeptId(e.target.value)}
                  disabled={exporting || !!exportEmpCode}
                >
                  <option value="">Cả công ty</option>
                  {exportDepartmentOptions.map((d) => (
                    <option key={d.id} value={d.id}>
                      {formatDepartmentLabel(d)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="toolbar-more-field">
                <span>Xuất 1 người</span>
                <EmployeeCodePicker
                  options={exportEmployeeOptions}
                  value={exportEmpCode}
                  onChange={setExportEmpCode}
                  disabled={exporting}
                  placeholder="Tìm MSNV / họ tên…"
                />
              </div>
              <button
                type="button"
                className="toolbar-more-item"
                disabled={exporting || !canExport}
                onClick={() => void onExport("ATM")}
              >
                Xuất ATM
              </button>
              <button
                type="button"
                className="toolbar-more-item"
                disabled={exporting || !canExport}
                onClick={() => void onExport("CASH")}
              >
                Xuất tiền mặt
              </button>
              <button
                type="button"
                className="toolbar-more-item"
                disabled={exporting || !canExport}
                onClick={() => void onExport("ALL")}
              >
                {exporting ? "Đang xuất…" : "Xuất ATM+TM"}
              </button>
            </ToolbarMoreMenu>
          </div>
        </section>

        <div className="payroll-status-bar" aria-live="polite">
          <span>
            {rows.length} phiếu · {STATUS_LABEL[periodStatus] ?? periodStatus}
            {periodMeta ? ` · ÷${periodMeta.salary_divisor}` : ""}
          </span>
          {exportEmpCode || exportDeptId ? (
            <span className="payroll-status-scope">Xuất: {exportScopeLabel}</span>
          ) : null}
        </div>

        <nav className="payroll-tabs" aria-label="Màn tính lương">
          <button
            type="button"
            className={tab === "grid" ? "btn-primary" : "btn-ghost-dark"}
            onClick={() => setTab("grid")}
          >
            Bảng lương
          </button>
          <button
            type="button"
            className={tab === "payslip" ? "btn-primary" : "btn-ghost-dark"}
            onClick={() => setTab("payslip")}
          >
            Phiếu lương
          </button>
          <button
            type="button"
            className={tab === "simulate" ? "btn-primary" : "btn-ghost-dark"}
            onClick={() => setTab("simulate")}
          >
            Chạy thử
          </button>
          <button
            type="button"
            className={adjOpen ? "btn-primary" : "btn-ghost-dark"}
            onClick={() => setAdjOpen((v) => !v)}
            title="Trả lại / truy lĩnh / tạm ứng"
          >
            Điều chỉnh{adjustments.length ? ` (${adjustments.length})` : ""}
          </button>
          <span className="field-hint payroll-tab-hint">{tabHint}</span>
        </nav>

        {tab === "simulate" ? (
          <PayrollSimulateSection period={period} />
        ) : tab === "grid" ? (
          <section className="users-list-card payroll-grid-card">
            <PayrollGridSection
              period={period}
              rows={rows}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              selectedId={selected?.id ?? null}
              onSelect={(slip) => {
                onSelectSlip(slip);
              }}
            />
          </section>
        ) : (
          <PayrollPayslipSection rows={rows} selected={selected} onSelect={onSelectSlip} />
        )}

        {adjOpen && (
        <section className="users-form-card payroll-adj-card">
          <h2>Điều chỉnh (trả lại / truy lĩnh / tạm ứng)</h2>
          <p className="field-hint">
            Cộng vào tổng thu · Trừ thực lãnh. Nhập trước khi phát hành, rồi Tính lương lại.
          </p>
          <form onSubmit={(e) => void onAdjSubmit(e)}>
            <div className="calendar-row">
              <label className="field">
                <span>Loại</span>
                <select
                  value={adjKind}
                  onChange={(e) => setAdjKind(e.target.value as "addon" | "deduction")}
                  disabled={!canAdjust || busy}
                >
                  <option value="addon">Cộng (tổng thu)</option>
                  <option value="deduction">Trừ (thực lãnh)</option>
                </select>
              </label>
              <label className="field">
                <span>MSNV</span>
                <input
                  value={adjEmp}
                  onChange={(e) => setAdjEmp(e.target.value)}
                  required
                  disabled={!canAdjust || busy}
                />
              </label>
              <label className="field">
                <span>Số tiền</span>
                <input
                  value={adjAmount}
                  onChange={(e) => setAdjAmount(e.target.value)}
                  required
                  disabled={!canAdjust || busy}
                />
              </label>
              <label className="field" style={{ flex: 1 }}>
                <span>Lý do</span>
                <input
                  value={adjReason}
                  onChange={(e) => setAdjReason(e.target.value)}
                  required
                  disabled={!canAdjust || busy}
                />
              </label>
              <button type="submit" className="btn-primary" disabled={!canAdjust || busy}>
                Lưu
              </button>
            </div>
          </form>
          {adjustments.length > 0 && (
            <table className="users-table" style={{ marginTop: 12 }}>
              <thead>
                <tr>
                  <th>MSNV</th>
                  <th>Loại</th>
                  <th>Số tiền</th>
                  <th>Lý do</th>
                  <th>Người nhập</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {adjustments.map((a) => (
                  <tr key={a.id}>
                    <td>{a.employee_code}</td>
                    <td>{a.kind === "addon" ? "Cộng" : "Trừ"}</td>
                    <td>{Number(a.amount).toLocaleString("vi-VN")}</td>
                    <td>{a.reason}</td>
                    <td>{a.created_by}</td>
                    <td>
                      <button
                        type="button"
                        className="link-btn danger"
                        disabled={!canAdjust || busy}
                        onClick={() => void onAdjDelete(a.id)}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
        )}
      </main>
    </div>
  );
}
