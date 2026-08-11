import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchConfigTabs,
  resetConfigTabs,
  saveConfigTabs,
  type ConfigPortalTab,
} from "../../shared/api";

/** Cấu Hình → Portal Tabs — đổi tên / thứ tự / bật-tắt (02§2.4, 08). */
export function PortalTabsPage() {
  const [tabs, setTabs] = useState<ConfigPortalTab[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      setTabs(await fetchConfigTabs());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải ô Portal.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  function patch(key: string, patch: Partial<ConfigPortalTab>) {
    setTabs((prev) => prev.map((t) => (t.key === key ? { ...t, ...patch } : t)));
  }

  function move(key: string, dir: -1 | 1) {
    setTabs((prev) => {
      const sorted = [...prev].sort((a, b) => a.sort_order - b.sort_order);
      const idx = sorted.findIndex((t) => t.key === key);
      const j = idx + dir;
      if (idx < 0 || j < 0 || j >= sorted.length) return prev;
      const a = sorted[idx];
      const b = sorted[j];
      const orderA = a.sort_order;
      const orderB = b.sort_order;
      return prev.map((t) => {
        if (t.key === a.key) return { ...t, sort_order: orderB };
        if (t.key === b.key) return { ...t, sort_order: orderA };
        return t;
      });
    });
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const saved = await saveConfigTabs(
        tabs.map((t) => ({
          key: t.key,
          name: t.name,
          description: t.description,
          sort_order: t.sort_order,
          enabled: t.enabled,
        })),
      );
      setTabs(saved);
      setOk("Đã lưu ô Portal. Về Portal để xem thứ tự/tên mới.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được.");
    } finally {
      setBusy(false);
    }
  }

  async function onReset() {
    if (!window.confirm("Khôi phục tên và thứ tự mặc định Hiến pháp?")) return;
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      setTabs(await resetConfigTabs());
      setOk("Đã khôi phục seed mặc định.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không khôi phục được.");
    } finally {
      setBusy(false);
    }
  }

  const sorted = [...tabs].sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="module-page">
      <header className="module-header">
        <Link to="/m/config" className="btn-back">
          ← Cấu Hình
        </Link>
        <nav className="breadcrumb">
          <Link to="/">Portal</Link>
          <span aria-hidden> › </span>
          <Link to="/m/config">Cấu Hình</Link>
          <span aria-hidden> › </span>
          <span>Ô Portal</span>
        </nav>
      </header>
      <main className="module-body">
        <h1>Ô Portal</h1>
        <p className="field-hint">
          Đổi tên, mô tả, thứ tự, bật/tắt 8 ô Lv1. Không thêm/xóa mã module (cố định). Ô Cấu Hình
          không tắt được.
        </p>
        {error && <p className="banner-warn">{error}</p>}
        {ok && <p className="banner-ok">{ok}</p>}
        {loading ? (
          <p className="field-hint">Đang tải…</p>
        ) : (
          <form onSubmit={(e) => void onSave(e)}>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Thứ tự</th>
                  <th>Mã</th>
                  <th>Tên hiển thị</th>
                  <th>Mô tả</th>
                  <th>Bật</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((t) => (
                  <tr key={t.key}>
                    <td>{t.sort_order}</td>
                    <td>
                      <code>{t.key}</code>
                      {t.is_system && <span className="field-hint"> system</span>}
                    </td>
                    <td>
                      <input
                        value={t.name}
                        onChange={(e) => patch(t.key, { name: e.target.value })}
                        required
                        disabled={busy}
                      />
                    </td>
                    <td>
                      <input
                        value={t.description}
                        onChange={(e) => patch(t.key, { description: e.target.value })}
                        disabled={busy}
                      />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={t.enabled}
                        disabled={busy || t.is_system}
                        onChange={(e) => patch(t.key, { enabled: e.target.checked })}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="link-btn"
                        disabled={busy}
                        onClick={() => move(t.key, -1)}
                      >
                        ↑
                      </button>{" "}
                      <button
                        type="button"
                        className="link-btn"
                        disabled={busy}
                        onClick={() => move(t.key, 1)}
                      >
                        ↓
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="calendar-row" style={{ marginTop: 16 }}>
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? "Đang lưu…" : "Lưu"}
              </button>
              <button
                type="button"
                className="btn-ghost-dark"
                disabled={busy}
                onClick={() => void onReset()}
              >
                Khôi phục mặc định
              </button>
              <button
                type="button"
                className="btn-ghost-dark"
                disabled={busy}
                onClick={() => void reload()}
              >
                Làm mới
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}
