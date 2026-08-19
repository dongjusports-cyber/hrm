import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent, ICellRendererParams, RowDoubleClickedEvent } from "ag-grid-community";
import {
  downloadEmployeesExport,
  fetchDepartments,
  fetchEmployees,
  fetchTeams,
  importAllowancesExcel,
  importEmployeesExcel,
  downloadEmployeeImportTemplate,
  unlockResetWorkerPassword,
  type Department,
  type Employee,
  type Team,
} from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";
import {
  activeTeams,
  departmentsWithActiveTeams,
  formatDepartmentLabel,
  formatOrgColumnCell,
  formatTeamLabel,
  orgColumnHeader,
} from "../../shared/formatOrg";
import {
  restoreAgGridColumnState,
  saveAgGridColumnState,
} from "../../shared/agGridColumnPrefs";
import { employeeMatchesQuery } from "../../shared/employeeSearch";
import { ToolbarSearchInput } from "../../shared/ToolbarSearchInput";
import { useAgGridExternalFilter } from "../../shared/useAgGridExternalFilter";
import { useHrHeaderRight } from "./HrLayout";
import { TransferTeamModal } from "./TransferTeamModal";
import { EmployeeProfileSheet } from "./EmployeeProfileSheet";
import { RehireSheet } from "./RehireSheet";
import { ToolbarMoreMenu } from "../../shared/ToolbarMoreMenu";
import { disabledTitle } from "../../shared/disabledHint";
import { useHrSubpageEsc } from "../../shared/useHrSubpageEsc";
import { cacheHydrate, cachePeek, employeesCacheKey } from "../../shared/clientCache";
import { useAliveParams, useKeepAlivePaneActive } from "../../shared/keepAlive";

type StatusFilter =
  | "active"
  | "probation"
  | "resigned"
  | "maternity"
  | "special_regime"
  | "all";
type ViewMode = "compact" | "full";

const FILTER_META: Record<StatusFilter, { title: string; hint: string }> = {
  all: { title: "Tất cả nhân viên", hint: "Toàn bộ hồ sơ" },
  active: { title: "Chính thức", hint: "Đã ký hợp đồng chính thức" },
  probation: { title: "Thử việc", hint: "Đang thử việc" },
  maternity: { title: "Thai sản", hint: "Nghỉ thai sản" },
  special_regime: {
    title: "Chế độ đặc biệt",
    hint: "Mang thai / Nghỉ thai sản / Nuôi con nhỏ — ngày vào, kỳ hiệu lực, lương BHXH",
  },
  resigned: { title: "Thôi việc", hint: "Đã thôi việc" },
};

// Khớp EXPORT_COLUMNS bên API (app/modules/mdm/export_employees.py) — một nguồn cột duy nhất.
const COMPACT_COLUMNS = [
  "employee_code",
  "full_name",
  "department_code",
  "team_code",
  "status",
  "account_status_label",
];
const FULL_COLUMNS = [
  "employee_code",
  "full_name",
  "department_code",
  "team_code",
  "position_title",
  "join_date",
  "contract_signed_at",
  "seniority_label",
  "seniority_amount",
  "annual_leave_remaining",
  "contract_type_label",
  "total_salary",
  "status",
  "account_status_label",
];
const SPECIAL_COLUMNS = [
  "employee_code",
  "full_name",
  "team_name",
  "join_date",
  "wt_regime_date_from",
  "wt_regime_date_to",
  "wt_regime_type",
  "si_base",
];

const WT_REGIME_LABEL: Record<string, string> = {
  PREGNANT: "Đang mang thai",
  MATERNITY: "Nghỉ thai sản",
  CHILD: "Nuôi con nhỏ",
};

const VIEW_PREFS_KEY = "hr_employees_view_prefs";
/** v7: cột khít chữ, dồn trái; không flex/autoSize (tránh Chức vụ phình, Thâm niên cắt chữ). */
const COLUMN_STATE_PREFIX = "hr_employees_column_state_v7";

function columnStateKey(viewMode: ViewMode, statusFilter: StatusFilter): string {
  if (statusFilter === "special_regime") return `${COLUMN_STATE_PREFIX}_special_regime`;
  return `${COLUMN_STATE_PREFIX}_${viewMode}`;
}

type ViewPrefs = {
  department_id: string;
  team_id: string;
  viewMode: ViewMode;
};

