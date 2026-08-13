import { useNavigate } from "react-router-dom";
import { ConfigTabNav } from "./ConfigTabNav";

const ADMIN_TILES = [
  {
    key: "policy-package",
    name: "Gói chính sách",
    description: "6 tab con BH · chuyên cần · phép · OT · phụ cấp · lịch",
  },
  {
    key: "catalogs",
    name: "Danh mục",
    description: "Loại nghỉ · khoản lương · chức vụ · lookup hồ sơ",
  },
  {
    key: "organization",
    name: "Tổ chức",
    description: "Bộ phận · tổ · chức vụ · công việc",
  },
  {
    key: "integration",
    name: "Máy & tích hợp",
    description: "Mitapro · sync · QR công nhân",
  },
  {
    key: "permissions",
    name: "Phân quyền",
    description: "Module × tài khoản · mật khẩu",
  },
  {
    key: "journal",
    name: "Nhật ký",
    description: "Audit · policy · sync_jobs hợp nhất",
  },
  {
    key: "ai",
    name: "AI Gemini",
    description: "Model Gemini · API key · hạn mức hỏi/ngày",
  },
];

/** Cấu Hình Lv2 — 6 tab Quản trị theo 23§23.4 (5.6). */
export function ConfigHome() {
  const navigate = useNavigate();

  return (
    <div className="config-home">
      <ConfigTabNav />
      <h1>Quản trị hệ thống</h1>
      <p className="module-placeholder">Chọn tab Admin (chỉ tài khoản Admin).</p>

      <div className="config-grid" aria-label="Quản trị — tab Admin">
        {ADMIN_TILES.map((section) => (
          <button
            key={section.key}
            type="button"
            className="config-tile"
            onClick={() => navigate(`/m/config/${section.key}`)}
          >
            <span className="tile-name">{section.name}</span>
            <span className="tile-desc">{section.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
