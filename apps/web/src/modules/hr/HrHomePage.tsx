import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  fetchEmployees,
  fetchViolationBoard,
  type Employee,
} from "../../shared/api";
import { navigateSmooth } from "../../shared/navigateSmooth";
import { EmployeeCreateSheet } from "./EmployeeCreateSheet";

const EMP_CACHE = "djhrm.hrEmployeesCache";

type HubTile = {
  key: string;
  name: string;
  description: string;
  to: string;
  countKey?: "employees" | "violations" | "none";
  countFn?: (rows: Employee[]) => number;
};

/** Trạng thái làm việc suy ra — khớp filter API tab Thử việc / Thai sản / Chính thức. */
function empEffectiveStatus(e: Employee): string {
  return e.effective_status ?? e.status;
}

const TILES: HubTile[] = [
  {
    key: "all",
    name: "Tất cả nhân viên",
    description: "Toàn bộ hồ sơ trong hệ thống",
    to: "/m/hr/lists/all",
    countKey: "employees",
    countFn: (r) => r.length,
  },
  {
    key: "active",
    name: "Chính thức",
    description: "Đã ký hợp đồng chính thức",
    to: "/m/hr/lists/active",
    countKey: "employees",
    countFn: (r) => r.filter((e) => empEffectiveStatus(e) === "active").length,
  },
  {
    key: "probation",
    name: "Thử việc",
    description: "Đang trong thời gian thử việc",
    to: "/m/hr/lists/probation",
    countKey: "employees",
    countFn: (r) => r.filter((e) => empEffectiveStatus(e) === "probation").length,
  },
  {
    key: "maternity",
    name: "Thai sản",
    description: "Nhân viên nghỉ thai sản",
    to: "/m/hr/lists/maternity",
    countKey: "employees",
    countFn: (r) => r.filter((e) => empEffectiveStatus(e) === "maternity").length,
  },
  {
    key: "new",
    name: "Tạo nhân viên mới",
    description: "Nhập tối thiểu — overlay full màn hình",
    to: "/m/hr",
    countKey: "none",
  },
  {
    key: "raise",
    name: "Tăng lương",
    description: "Tăng theo bộ phận hoặc toàn công ty",
    to: "/m/hr/salary-raise",
    countKey: "none",
  },
  {
    key: "contracts",
    name: "Hợp đồng lao động",
    description: "HĐ sắp hết hạn · ký HĐ tiếp · dòng thời gian",
    to: "/m/hr/contracts",
    countKey: "none",
  },
  {
    key: "movements",
    name: "Biến động",
    description: "Chuyển tổ · lương · vi phạm — một lưới",
    to: "/m/hr/movements",
    countKey: "none",
  },
  {
    key: "resignation",
    name: "Thủ tục thôi việc",
    description: "Wizard 3 bước — nghỉ việc & trợ cấp",
    to: "/m/hr/resignation",
    countKey: "none",
  },
  {
    key: "resigned",
    name: "Thôi việc",
    description: "Đã nghỉ / thôi việc",
    to: "/m/hr/lists/resigned",
    countKey: "employees",
    countFn: (r) => r.filter((e) => e.status === "resigned").length,
  },
  {
    key: "violations",
    name: "Vi phạm",
    description: "Nhân viên có biên bản / kỷ luật",
    to: "/m/hr/violations",
    countKey: "violations",
  },
  {
    key: "qr",
    name: "Mã QR công nhân",
    description: "Xuất / in QR đăng nhập Worker",
    to: "/admin/qr-code",
    countKey: "none",
  },
];

/** Nhân Sự Lv2 — ô lớn như Portal; bấm → full màn chức năng. */
export function HrHomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [showCreate, setShowCreate] = useState(false);
  const [rows, setRows] = useState<Employee[]>(() => {
    try {
      const raw = sessionStorage.getItem(EMP_CACHE);
      return raw ? (JSON.parse(raw) as Employee[]) : [];
    } catch {
      return [];
    }
  });
  const [violationPeople, setViolationPeople] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const st = location.state as { openCreate?: boolean } | null;
    if (st?.openCreate) {
      setShowCreate(true);
      navigate("/m/hr", { replace: true, state: {} });
    }
  }, [location.state, navigate]);

  useEffect(() => {
    let cancelled = false;
    void fetchEmployees()
      .then((list) => {
        if (cancelled) return;
        setRows(list);
        sessionStorage.setItem(EMP_CACHE, JSON.stringify(list));
      })
      .catch((e: unknown) => {
        if (!cancelled && rows.length === 0) {
          setError(e instanceof Error ? e.message : "Không tải được nhân sự.");
        }
      });
    void fetchViolationBoard()
      .then((list) => {
        if (!cancelled) setViolationPeople(list.length);
      })
      .catch(() => {
        /* đếm phụ — không chặn hub */
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function tileCount(tile: HubTile): number | null {
    if (tile.countKey === "violations") return violationPeople;
    if (tile.countKey === "employees" && tile.countFn) return tile.countFn(rows);
    return null;
  }

  return (
    <div className="hr-hub">
      <div className="hr-hub-head">
        <h1>Nhân Sự</h1>
        <p className="field-hint">
          Tạo NV tại ô «Tạo nhân viên mới» · trong danh sách bấm <strong>tên</strong> để mở hồ sơ full màn.
        </p>
      </div>
      {error && <p className="banner-warn">{error}</p>}
      <div className="portal-grid hr-hub-grid" aria-label="Chức năng nhân sự">
        {TILES.map((tile) => {
          const n = tileCount(tile);
          return (
            <button
              key={tile.key}
              type="button"
              className="portal-tile"
              onClick={() => {
                if (tile.key === "new") setShowCreate(true);
                else navigateSmooth(navigate, tile.to);
              }}
            >
              <span className="tile-name">{tile.name}</span>
              {n !== null && <span className="hr-hub-count">{n}</span>}
              <span className="tile-desc">{tile.description}</span>
            </button>
          );
        })}
      </div>

      <EmployeeCreateSheet
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(emp) => {
          setShowCreate(false);
          void fetchEmployees()
            .then((list) => {
              setRows(list);
              sessionStorage.setItem(EMP_CACHE, JSON.stringify(list));
            })
            .catch(() => {});
          navigate(`/m/hr/lists/all`, {
            state: { openProfileId: emp.id },
          });
        }}
      />
    </div>
  );
}
