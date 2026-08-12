import type { ColDef, CellClassParams } from "ag-grid-community";
import type { Payslip } from "../../shared/api";
import { formatDateDDMMYYYY } from "../../shared/formatDate";

export type PayrollViewMode = "compact" | "work" | "allowance" | "deduction" | "full";

export const PAYROLL_VIEW_LABELS: Record<PayrollViewMode, string> = {
  compact: "Gọn",
  work: "Công",
  allowance: "Phụ cấp",
  deduction: "Khấu trừ",
  full: "Đầy đủ",
};

/** Ngưỡng tô màu chênh Thực lãnh so kỳ trước (23§23.4). */
export const NET_DELTA_WARN_THRESHOLD = 500_000;

export function formatVnd(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("vi-VN");
}

function deltaCellClass(p: CellClassParams<Payslip>): string | undefined {
  const d = Number(p.value);
  if (Number.isNaN(d) || d === 0) return "payroll-delta-zero";
  return Math.abs(d) >= NET_DELTA_WARN_THRESHOLD ? "payroll-delta-warn" : "payroll-delta-ok";
}

const ID_COLS: ColDef<Payslip>[] = [
  { field: "employee_code", headerName: "MSNV", width: 88, minWidth: 72 },
  { field: "full_name", headerName: "Họ tên", flex: 2, minWidth: 120 },
];

/** Chỉ ghim trái khi nhiều cột — tránh khoảng trống giữa vùng ghim. */
const PINNED_LEFT: ColDef<Payslip>[] = [
  { field: "employee_code", headerName: "MSNV", width: 88, pinned: "left" },
  { field: "full_name", headerName: "Họ tên", flex: 1, minWidth: 130, pinned: "left" },
];

const NET_DELTA: ColDef<Payslip> = {
  field: "net_delta",
  headerName: "Δ Thực lãnh",
  width: 118,
  headerTooltip: `Chênh Thực lãnh so kỳ trước — đỏ nếu |Δ| ≥ ${NET_DELTA_WARN_THRESHOLD.toLocaleString("vi-VN")}đ`,
  valueFormatter: (p) => {
    if (p.value === null || p.value === undefined || p.value === "") return "—";
    const n = Number(p.value);
    if (Number.isNaN(n)) return String(p.value);
    const prefix = n > 0 ? "+" : "";
    return prefix + n.toLocaleString("vi-VN");
  },
  cellClass: deltaCellClass,
};

const PINNED_RIGHT: ColDef<Payslip>[] = [
  {
    field: "net",
    headerName: "Thực lãnh",
    width: 118,
    pinned: "right",
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "status",
    headerName: "TT phiếu",
    width: 108,
    pinned: "right",
    valueFormatter: (p) =>
      (
        {
          draft: "Nháp",
          published: "Đã PH",
          confirmed: "Đã XN",
          disputed: "Khiếu nại",
          locked: "Khóa",
        } as Record<string, string>
      )[String(p.value ?? "")] ?? String(p.value ?? "—"),
  },
];

const NET_DELTA_FLEX: ColDef<Payslip> = {
  field: "net_delta",
  headerName: "Δ Thực lãnh",
  flex: 1,
  minWidth: 100,
  headerTooltip: `Chênh Thực lãnh so kỳ trước — đỏ nếu |Δ| ≥ ${NET_DELTA_WARN_THRESHOLD.toLocaleString("vi-VN")}đ`,
  valueFormatter: (p) => {
    if (p.value === null || p.value === undefined || p.value === "") return "—";
    const n = Number(p.value);
    if (Number.isNaN(n)) return String(p.value);
    const prefix = n > 0 ? "+" : "";
    return prefix + n.toLocaleString("vi-VN");
  },
  cellClass: deltaCellClass,
};

const COMPACT_COLS: ColDef<Payslip>[] = [
  {
    field: "gross",
    headerName: "Tổng thu nhập",
    flex: 1,
    minWidth: 108,
    valueFormatter: (p) => formatVnd(p.value),
  },
  NET_DELTA_FLEX,
  {
    field: "net",
    headerName: "Thực lãnh",
    flex: 1,
    minWidth: 108,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "status",
    headerName: "TT phiếu",
    width: 96,
    minWidth: 88,
    valueFormatter: (p) =>
      (
        {
          draft: "Nháp",
          published: "Đã PH",
          confirmed: "Đã XN",
          disputed: "Khiếu nại",
          locked: "Khóa",
        } as Record<string, string>
      )[String(p.value ?? "")] ?? String(p.value ?? "—"),
  },
];

