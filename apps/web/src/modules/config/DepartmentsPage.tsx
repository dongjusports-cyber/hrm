import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createDepartment,
  deleteDepartment,
  fetchDepartments,
  updateDepartment,
  type Department,
} from "../../shared/api";
import { labelDeptCategory } from "../../shared/viLabels";

const CATEGORIES = [
  { value: "direct", label: "Trực tiếp" },
  { value: "prod_indirect", label: "Gián tiếp SX" },
  { value: "admin_indirect", label: "Gián tiếp hành chính" },
];

/** Cấu Hình → Bộ phận — chỉ Admin (thêm / sửa / xóa). */
export function DepartmentsPage() {
  const [rows, setRows] = useState<Department[]>([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("direct");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function reload() {
    setRows(await fetchDepartments());
  }

  useEffect(() => {
    void reload().catch((e: unknown) => {
      setError(e instanceof Error ? e.message : "Không tải bộ phận.");
    });
  }, []);

  function startEdit(d: Department) {
    setEditingId(d.id);
    setCode(d.code);
    setName(d.name);
    setCategory(d.category);
    setOk(null);
    setError(null);
  }

  function resetForm() {
    setEditingId(null);
    setCode("");
    setName("");
    setCategory("direct");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      if (editingId) {
        await updateDepartment(editingId, { name, category });
        setOk("Đã cập nhật bộ phận.");
      } else {
        await createDepartment({ code, name: name || code, category });
        setOk("Đã thêm bộ phận.");
      }
      resetForm();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    }
  }

  async function onDelete(d: Department) {
    if (!window.confirm(`Xóa bộ phận ${d.code} — ${d.name}?`)) return;
    setError(null);
    setOk(null);
    try {
      await deleteDepartment(d.id);
      setOk(`Đã xóa ${d.code}.`);
      if (editingId === d.id) resetForm();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xóa được.");
    }
  }

  return (
    <div className="config-section-page">
      <p className="field-hint">
        <Link to="/m/config" className="hr-layer-btn">
          ← Cấu Hình
        </Link>
      </p>
      <h1>Bộ phận</h1>
      <p className="field-hint">
        Chỉ Admin thêm / đổi tên / xóa. Nhân Sự chỉ chọn bộ phận khi gán NV — không tự tạo danh
        mục.
      </p>
      {error && <p className="banner-warn">{error}</p>}
      {ok && <p className="banner-ok">{ok}</p>}

      <div className="hr-split">
        <div className="users-form-card">
          <h2>Danh mục ({rows.length})</h2>
          <table className="users-table">
            <thead>
              <tr>
                <th>Mã</th>
                <th>Tên</th>
                <th>Loại</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id}>
                  <td>
                    <strong>{d.code}</strong>
                  </td>
                  <td>{d.name}</td>
                  <td>{labelDeptCategory(d.category)}</td>
                  <td className="dept-actions">
                    <button type="button" className="btn-ghost-dark" onClick={() => startEdit(d)}>
                      Sửa
                    </button>
                    <button type="button" className="btn-ghost-dark" onClick={() => void onDelete(d)}>
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form className="users-form-card" onSubmit={(ev) => void onSubmit(ev)}>
          <h2>{editingId ? `Sửa · ${code}` : "Thêm bộ phận"}</h2>
          {!editingId && (
            <label className="field">
              <span>Mã</span>
              <input value={code} onChange={(e) => setCode(e.target.value)} required />
            </label>
          )}
          <label className="field">
            <span>Tên</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="field">
            <span>Phân loại KPI</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <div className="hr-dept-row">
            <button type="submit" className="btn-primary">
              {editingId ? "Lưu" : "Thêm"}
            </button>
            {editingId && (
              <button type="button" className="btn-ghost-dark" onClick={resetForm}>
                Hủy
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
