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
  askAiAssist,
  downloadApiHref,
  fetchAiInbox,
  markAlertRead,
  markAllAlertsRead,
  type AiAlert,
  type AiSuggestion,
  type TodoCard,
} from "./api";
import { isTimesheetExportHref } from "./timesheetUrl";
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
import { speechBlockReason, startSpeechSession, type SpeechSession } from "./speechToText";

type Tab = "alerts" | "chat";

const FAB_SIZE = 56;

const DEFAULT_CHIPS: AiSuggestion[] = [
  { label: "Tóm tắt hôm nay", message: "Tóm tắt việc cần làm hôm nay" },
  { label: "Mở bảng công", message: "Mở bảng công cả công ty" },
  { label: "In bảng công", message: "In bảng công cả công ty" },
  { label: "Lẻ hôm qua", message: "Lọc và mở ds nhân viên lẻ hôm qua" },
  { label: "Ai chấm lẻ?", message: "Ai chấm lẻ tháng này" },
  { label: "Đơn phép?", message: "Đơn phép chờ duyệt" },
];

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
  const [todoTotal, setTodoTotal] = useState(0);
  const [alerts, setAlerts] = useState<AiAlert[]>([]);
  const [todos, setTodos] = useState<TodoCard[]>([]);
  const [suggestions, setSuggestions] = useState<AiSuggestion[]>([]);
  const [followups, setFollowups] = useState<AiSuggestion[]>([]);
  const [thread, setThread] = useState<{ q: string; a: string }[]>([]);
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
  const [listening, setListening] = useState(false);
  const speechRef = useRef<SpeechSession | null>(null);
  const sendMessageRef = useRef<(text: string) => Promise<void>>(async () => undefined);

  const onWorker = location.pathname.startsWith("/worker");
  const onLogin = location.pathname === "/login" || location.pathname === "/worker/login";
  const canQuery = Boolean(user?.permissions?.includes("ai_query") || user?.role === "admin");
  const canAssist = Boolean(
    canQuery ||
      user?.modules?.includes("hr") ||
      user?.modules?.includes("timekeeping") ||
      user?.modules?.includes("payroll"),
  );

  const reload = useCallback(
    async (light: boolean) => {
      if (!accessToken) return;
      try {
        const data = await fetchAiInbox(light);
        setUnread(data.unread_count);
        setTodoTotal(data.todo_total);
        if (!data.light) {
          setAlerts(data.alerts);
          setTodos(data.cards);
          setSuggestions(data.suggestions);
        }
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không tải nhắc việc.");
      }
    },
    [accessToken],
  );

  useEffect(() => {
    if (!accessToken || onWorker || onLogin) return;
    void reload(true);
    const t = window.setInterval(() => void reload(true), 60_000);
    return () => window.clearInterval(t);
  }, [accessToken, onWorker, onLogin, reload]);

  useEffect(() => {
    if (!open || !accessToken || onWorker || onLogin) return;
    void reload(false);
  }, [open, accessToken, onWorker, onLogin, reload]);

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

  useEffect(() => {
    if (open) return;
    speechRef.current?.stop();
    speechRef.current = null;
    setListening(false);
  }, [open]);

  useEffect(
    () => () => {
      speechRef.current?.stop();
    },
    [],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!canAssist || asking || !text.trim()) return;
      const q = text.trim();
      setAsking(true);
      setError(null);
      try {
        const res = canQuery ? await askAi(q) : await askAiAssist(q);
        setChatAnswer(res.answer);
        setChatMeta(res.message);
        setFollowups(res.suggestions ?? []);
        setThread((prev) => [...prev.slice(-2), { q, a: res.answer }]);
        if (res.kind === "timesheet_open" || res.kind === "punch_review") {
          const sugg = res.suggestions ?? [];
          const file = sugg.find((s) => isTimesheetExportHref(s.href));
          const pages = sugg.filter((s) => (s.href || "").startsWith("/m/"));
          if (file?.href) {
            try {
              await downloadApiHref(file.href);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Không tải Excel bảng công.");
              return;
            }
          }
          const punchPage = pages.find(
            (s) => (s.href || "").includes("date=") || (s.href || "").includes("odd="),
          );
          const openPage =
            res.kind === "timesheet_open" && pages.length === 1
              ? pages[0]
              : punchPage;
          if (openPage?.href) {
            setOpen(false);
            navigate(openPage.href);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Không hỏi được AI.");
      } finally {
        setAsking(false);
      }
    },
    [canAssist, canQuery, asking, navigate],
  );
  sendMessageRef.current = sendMessage;

  const panelBox = useMemo(() => {
    const phone = viewport.w < 640;
    const chat = tab === "chat";
    return computePanelBox(pos, viewport.w, viewport.h, {
      fabSize: FAB_SIZE,
      panelWidth: phone
        ? viewport.w - 16
        : chat
          ? Math.min(520, Math.max(400, viewport.w - 32))
          : 400,
      preferredHeight: phone
        ? Math.min(viewport.h - 24, Math.max(420, Math.floor(viewport.h * 0.9)))
        : chat
          ? Math.min(720, Math.max(480, Math.floor(viewport.h * 0.82)))
          : Math.min(560, Math.max(360, Math.floor(viewport.h * 0.65))),
    });
  }, [pos, viewport.w, viewport.h, tab]);

  if (!accessToken || onWorker || onLogin) return null;

  const badge = aiFabBadgeCount(unread, todoTotal);

  async function onRead(id: string) {
    await markAlertRead(id);
    await reload(false);
  }

  async function onReadAll() {
    await markAllAlertsRead();
    await reload(false);
  }

  function openHref(href: string) {
    setOpen(false);
    navigate(href);
  }

  function alertHref(a: AiAlert): string {
    switch (a.rule_key) {
      case "punch_odd":
        return "/m/timekeeping?view=daily";
      case "wt_regime_expiring":
        return "/m/hr/lists/special_regime";
      case "payslip_unconfirmed":
      case "period_lock_overdue":
        return "/m/payroll";
      case "dispute_new":
      case "dispute_stale":
        return "/m/dispute";
      case "kpi_attendance_low":
      case "kpi_ot_high":
      case "kpi_turnover_high":
      case "kpi_ot_dept_high":
        return "/m/report";
      default:
        return `/m/${a.target_module || "timekeeping"}`;
    }
  }

  async function onAsk(e: FormEvent) {
    e.preventDefault();
    await sendMessage(chatInput);
  }

  function stopSpeech() {
    speechRef.current?.stop();
    speechRef.current = null;
    setListening(false);
  }

  function toggleVoice() {
    if (asking) return;
    if (listening) {
      stopSpeech();
      return;
    }
    const blocked = speechBlockReason();
    if (blocked) {
      setError(blocked);
      return;
    }
    setError(null);
    setTab("chat");
    setListening(true);
    speechRef.current = startSpeechSession({
      onInterim: (text) => setChatInput(text),
      onFinal: (text) => {
        speechRef.current = null;
        setListening(false);
        setChatInput(text);
        if (text) void sendMessageRef.current(text);
      },
      onError: (message) => {
        speechRef.current = null;
        setListening(false);
        if (message) setError(message);
      },
      onEnd: () => {
        speechRef.current = null;
        setListening(false);
      },
    });
  }

  async function askPreset(s: AiSuggestion) {
    if (s.href && !s.message) {
      openHref(s.href);
      return;
    }
    if (!canAssist) {
      if (s.href) openHref(s.href);
      return;
    }
    if (!s.message) return;
    setTab("chat");
    setChatInput(s.message);
    await sendMessage(s.message);
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
  }

  return (
    <>
      {open && (
        <div
          className={`ai-fab-panel${tab === "chat" ? " ai-fab-panel--chat" : ""}`}
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
            {canAssist && (
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

          {error && <p className="banner-warn ai-fab-banner">{error}</p>}

          <div className="ai-fab-body">
            {tab === "alerts" ? (
              <>
                <div className="ai-fab-actions">
                  <button type="button" className="link-btn" onClick={() => void reload(false)}>
                    Làm mới
                  </button>
                  {canAssist && (
                    <button
                      type="button"
                      className="link-btn"
                      onClick={() =>
                        void askPreset({
                          label: "Tóm tắt hôm nay",
                          message: "Tóm tắt việc cần làm hôm nay",
                        })
                      }
                    >
                      Tóm tắt hôm nay
                    </button>
                  )}
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
                        {canAssist && card.ask_message && (
                          <button
                            type="button"
                            className="link-btn ai-fab-ask"
                            onClick={() =>
                              void askPreset({
                                label: "Hỏi",
                                message: card.ask_message ?? "",
                                href: card.href,
                              })
                            }
                          >
                            Hỏi AI
                          </button>
                        )}
                      </li>
                    ))}
                    {alerts.map((a) => (
                      <li key={a.id} className={a.is_read ? "is-read" : "is-unread"}>
                        <button
                          type="button"
                          className="ai-fab-item"
                          onClick={() => {
                            void onRead(a.id);
                            openHref(alertHref(a));
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
                <p className="field-hint ai-fab-chat-hint">
                  {canQuery
                    ? "Tra cứu MSNV/họ tên và việc nhà máy trả lời ngay từ CSDL. Câu phân tích mới gọi Gemini. Không tự sửa dữ liệu."
                    : "Bạn đang tra cứu CSDL (không gọi Gemini): tóm tắt hôm nay, thông tin NV, chấm lẻ, đơn phép, HĐ, thử việc. Câu phân tích cần Admin cấp quyền ai_query. Không tự sửa dữ liệu."}{" "}
                  Nói trên điện thoại: bấm mic, nói xong máy hỏi hộ. Không tự duyệt phép / sửa công / tính lương.
                </p>
                {(followups.length > 0 || suggestions.length > 0 || DEFAULT_CHIPS.length > 0) && (
                  <div className="ai-fab-chips" role="group" aria-label="Gợi ý hỏi">
                    {(followups.length > 0
                      ? followups
                      : suggestions.length > 0
                        ? suggestions
                        : DEFAULT_CHIPS
                    ).map((s) => (
                      <button
                        key={`${s.label}-${s.message ?? ""}-${s.href ?? ""}`}
                        type="button"
                        className="ai-fab-chip"
                        disabled={asking}
                        onClick={() => void askPreset(s)}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                )}
                <textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  rows={2}
                  maxLength={4000}
                  placeholder={
                    listening
                      ? "Đang nghe… nói ví dụ: ai chấm lẻ tháng này"
                      : "Gõ hoặc bấm mic. Ví dụ: Tóm tắt việc cần làm hôm nay · Thông tin Lê Văn C"
                  }
                  disabled={asking}
                />
                <div className="ai-fab-chat-row">
                  <button
                    type="button"
                    className={`ai-fab-mic${listening ? " is-listening" : ""}`}
                    aria-pressed={listening}
                    aria-label={listening ? "Dừng nghe" : "Nói lệnh cho Trợ Lý AI"}
                    title={listening ? "Dừng nghe" : "Nói (tiếng Việt)"}
                    disabled={asking}
                    onClick={toggleVoice}
                  >
                    {listening ? "●" : "🎤"}
                  </button>
                  <button type="submit" className="btn-primary" disabled={asking || listening || !chatInput.trim()}>
                    {asking ? "Đang hỏi…" : "Gửi"}
                  </button>
                </div>
                {chatMeta && <p className="field-hint ai-fab-chat-meta">{chatMeta}</p>}
                {(chatAnswer || thread.length > 0) && (
                  <div className="ai-fab-answer-wrap" aria-live="polite">
                    {thread.length > 1 &&
                      thread.slice(0, -1).map((item, i) => (
                        <div key={`${item.q}-${i}`} className="ai-fab-thread">
                          <p className="ai-fab-thread-q">{item.q}</p>
                          <pre className="ai-fab-answer">{item.a}</pre>
                        </div>
                      ))}
                    {chatAnswer && <pre className="ai-fab-answer">{chatAnswer}</pre>}
                  </div>
                )}
              </form>
            )}
          </div>
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