const WORK_COLS: ColDef<Payslip>[] = [
  { field: "worked_days", headerName: "Công", width: 72 },
  { field: "al_days", headerName: "AL", width: 62 },
  { field: "rem_days", headerName: "REM", width: 68 },
  { field: "salary_divisor", headerName: "Mẫu số", width: 82 },
  {
    field: "wd_salary",
    headerName: "Lương ngày công",
    width: 128,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "ot_pay",
    headerName: "Tiền OT",
    width: 108,
    valueFormatter: (p) => formatVnd(p.value),
  },
];

const ALLOWANCE_COLS: ColDef<Payslip>[] = [
  {
    field: "allowance_total",
    headerName: "Phụ cấp",
    width: 112,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "other_adjustments",
    headerName: "Thưởng / Đ.chỉnh (+)",
    width: 130,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "gross",
    headerName: "Tổng thu nhập",
    width: 124,
    valueFormatter: (p) => formatVnd(p.value),
  },
];

const DEDUCTION_COLS: ColDef<Payslip>[] = [
  {
    field: "bhxh",
    headerName: "BHXH",
    width: 100,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "bhyt",
    headerName: "BHYT",
    width: 92,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "bhtn",
    headerName: "BHTN",
    width: 92,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "union_fee",
    headerName: "Công đoàn",
    width: 104,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "pit_amount",
    headerName: "TNCN",
    width: 100,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "other_deductions",
    headerName: "Khấu trừ khác",
    width: 118,
    valueFormatter: (p) => formatVnd(p.value),
  },
  {
    field: "taxable_income",
    headerName: "TN chịu thuế",
    width: 118,
    valueFormatter: (p) => formatVnd(p.value),
  },
];

const FULL_MIDDLE: ColDef<Payslip>[] = [
  { field: "pay_channel", headerName: "Kênh", width: 72 },
  ...WORK_COLS,
  ...ALLOWANCE_COLS.filter((c) => c.field !== "gross"),
  ...DEDUCTION_COLS,
  NET_DELTA,
  {
    field: "gross",
    headerName: "Tổng thu nhập",
    width: 124,
    valueFormatter: (p) => formatVnd(p.value),
  },
  { field: "confirm_deadline", headerName: "Hạn XN", width: 100, valueFormatter: (p) => formatDateDDMMYYYY(p.value) },
];

export function columnsForViewMode(mode: PayrollViewMode): ColDef<Payslip>[] {
  switch (mode) {
    case "work":
      return [
        ...PINNED_LEFT,
        ...WORK_COLS,
        ...COMPACT_COLS.filter((c) => c.field === "gross"),
        NET_DELTA,
        ...PINNED_RIGHT,
      ];
    case "allowance":
      return [...PINNED_LEFT, ...ALLOWANCE_COLS, NET_DELTA, ...PINNED_RIGHT];
    case "deduction":
      return [...PINNED_LEFT, ...DEDUCTION_COLS, NET_DELTA, ...PINNED_RIGHT];
    case "full":
      return [...PINNED_LEFT, ...FULL_MIDDLE, ...PINNED_RIGHT];
    case "compact":
    default:
      /* Không ghim — cột flex co giãn full khung, không còn vùng trống giữa. */
      return [...ID_COLS, ...COMPACT_COLS];
  }
}

/** Chế độ «Đầy đủ» cần cuộn ngang; các chế độ khác cố gắng vừa khung. */
export function payrollGridNeedsHorizontalScroll(mode: PayrollViewMode): boolean {
  return mode === "full";
}

export function sumPayslipField(rows: Payslip[], field: keyof Payslip): number {
  return rows.reduce((acc, r) => {
    const n = Number(r[field]);
    return acc + (Number.isNaN(n) ? 0 : n);
  }, 0);
}
