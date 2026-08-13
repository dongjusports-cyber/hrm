import { NavLink } from "react-router-dom";

/** Tab Quản trị — 23§23.4 / 5.6 + AI Gemini. */
const TABS = [
  { to: "/m/config/policy-package", label: "Gói chính sách" },
  { to: "/m/config/catalogs", label: "Danh mục" },
  { to: "/m/config/organization", label: "Tổ chức" },
  { to: "/m/config/integration", label: "Máy & tích hợp" },
  { to: "/m/config/permissions", label: "Phân quyền" },
  { to: "/m/config/journal", label: "Nhật ký" },
  { to: "/m/config/ai", label: "AI Gemini" },
];

export function ConfigTabNav() {
  return (
    <nav className="emp-subtabs config-admin-tabs" aria-label="Quản trị — tab Admin">
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          className={({ isActive }) => (isActive ? "emp-subtab active" : "emp-subtab")}
        >
          {t.label}
        </NavLink>
      ))}
    </nav>
  );
}