function loadViewPrefs(): ViewPrefs {
  try {
    const raw = localStorage.getItem(VIEW_PREFS_KEY);
    if (!raw) return { department_id: "", team_id: "", viewMode: "full" };
    const parsed = JSON.parse(raw) as Partial<ViewPrefs>;
    return {
      department_id: parsed.department_id ?? "",
      team_id: parsed.team_id ?? "",
      viewMode: parsed.viewMode === "compact" ? "compact" : "full",
    };
  } catch {
    return { department_id: "", team_id: "", viewMode: "full" };
  }
}

function saveViewPrefs(prefs: ViewPrefs) {
  localStorage.setItem(VIEW_PREFS_KEY, JSON.stringify(prefs));
}

function parseFilter(raw: string | undefined): StatusFilter {
  if (raw && raw in FILTER_META) return raw as StatusFilter;
  return "all";
}

function formatLeaveDays(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("vi-VN", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatVnd(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("vi-VN");
}

/** Danh sách NV full màn theo nhóm (từ ô Nhân Sự). */
export function EmployeesPage() {
  const { filterKey } = useAliveParams();
  const statusFilter = parseFilter(filterKey);
  const specialGrid = statusFilter === "special_regime";
  const paneActive = useKeepAlivePaneActive();
  useHrSubpageEsc({ backTo: "/m/hr" });
  const meta = FILTER_META[statusFilter];
  const navigate = useNavigate();
  const location = useLocation();
  const [rows, setRows] = useState<Employee[]>([]);
  const [appliedQ, setAppliedQ] = useState("");
  const [liveQ, setLiveQ] = useState("");
  const [searchReset, setSearchReset] = useState(0);
  const typedQRef = useRef("");
  const fetchSeqRef = useRef(0);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [selectedRows, setSelectedRows] = useState<Employee[]>([]);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [rehireEmp, setRehireEmp] = useState<Employee | null>(null);
  const [profileEmpId, setProfileEmpId] = useState<string | null>(null);

  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const initialPrefs = useMemo(loadViewPrefs, []);
  const [departmentId, setDepartmentId] = useState(initialPrefs.department_id);
  const [teamId, setTeamId] = useState(initialPrefs.team_id);
  const [viewMode, setViewMode] = useState<ViewMode>(initialPrefs.viewMode);
  const gridApiRef = useRef<GridApi<Employee> | null>(null);

  const persistColumns = useCallback(
    (api: GridApi<Employee>) => {
      saveAgGridColumnState(columnStateKey(viewMode, statusFilter), api);
    },
    [viewMode, statusFilter],
  );

  const applySavedColumns = useCallback(
    (api: GridApi<Employee>) => {
      restoreAgGridColumnState(columnStateKey(viewMode, statusFilter), api);
    },
    [viewMode, statusFilter],
  );

  useEffect(() => {
    setSearchReset((n) => n + 1);
    setAppliedQ("");
    setLiveQ("");
  }, [statusFilter]);

  useEffect(() => {
    if (!paneActive) return;
    const st = location.state as { openProfileId?: string } | null;
    if (st?.openProfileId) {
      setProfileEmpId(st.openProfileId);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [paneActive, location.state, location.pathname, navigate]);

  useEffect(() => {
    saveViewPrefs({ department_id: departmentId, team_id: teamId, viewMode });
  }, [departmentId, teamId, viewMode]);

  useEffect(() => {
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

  const searchCrossTabHint = useMemo(() => {
    if (!appliedQ.trim() || statusFilter === "all" || statusFilter === "resigned") return null;
    const others = rows.filter((e) => e.effective_status && e.effective_status !== statusFilter);
    if (others.length === 0) return null;
    const labels = [...new Set(others.map((e) => e.status_label || e.effective_status))];
    return `Kết quả gồm NV thuộc tab khác (${labels.join(", ")}) — vẫn mở được hồ sơ.`;
  }, [appliedQ, rows, statusFilter]);

  const reload = useCallback(async () => {
    const seq = ++fetchSeqRef.current;
    setError(null);
    const filters = {
      q: appliedQ || undefined,
      status: statusFilter,
      department_id: departmentId || undefined,
      team_id: teamId || undefined,
    };
    const key = employeesCacheKey(filters);
    const disk = cachePeek<Employee[]>(key) ?? (await cacheHydrate<Employee[]>(key));
    if (seq === fetchSeqRef.current && disk) setRows(disk);
    try {
      const data = await fetchEmployees(filters);
      if (seq !== fetchSeqRef.current) return;
      setRows(data);
    } catch (e) {
      if (seq !== fetchSeqRef.current) return;
      setError(e instanceof Error ? e.message : "Không tải được nhân sự.");
    }
  }, [appliedQ, statusFilter, departmentId, teamId]);

  useEffect(() => {
    if (!paneActive) return;
    void reload();
  }, [reload, paneActive]);

  function onDepartmentChange(id: string) {
    setDepartmentId(id);
    // Đổi bộ phận thì bỏ tổ đang chọn — tránh lọc lệch (tổ có thể không thuộc bộ phận mới).
    setTeamId("");
  }

  function onResetFilters() {
    setDepartmentId("");
    setTeamId("");
    setSearchReset((n) => n + 1);
    setAppliedQ("");
    setLiveQ("");
  }

  async function onUnlockReset(emp: Employee, e: MouseEvent) {
    e.stopPropagation();
    if (emp.account_status === "resigned" || emp.status === "resigned") {
      setError("Nhân viên đã nghỉ việc — không mở khóa đăng nhập.");
      return;
    }
    const okConfirm = window.confirm(
      `Reset mật khẩu cho ${emp.full_name} (MSNV ${emp.employee_code})?\n` +
        `Mật khẩu mới = 4 số cuối CCCD (chưa có CCCD thì 4 số cuối MSNV). Bắt buộc đổi lần đăng nhập sau.`,
    );
    if (!okConfirm) return;
    setBusyId(emp.id);
    setError(null);
    setOk(null);
    try {
      const result = await unlockResetWorkerPassword(emp.id);
      setOk(result.detail);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mở khóa thất bại.");
    } finally {
      setBusyId(null);
    }
  }

  const empFilter = useAgGridExternalFilter<Employee>({
    active: Boolean(liveQ.trim()),
    queryKey: liveQ,
    pass: (r) => employeeMatchesQuery(r, liveQ),
  });

  const visibleCount = useMemo(() => {
    if (!liveQ.trim()) return rows.length;
    return rows.filter((r) => employeeMatchesQuery(r, liveQ)).length;
  }, [rows, liveQ]);

  const headerRight = useMemo(
    (): ReactNode => (
      <>
        <span className="hr-layer-btn is-current">
          <span className="hr-layer-name">{meta.title}</span>
          <span className="hr-layer-count">{visibleCount} NV</span>
        </span>
        <Link to="/admin/qr-code" className="hr-layer-btn">
          QR công nhân
        </Link>
      </>
    ),
    [meta.title, visibleCount],
  );
  useHrHeaderRight(paneActive ? headerRight : null);

  const columnDefs = useMemo<ColDef<Employee>[]>(() => {
    if (specialGrid) {
      return [
        {
          field: "employee_code",
          headerName: "MSNV",
          width: 78,
          minWidth: 70,
          filter: false,
          pinned: "left",
          cellClass: "hr-cell-open-profile",
        },
        {
          field: "full_name",
          headerName: "Họ tên",
          minWidth: 168,
          width: 200,
          filter: false,
          pinned: "left",
          cellClass: "hr-cell-name-link",
        },
        {
          colId: "team",
          headerName: "Tổ",
          minWidth: 120,
          width: 148,
          filter: false,
          valueGetter: (p) => p.data?.team_name || p.data?.team_code || "—",
        },
        {
          field: "join_date",
          headerName: "Ngày vào",
          width: 118,
          minWidth: 108,
          filter: false,
          valueFormatter: (p) => formatDateDDMMYYYY(p.value),
        },
        {
          field: "wt_regime_date_from",
          headerName: "Ngày bắt đầu",
          width: 124,
          minWidth: 118,
          filter: false,
          valueFormatter: (p) => formatDateDDMMYYYY(p.value),
        },
        {
          field: "wt_regime_date_to",
          headerName: "Ngày kết thúc",
          width: 124,
          minWidth: 118,
          filter: false,
          valueFormatter: (p) => formatDateDDMMYYYY(p.value),
        },
        {
          field: "wt_regime_type",
          headerName: "Loại chế độ",
          width: 128,
          minWidth: 120,
          filter: false,
          valueFormatter: (p) => WT_REGIME_LABEL[String(p.value || "")] || p.value || "—",
        },
        {
          field: "si_base",
          headerName: "Lương tham gia BHXH",
          width: 168,
          minWidth: 156,
          filter: false,
          cellClass: "hr-cell-money",
          headerClass: "hr-header-money",
          valueFormatter: (p) => formatVnd(p.value),
        },
      ];
    }

    const base: ColDef<Employee>[] = [
      {
        colId: "sel",
        headerName: "",
        width: 44,
        pinned: "left",
        checkboxSelection: true,
        headerCheckboxSelection: true,
        sortable: false,
        resizable: false,
        suppressHeaderMenuButton: true,
        cellClass: "tk-grid-sel-cell",
        headerClass: "tk-grid-sel-header",
      },
      {
        field: "employee_code",
        headerName: "MSNV",
        width: 72,
        minWidth: 64,
        filter: false,
        pinned: "left",
        cellClass: "hr-cell-open-profile",
      },
      {
        field: "full_name",
        headerName: "Họ tên",
        minWidth: 168,
        width: 196,
        filter: false,
        pinned: "left",
        cellClass: "hr-cell-name-link",
      },
      {
        colId: "dept_team",
        headerName: orgColumnHeader({ departmentId, teamId }),
        minWidth: 100,
        width: 128,
        filter: false,
        cellClass: "hr-cell-org",
        valueGetter: (p) =>
          formatOrgColumnCell(
            p.data?.department_name,
            p.data?.department_code,
            p.data?.team_name,
            p.data?.team_code,
            { departmentId, teamId },
          ),
      },
    ];

    if (viewMode === "full") {
      base.push(
        {
          field: "position_title",
          headerName: "Chức vụ",
          minWidth: 108,
          width: 120,
          filter: false,
        },
        {
          field: "join_date",
          headerName: "Ngày vào",
          width: 108,
          minWidth: 108,
          filter: false,
          valueFormatter: (p) => formatDateDDMMYYYY(p.value),
        },
        {
          field: "contract_signed_at",
          headerName: "Ngày Ký HĐ",
          width: 118,
          minWidth: 118,
          filter: false,
          valueFormatter: (p) => formatDateDDMMYYYY(p.value),
        },
        {
          field: "seniority_label",
          headerName: "Thâm niên",
          width: 148,
          minWidth: 148,
          filter: false,
        },
        {
          field: "seniority_amount",
          headerName: "PC thâm niên",
          width: 124,
          minWidth: 124,
          filter: false,
          cellClass: "hr-cell-money",
          headerClass: "hr-header-money",
          valueFormatter: (p) => formatVnd(p.value),
        },
        {
          field: "annual_leave_remaining",
          headerName: "Phép còn",
          width: 96,
          minWidth: 96,
          filter: false,
          cellClass: "hr-cell-money",
          headerClass: "hr-header-money",
          valueFormatter: (p) => formatLeaveDays(p.value),
        },
        {
          field: "contract_type_label",
          headerName: "Loại HĐ",
          minWidth: 188,
          width: 196,
          filter: false,
        },
        {
          field: "total_salary",
          headerName: "Lương Tổng",
          width: 124,
          minWidth: 124,
          filter: false,
          cellClass: "hr-cell-money",
          headerClass: "hr-header-money",
          valueFormatter: (p) => formatVnd(p.value),
        },
      );
    }

    if (statusFilter === "resigned") {
      base.push({
        colId: "rehire",
        headerName: "Tái tuyển",
        width: 120,
        sortable: false,
        filter: false,
        cellRenderer: (p: ICellRendererParams<Employee>) => {
          const emp = p.data;
          if (!emp) return null;
          return (
            <button
              type="button"
              className="btn-secondary btn-compact"
              onClick={(ev) => {
                ev.stopPropagation();
                setRehireEmp(emp);
              }}
            >
              Tái tuyển
            </button>
          );
        },
      });
    }

    base.push({
      colId: "unlock",
      headerName: "Bảo mật",
      width: 132,
      minWidth: 132,
      maxWidth: 136,
      suppressSizeToFit: true,
      resizable: false,
      sortable: false,
      filter: false,
      cellClass: "hr-cell-unlock",
      headerClass: "hr-header-unlock",
      cellRenderer: (p: ICellRendererParams<Employee>) => {
        const emp = p.data;
        if (!emp) return null;
        const resigned = emp.account_status === "resigned" || emp.status === "resigned";
        return (
          <button
            type="button"
            className="btn-unlock-reset"
            disabled={resigned || busyId === emp.id}
            onClick={(ev) => void onUnlockReset(emp, ev)}
          >
            {busyId === emp.id ? "Đang xử lý…" : "Reset Mật Khẩu"}
          </button>
        );
      },
    });

    return base;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busyId, viewMode, departmentId, teamId, statusFilter, specialGrid]);

  useEffect(() => {
    const api = gridApiRef.current;
    if (api) applySavedColumns(api);
  }, [viewMode, columnDefs, applySavedColumns]);

  function openProfile(emp: Employee) {
    if (emp.id) setProfileEmpId(emp.id);
  }

  function onCellClicked(e: CellClickedEvent<Employee>) {
    const colId = e.column.getColId();
    if ((colId === "full_name" || colId === "employee_code") && e.data?.id) {
      openProfile(e.data);
    }
  }

  function onRowDoubleClicked(e: RowDoubleClickedEvent<Employee>) {
    if (e.data?.id) openProfile(e.data);
  }

  async function onImport(file: File | null) {
    if (!file) return;
    setError(null);
    setOk(null);
    try {
      const result = await importEmployeesExcel(file);
      setOk(result.detail + (result.errors[0] ? ` — ${result.errors[0]}` : ""));
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nhập Excel thất bại.");
    }
  }

  async function onImportAllowances(file: File | null) {
    if (!file) return;
    setError(null);
    setOk(null);
    try {
      const result = await importAllowancesExcel(file);
      setOk(result.detail + (result.errors[0] ? ` — ${result.errors[0]}` : ""));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nhập phụ cấp thất bại.");
    }
  }

  async function onExport() {
    setExporting(true);
    setError(null);
    setOk(null);
    try {
      await downloadEmployeesExport(
        {
          q: appliedQ || undefined,
          status: statusFilter,
          department_id: departmentId || undefined,
          team_id: teamId || undefined,
        },
        specialGrid ? SPECIAL_COLUMNS : viewMode === "compact" ? COMPACT_COLUMNS : FULL_COLUMNS,
      );
      setOk(`Đã xuất Excel ${rows.length} nhân viên theo bộ lọc và cột đang hiện.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xuất Excel thất bại.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="hr-page hr-page-list">
      {error && <p className="banner-warn">{error}</p>}
      {searchCrossTabHint && <p className="field-hint">{searchCrossTabHint}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      <div className="hr-toolbar">
        <ToolbarSearchInput
          className="hr-toolbar-search"
          placeholder="Tìm MSNV / họ tên…"
          resetToken={searchReset}
          onQuery={setLiveQ}
          onTyped={(v) => {
            typedQRef.current = v;
          }}
          onSubmit={(needle) => setAppliedQ(needle)}
        />
        <select
          className="hr-toolbar-select"
          value={departmentId}
          onChange={(e) => onDepartmentChange(e.target.value)}
          aria-label="Bộ phận"
        >
          <option value="">Tất cả bộ phận</option>
          {departmentOptions.map((d) => (
            <option key={d.id} value={d.id}>
              {formatDepartmentLabel(d)}
            </option>
          ))}
        </select>
        <select
          className="hr-toolbar-select"
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          aria-label="Tổ"
        >
          <option value="">Tất cả tổ</option>
          {teamOptions.map((t) => (
            <option key={t.id} value={t.id}>
              {departmentId
                ? formatTeamLabel(t)
                : formatTeamLabel(t, { showDepartment: true })}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn-primary btn-compact"
          onClick={() => setAppliedQ(typedQRef.current.trim())}
        >
          Tìm
        </button>
        {!specialGrid ? (
        <div className="view-toggle view-toggle-compact">
          <button
            type="button"
            className={viewMode === "compact" ? "active" : ""}
            onClick={() => setViewMode("compact")}
          >
            Gọn
          </button>
          <button
            type="button"
            className={viewMode === "full" ? "active" : ""}
            onClick={() => setViewMode("full")}
          >
            Đầy đủ
          </button>
        </div>
        ) : null}
        <ToolbarMoreMenu>
          <button type="button" className="toolbar-more-item" onClick={onResetFilters}>
            Đặt lại lọc
          </button>
          <button
            type="button"
            className="toolbar-more-item"
            onClick={() => {
            localStorage.removeItem(columnStateKey(viewMode, statusFilter));
              gridApiRef.current?.resetColumnState();
            }}
          >
            Đặt lại cột
          </button>
          <button
            type="button"
            className="toolbar-more-item"
            disabled={exporting}
            onClick={() => void onExport()}
          >
            {exporting ? "Đang xuất…" : "Xuất Excel"}
          </button>
          <button
            type="button"
            className="toolbar-more-item"
            onClick={() => void downloadEmployeeImportTemplate().catch((err) => setError(err instanceof Error ? err.message : "Không tải được mẫu Excel."))}
          >
            Tải mẫu Excel NV
          </button>
          <label className="toolbar-more-item file-btn">
            Nhập Excel nhân viên
            <input
              type="file"
              accept=".xlsx,.xlsm"
              hidden
              onChange={(e) => void onImport(e.target.files?.[0] ?? null)}
            />
          </label>
          <label className="toolbar-more-item file-btn">
            Nhập phụ cấp
            <input
              type="file"
              accept=".xlsx,.xlsm"
              hidden
              onChange={(e) => void onImportAllowances(e.target.files?.[0] ?? null)}
            />
          </label>
        </ToolbarMoreMenu>
        <div className="hr-toolbar-end">
          {selectedRows.length > 0 ? (
            <span className="hr-status-count" aria-live="polite">
              Đã chọn {selectedRows.length}
            </span>
          ) : null}
          {!specialGrid ? (
            <div className="hr-status-actions">
              <button
                type="button"
                className="btn-secondary btn-compact"
                disabled={selectedRows.length === 0}
                title={disabledTitle(selectedRows.length === 0, "Chọn ít nhất một dòng trên lưới")}
                onClick={() => setShowTransferModal(true)}
              >
                Chuyển tổ{selectedRows.length ? ` (${selectedRows.length})` : ""}
              </button>
              <button
                type="button"
                className="btn-secondary btn-compact"
                disabled={selectedRows.length === 0}
                title={disabledTitle(selectedRows.length === 0, "Chọn ít nhất một dòng trên lưới")}
                onClick={() =>
                  navigate("/m/hr/salary-raise", {
                    state: { employeeIds: selectedRows.map((r) => r.id) },
                  })
                }
              >
                Tăng lương{selectedRows.length ? ` (${selectedRows.length})` : ""}
              </button>
            </div>
          ) : null}
        </div>
      </div>

      <div className="ag-theme-quartz hr-grid hr-grid-list">
        <AgGridReact<Employee>
          rowData={rows}
          columnDefs={columnDefs}
          getRowId={(p) => p.data.id}
          rowHeight={specialGrid || viewMode === "full" ? 38 : 32}
          animateRows={false}
          rowSelection={specialGrid ? undefined : "multiple"}
          suppressRowClickSelection
          overlayNoRowsTemplate="<span>Không có nhân viên trong mục này</span>"
          onCellClicked={onCellClicked}
          onRowDoubleClicked={onRowDoubleClicked}
          onSelectionChanged={(e) => setSelectedRows(e.api.getSelectedRows())}
          onGridReady={(e: GridReadyEvent<Employee>) => {
            gridApiRef.current = e.api;
            applySavedColumns(e.api);
            empFilter.onGridReady(e);
          }}
          isExternalFilterPresent={empFilter.isExternalFilterPresent}
          doesExternalFilterPass={empFilter.doesExternalFilterPass}
          onFirstDataRendered={(e) => applySavedColumns(e.api)}
          onColumnMoved={(e) => persistColumns(e.api)}
          onColumnResized={(e) => {
            if (e.finished) persistColumns(e.api);
          }}
          onColumnPinned={(e) => persistColumns(e.api)}
          onColumnVisible={(e) => persistColumns(e.api)}
          defaultColDef={{
            sortable: true,
            resizable: true,
            filter: false,
            suppressHeaderMenuButton: true,
            flex: 0,
          }}
        />
      </div>

      {showTransferModal && (
        <TransferTeamModal
          employees={selectedRows}
          teams={activeTeamList}
          onClose={() => setShowTransferModal(false)}
          onDone={(msg) => {
            setShowTransferModal(false);
            setSelectedRows([]);
            setOk(msg);
            void reload();
          }}
        />
      )}

      {rehireEmp && (
        <RehireSheet
          employee={rehireEmp}
          teams={activeTeamList}
          onClose={() => setRehireEmp(null)}
          onDone={(msg) => {
            setRehireEmp(null);
            setOk(msg);
            void reload();
          }}
        />
      )}

      <EmployeeProfileSheet
        employeeId={profileEmpId ?? ""}
        open={profileEmpId !== null}
        onClose={() => setProfileEmpId(null)}
        onUpdated={() => void reload()}
      />
    </div>
  );
}
