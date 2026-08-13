import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  askAi,
  fetchMyAlerts,
  fetchTodos,
  markAlertRead,
  markAllAlertsRead,
  type AiAlert,
  type TodoCard,
} from "./api";
import { aiFabBadgeCount } from "./aiReminder";
import {
  clampFabPosition,
  clearFabPosition,
  computePanelBox,
  defaultFabPosition,
  loadFabPosition,
  nudgeFabFromGrid,
  saveFabPosition,
} from "./aiFabPosition";
import { useAuth } from "./authStore";
import { useEscLayer } from "./useEscLayer";

type Tab = "alerts" | "chat";

const FAB_SIZE = 56;

/**
 * Trợ Lý AI — Lớp A badge + Lớp B Hỏi AI.
 * Nút kéo thả độc lập; panel fixed trong khung màn (đóng/kéo được ở mọi góc).
 */
export function AiFab() {
  const { accessToken, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const dragRef = useRef<{
    startX: number;
    startY: number;
    originLeft: number;
    originTop: number;
    moved: boolean;
  } | null>(null);
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("alerts");
  const [unread, setUnread] = useState(0);
  const [alerts, setAlerts] = useState<AiAlert[]>([]);
  const [todos, setTodos] = useState<TodoCard[]>([]);
  const [pos, setPos] = useState(() =>
    typeof window !== "undefined"
      ? loadFabPosition(window.innerWidth, window.innerHeight)
      : defaultFabPosition(1280, 720),
  );
  const [viewport, setViewport] = useState(() =>
    typeof window !== "undefined"
      ? { w: window.innerWidth, h: window.innerHeight }
      : { w: 1280, h: 720 },
  );
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [chatAnswer, setChatAnswer] = useState<string | null>(null);
  const [chatMeta, setChatMeta] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  const onWorker = location.pathname.startsWith("/worker");
  const onLogin = location.pathname === "/login" || location.pathname === "/worker/login";
  const canQuery = Boolean(user?.permissions?.includes("ai_query") || user?.role === "admin");

  const reload = useCallback(async () => {
    if (!accessToken) return;
    try {
      const [alertData, todoData] = await Promise.all([fetchMyAlerts(false), fetchTodos()]);
      setUnread(alertData.unread_count);
      setAlerts(alertData.alerts);
      setTodos(todoData.cards);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải nhắc việc.");
    }
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken || onWorker || onLogin) return;
    void reload();
    const t = window.setInterval(() => void reload(), 60_000);
    return () => window.clearInterval(t);
  }, [accessToken, onWorker, onLogin, reload]);

  useEffect(() => {
    saveFabPosition(pos);
  }, [pos]);

  useEffect(() => {
    function onResize() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      setViewport({ w, h });
      setPos((p) => clampFabPosition(p.left, p.top, w, h, FAB_SIZE));
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEscLayer(open, () => setOpen(false));

  const panelBox = useMemo(
    () => computePanelBox(pos, viewport.w, viewport.h, { fabSize: FAB_SIZE }),
    [pos, viewport.w, viewport.h],
  );

  if (!accessToken || onWorker || onLogin) return null;

  const badge = aiFabBadgeCount(unread, todos.length);

  async function onRead(id: string) {
    await markAlertRead(id);
    await reload();
  }

  async function onReadAll() {
    await markAllAlertsRead();
    await reload();
  }

  function openHref(href: string) {
    setOpen(false);
    navigate(href);
  }

  function openModule(moduleKey: string) {
    setOpen(false);
    navigate(`/m/${moduleKey}`);
  }

  async function onAsk(e: FormEvent) {
    e.preventDefault();
    if (!canQuery || asking || !chatInput.trim()) return;
    setAsking(true);
    setError(null);
    try {
      const res = await askAi(chatInput.trim());
      setChatAnswer(res.answer);
      setChatMeta(`${res.message}${res.stub ? " (stub — chưa gọi Gemini thật)" : ""}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không hỏi được AI.");
    } finally {
      setAsking(false);
    }
  }

  function onFabPointerDown(e: ReactPointerEvent<HTMLButtonElement>) {
    if (e.button !== 0) return;
    e.preventDefault();
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      originLeft: pos.left,
      originTop: pos.top,
      moved: false,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(false);
  }

  function onFabPointerMove(e: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < 6) return;
    drag.moved = true;
    setDragging(true);
    setPos(
      clampFabPosition(
        drag.originLeft + dx,
        drag.originTop + dy,
        window.innerWidth,
        window.innerHeight,
        FAB_SIZE,
      ),
    );
  }

  function resetFabPosition() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    clearFabPosition();
    setPos(defaultFabPosition(w, h));
  }

  function onFabPointerUp(e: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    const wasDrag = Boolean(drag?.moved);
    dragRef.current = null;
    setDragging(false);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* already released */
    }
    if (wasDrag) {
      setPos((p) => nudgeFabFromGrid(p, window.innerWidth, window.innerHeight, FAB_SIZE));
      return;
    }
    setOpen((v) => {
      const next = !v;
      if (next) {
        setPos((p) => nudgeFabFromGrid(p, window.innerWidth, window.innerHeight, FAB_SIZE));
      }
      return next;
    });
    void reload();
  }

  return (
    <>
      {open && (
        <div
          className="ai-fab-panel"
          role="dialog"
          aria-label="Trợ Lý AI"
          style={{
            left: panelBox.left,
            top: panelBox.top,
            width: panelBox.width,
            maxHeight: panelBox.maxHeight,
          }}
        >
          <header className="ai-fab-panel-head">
            <div>
              <strong>Trợ Lý AI</strong>
              <p>Xin chào, {user?.full_name ?? "bạn"}.</p>
            </div>
            <button
              type="button"
              className="ai-fab-close"
              aria-label="Đóng"
              onClick={() => setOpen(false)}
            >
              ×
            </button>
          </header>

          <div className="ai-fab-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              className={tab === "alerts" ? "is-active" : ""}
              aria-selected={tab === "alerts"}
              onClick={() => setTab("alerts")}
            >
              Việc cần làm
            </button>
            {canQuery && (
              <button
                type="button"
                role="tab"
                className={tab === "chat" ? "is-active" : ""}
                aria-selected={tab === "chat"}
                onClick={() => setTab("chat")}
              >
                Hỏi AI
              </button>
            )}
          </div>

          {error && <p className="banner-warn">{error}</p>}

          {tab === "alerts" ? (
            <>
              <div className="ai-fab-actions">
                <button type="button" className="link-btn" onClick={() => void reload()}>
                  Làm mới
                </button>
                {unread > 0 && (
                  <button type="button" className="link-btn" onClick={() => void onReadAll()}>
                    Đánh dấu đã đọc hết
                  </button>
                )}
              </div>
              {alerts.length === 0 && todos.length === 0 ? (
                <p className="field-hint">Không có nhắc việc (0 token).</p>
              ) : (
                <ul className="ai-fab-list">
                  {todos.map((card) => (
                    <li key={card.key} className="is-unread">
                      <button type="button" className="ai-fab-item" onClick={() => openHref(card.href)}>
                        <strong>
                          {card.title}
                          {card.count > 0 ? ` (${card.count})` : ""}
                        </strong>
                        <span>{card.body}</span>
                      </button>
                    </li>
                  ))}
                  {alerts.map((a) => (
                    <li key={a.id} className={a.is_read ? "is-read" : "is-unread"}>
                      <button
                        type="button"
                        className="ai-fab-item"
                        onClick={() => {
                          void onRead(a.id);
                          openModule(a.target_module || "timekeeping");
                        }}
                      >
                        <strong>{a.title}</strong>
                        <span>{a.body}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <form className="ai-fab-chat" onSubmit={(e) => void onAsk(e)}>
              <p className="field-hint">
                Chỉ phân tích / đề xuất (read-only). Không tự sửa lương hay đóng khiếu nại.
              </p>
              <textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                rows={3}
                maxLength={4000}
                placeholder="Ví dụ: Thông tin MSNV 1519 · Rà soát khiếu nại OT…"
                disabled={asking}
              />
              <button type="submit" className="btn-primary" disabled={asking || !chatInput.trim()}>
                {asking ? "Đang hỏi…" : "Gửi"}
              </button>
              {chatMeta && <p className="field-hint">{chatMeta}</p>}
              {chatAnswer && <pre className="ai-fab-answer">{chatAnswer}</pre>}
            </form>
          )}
        </div>
      )}

      <div
        className="ai-fab-root"
        style={{ left: pos.left, top: pos.top, right: "auto", bottom: "auto" }}
      >
        <button
          type="button"
          className="ai-fab-reset"
          aria-label="Đặt lại vị trí nút Trợ Lý AI"
          title="Đặt lại vị trí"
          onClick={resetFabPosition}
        >
          ↺
        </button>
        <button
          type="button"
          className={`ai-fab-btn${dragging ? " is-dragging" : ""}`}
          aria-label="Trợ Lý AI — kéo để di chuyển, bấm để mở"
          onPointerDown={onFabPointerDown}
          onPointerMove={onFabPointerMove}
          onPointerUp={onFabPointerUp}
          onPointerCancel={onFabPointerUp}
        >
          <span>AI</span>
          {badge > 0 && <span className="ai-fab-badge">{badge > 99 ? "99+" : badge}</span>}
        </button>
      </div>
    </>
  );
}
