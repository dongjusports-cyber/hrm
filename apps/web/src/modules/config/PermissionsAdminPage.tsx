import { ConfigTabNav } from "./ConfigTabNav";
import { UsersPage } from "./UsersPage";

/** Phân quyền — ma trận module + tài khoản (5.6 / 23§23.4). */
export function PermissionsAdminPage() {
  return (
    <div className="config-section-page">
      <ConfigTabNav />
      <h1>Phân quyền</h1>
      <p className="field-hint">
        Gán tối đa 7 module + quyền AI cho từng tài khoản. Vai trò Admin có toàn quyền Cấu Hình.
      </p>
      <UsersPage embedded />
    </div>
  );
}
