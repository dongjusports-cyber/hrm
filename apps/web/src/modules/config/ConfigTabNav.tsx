import { NavLink } from "react-router-dom";

/** 6 tab Quản trị theo 23§23.4 / 5.6. */
const TABS = [
  { to: "/m/config/policy-package", label: "Gói chính sách" },
  { to: "/m/config/catalogs", label: "Danh mục" },
  { to: "/m/config/organization", label: "Tổ chức" },
  { to: "/m/config/integration", label: "Máy & tích hợp" },
  { to: "/m/config/permissions", label: "Phân quyền" },
  { to: "/m/config/journal", label: "Nhật ký" },
];

export function ConfigTabNav() {
  return (
    <nav className="emp-subtabs config-admin-tabs" aria-label="Quản trị — 6 tab">
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
