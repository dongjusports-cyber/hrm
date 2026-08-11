import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  createUser,
  deactivateUser,
  fetchAssignableModules,
  fetchUsers,
  updateUser,
  type AssignableModule,
  type StaffUser,
} from "../../shared/api";

const emptyForm = {
  username: "",
  full_name: "",
  password: "",
  modules: [] as string[],
  ai_query: false,
  is_active: true,
  new_password: "",
};

export function UsersPage({ embedded = false }: { embedded?: boolean }) {
  const [users, setUsers] = useState<StaffUser[]>([]);
  const [catalog, setCatalog] = useState<AssignableModule[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);

  const assignable = useMemo(
    () => catalog.filter((m) => m.assignable_to_user),
    [catalog],
  );

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const [list, meta] = await Promise.all([fetchUsers(), fetchAssignableModules()]);
      setUsers(list);
      setCatalog(meta.modules);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được danh sách user.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  function startCreate() {
    setEditingId(null);
    setForm(emptyForm);
    setOk(null);
    setError(null);
  }

  function startEdit(u: StaffUser) {
    setEditingId(u.id);
    setForm({
      username: u.username,
      full_name: u.full_name,
      password: "",
      modules: u.modules.filter((k) => k !== "config"),
      ai_query: u.permissions.includes("ai_query"),
      is_active: u.is_active,
      new_password: "",
    });
    setOk(null);
    setError(null);
  }

  function toggleModule(key: string) {
    setForm((prev) => {
      const has = prev.modules.includes(key);
      if (has) {
        return { ...prev, modules: prev.modules.filter((k) => k !== key) };
      }
      if (prev.modules.length >= 7) {
        setError("Trợ Lý AI: user thường được gán tối đa 7 module.");
        return prev;
      }
      setError(null);
      return { ...prev, modules: [...prev.modules, key] };
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      const permissions = form.ai_query ? ["ai_query"] : [];
      if (editingId) {
        await updateUser(editingId, {
          full_name: form.full_name,
          is_active: form.is_active,
          modules: form.modules,
          permissions,
          new_password: form.new_password || undefined,
        });
        setOk("Đã cập nhật người dùng.");
      } else {
        if (!form.password) {
          setError("Trợ Lý AI: vui lòng nhập mật khẩu khi tạo user mới.");
          return;
        }
        await createUser({
          username: form.username,
          full_name: form.full_name,
          password: form.password,
          modules: form.modules,
          permissions,
          must_change_password: true,
        });
        setOk("Đã tạo người dùng mới.");
        startCreate();
      }
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại.");
    }
  }

  async function onDeactivate(u: StaffUser) {
    if (!confirm(`Vô hiệu hóa tài khoản ${u.username}?`)) return;
    try {
      await deactivateUser(u.id);
      setOk(`Đã vô hiệu hóa ${u.username}.`);
      await reload();
      if (editingId === u.id) startCreate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không vô hiệu hóa được.");
    }
  }

  return (
    <div className="users-page">
      <div className="users-head">
        <div>
          {!embedded && <h1>Người dùng & quyền</h1>}
          <p className="module-placeholder">
            Tạo tài khoản Web, gán tối đa 7 module. Ô Cấu Hình chỉ Admin.
          </p>
        </div>
        {!embedded && (
          <Link to="/m/config" className="btn-back">
            ← Cấu Hình
          </Link>
        )}
      </div>

      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      <div className="users-layout">
        <section className="users-list-card">
          <div className="users-list-toolbar">
            <h2>Danh sách</h2>
            <button type="button" className="btn-primary" onClick={startCreate}>
              + Người dùng mới
            </button>
          </div>
          {loading ? (
            <p>Đang tải…</p>
          ) : (
            <table className="users-table">
              <thead>
                <tr>
                  <th>Tên đăng nhập</th>
                  <th>Họ tên</th>
                  <th>Vai trò</th>
                  <th>Module</th>
                  <th>TT</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className={editingId === u.id ? "is-selected" : ""}>
                    <td>{u.username}</td>
                    <td>{u.full_name}</td>
                    <td>{u.role === "admin" ? "Admin" : "Người dùng"}</td>
                    <td>{u.role === "admin" ? "8/8" : `${u.modules.length}/7`}</td>
                    <td>{u.is_active ? "Đang bật" : "Tắt"}</td>
                    <td className="users-actions">
                      <button type="button" className="link-btn" onClick={() => startEdit(u)}>
                        Sửa
                      </button>
                      {u.role !== "admin" && u.is_active && (
                        <button type="button" className="link-btn danger" onClick={() => onDeactivate(u)}>
                          Tắt
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <form className="users-form-card" onSubmit={onSubmit}>
          <h2>{editingId ? "Sửa người dùng" : "Tạo người dùng"}</h2>

          {!editingId && (
            <label className="field">
              <span>Tên đăng nhập</span>
              <input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                required
                minLength={3}
              />
            </label>
          )}

          <label className="field">
            <span>Họ và tên</span>
            <input
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          </label>

          {!editingId ? (
            <label className="field">
              <span>Mật khẩu tạm</span>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
                minLength={8}
              />
            </label>
          ) : (
            <>
              <label className="field">
                <span>Mật khẩu mới (để trống nếu giữ nguyên)</span>
                <input
                  type="password"
                  value={form.new_password}
                  onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                  minLength={8}
                />
              </label>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                <span>Đang hoạt động</span>
              </label>
            </>
          )}

          <fieldset className="modules-fieldset">
            <legend>Module được phép (tối đa 7)</legend>
            {assignable.map((m) => (
              <label key={m.key} className="check-row">
                <input
                  type="checkbox"
                  checked={form.modules.includes(m.key)}
                  onChange={() => toggleModule(m.key)}
                  disabled={editingId !== null && users.find((u) => u.id === editingId)?.role === "admin"}
                />
                <span>{m.name}</span>
              </label>
            ))}
            <p className="field-hint">Ô Cấu Hình không gán cho user — chỉ Admin.</p>
          </fieldset>

          <label className="check-row">
            <input
              type="checkbox"
              checked={form.ai_query}
              onChange={(e) => setForm({ ...form, ai_query: e.target.checked })}
              disabled={editingId !== null && users.find((u) => u.id === editingId)?.role === "admin"}
            />
            <span>Quyền hỏi AI (`ai_query`)</span>
          </label>

          <button type="submit" className="btn-primary login-submit">
            {editingId ? "Lưu thay đổi" : "Tạo user"}
          </button>
        </form>
      </div>
    </div>
  );
}
