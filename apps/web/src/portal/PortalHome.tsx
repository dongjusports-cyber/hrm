import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchPortalTabs, type PortalTab } from "../shared/api";
import { clearAuth, useAuth } from "../shared/authStore";
import { showDenied } from "../shared/deniedStore";
import { navigateSmooth } from "../shared/navigateSmooth";
import { getPinnedScreens, type PinnedScreen } from "../shared/pinnedScreens";
import { SlideOverPanel } from "../shared/SlideOverPanel";
import { TabIcon } from "./tabIcons";

const TABS_CACHE_KEY = "djhrm.portalTabs";

const TILE_ACCENT: Record<string, string> = {
  overview: "blue",
  hr: "rose",
  timekeeping: "emerald",
  payroll: "amber",
  insurance: "cyan",
  report: "violet",
  dispute: "orange",
  config: "slate",
};

function readCachedTabs(): PortalTab[] {
  try {
    const raw = sessionStorage.getItem(TABS_CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as PortalTab[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Portal Lv1 — nền tím nhạt (hiện tại).
 * Backup nền đen: themes/Module-Menu-V1.0.css
 */
export function PortalHome() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [tabs, setTabs] = useState<PortalTab[]>(() => readCachedTabs());
  const [pinned, setPinned] = useState<PinnedScreen[]>(() => getPinnedScreens());
  const [error, setError] = useState<string | null>(null);
  /** Khay HUD — mở bằng `window.dispatchEvent(new Event("djhrm:open-hud"))`. */
  const [hudOpen, setHudOpen] = useState(false);

  useEffect(() => {
    const openHud = () => setHudOpen(true);
    const onPinned = () => setPinned(getPinnedScreens());
    window.addEventListener("djhrm:open-hud", openHud);
    window.addEventListener("djhrm:pinned-changed", onPinned);
    return () => {
      window.removeEventListener("djhrm:open-hud", openHud);
      window.removeEventListener("djhrm:pinned-changed", onPinned);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchPortalTabs();
        if (cancelled) return;
        setTabs(data.tabs);
        sessionStorage.setItem(TABS_CACHE_KEY, JSON.stringify(data.tabs));
        setError(null);
      } catch (e) {
        if (!cancelled && tabs.length === 0) {
          setError(e instanceof Error ? e.message : "Không tải được portal.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onTileClick(tab: PortalTab) {
    const fullName = user?.full_name ?? "bạn";
    if (!tab.allowed) {
      showDenied(fullName);
      return;
    }
    navigateSmooth(navigate, `/m/${tab.key}`);
  }

  function logout() {
    clearAuth();
    sessionStorage.removeItem(TABS_CACHE_KEY);
    navigate("/login", { replace: true });
  }

  return (
    <div className="portal-page portal-titan">
      <header className="portal-header">
        <div className="brand">
          <img
            className="brand-mark"
            src="/dj-logo.png"
            alt="DJ"
            width={64}
            height={32}
          />
          <div>
            <h1>DJ HRM</h1>
            <p className="brand-sub">DONGJU Sports Việt Nam</p>
          </div>
        </div>
        <div className="header-right">
          <p className="greeting">
            Xin chào, <strong>{user?.full_name ?? "…"}</strong>
          </p>
          <button type="button" className="btn-ghost portal-btn-ghost" onClick={logout}>
            Đăng xuất
          </button>
        </div>
      </header>

      {error && <p className="banner-warn">{error}</p>}

      {pinned.length > 0 && (
        <section className="portal-section" aria-label="Màn đã ghim">
          <h2 className="portal-section-title">Màn đã ghim</h2>
          <div className="portal-grid hr-hub-grid">
            {pinned.map((p) => (
              <Link key={p.href} to={p.href} className="portal-tile portal-bento-tile tile-slate">
                <span className="tile-name">{p.label}</span>
                <span className="tile-desc">Ctrl+K để bỏ ghim</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {tabs.length === 0 ? (
        <p className="portal-loading">Đang tải chức năng…</p>
      ) : (
        <main className="portal-grid portal-bento" aria-label="Danh sách chức năng">
          {tabs.map((tab) => {
            const accent = TILE_ACCENT[tab.key] ?? "slate";
            const locked = !tab.allowed;
            return (
              <button
                key={tab.key}
                type="button"
                className={`portal-tile portal-bento-tile tile-${accent}${locked ? " is-locked" : ""}`}
                onClick={() => onTileClick(tab)}
                aria-label={locked ? `${tab.name} — không có quyền` : tab.name}
                aria-disabled={locked}
              >
                <span className="tile-icon" aria-hidden>
                  <TabIcon moduleKey={tab.key} />
                </span>
                <span className="tile-name">{tab.name}</span>
                <span className="tile-desc">{tab.description}</span>
              </button>
            );
          })}
        </main>
      )}

      <footer className="portal-creator" aria-label="Tác giả">
        <p className="portal-creator-label">Designed &amp; Built by</p>
        <p className="portal-creator-name">NGUYỄN THANH THIỆN</p>
        <div className="portal-creator-meta">
          <span>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M6.5 4.5h3l1.5 4-2 1.5a12 12 0 006 6l1.5-2 4 1.5v3A2 2 0 0119 20 15 15 0 014.5 5.5a2 2 0 012-2z"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinejoin="round"
              />
            </svg>
            0918 283 825
          </span>
          <span>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M12 21s7-5.5 7-12a7 7 0 10-14 0c0 6.5 7 12 7 12z"
                stroke="currentColor"
                strokeWidth="1.75"
              />
              <circle cx="12" cy="9" r="2.2" stroke="currentColor" strokeWidth="1.75" />
            </svg>
            Vietnam
          </span>
        </div>
      </footer>

      <SlideOverPanel
        open={hudOpen}
        title="Chi tiết nhân sự"
        onClose={() => setHudOpen(false)}
      >
        <div className="hud-panel">
          <p className="field-hint">
            Khay trượt tra cứu NV — mở hồ sơ nhanh mà không rời Portal. Hiện dùng bảng lệnh và
            danh sách HR.
          </p>
          <div className="hud-panel-actions">
            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={() => {
                setHudOpen(false);
                navigate("/m/hr/lists/all");
              }}
            >
              Danh sách nhân viên
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                setHudOpen(false);
                window.dispatchEvent(new Event("djhrm:open-cmdk"));
              }}
            >
              Bảng lệnh (Ctrl+K)
            </button>
          </div>
          <ul className="hud-panel-tips">
            <li>Gõ MSNV hoặc họ tên trong bảng lệnh để mở hồ sơ.</li>
            <li>Trên danh sách HR: double-click dòng hoặc bấm <strong>Xem</strong>.</li>
            <li>Tra cứu đầy đủ trong khay này sẽ bổ sung ở phiên sau.</li>
          </ul>
        </div>
      </SlideOverPanel>
    </div>
  );
}
