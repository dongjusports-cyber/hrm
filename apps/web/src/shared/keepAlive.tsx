import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { useLocation, useParams } from "react-router-dom";

export type KeepAliveId = "hr-lists" | "timekeeping" | "payroll";

export type KeepAliveSnapshot = {
  pathname: string;
  search: string;
  params: Record<string, string | undefined>;
};

type State = {
  current: KeepAliveId | null;
  visited: KeepAliveId[];
  snaps: Partial<Record<KeepAliveId, KeepAliveSnapshot>>;
};

let state: State = { current: null, visited: [], snaps: {} };
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function snapEqual(a: KeepAliveSnapshot | undefined, b: KeepAliveSnapshot): boolean {
  if (!a) return false;
  return (
    a.pathname === b.pathname &&
    a.search === b.search &&
    JSON.stringify(a.params) === JSON.stringify(b.params)
  );
}

export function activateKeepAlive(id: KeepAliveId, snap: KeepAliveSnapshot) {
  const visited = state.visited.includes(id) ? state.visited : [...state.visited, id];
  if (state.current === id && state.visited === visited && snapEqual(state.snaps[id], snap)) {
    return;
  }
  state = { current: id, visited, snaps: { ...state.snaps, [id]: snap } };
  emit();
}

export function deactivateKeepAliveIf(id: KeepAliveId) {
  if (state.current !== id) return;
  state = { ...state, current: null };
  emit();
}

export function deactivateKeepAlive() {
  if (state.current == null) return;
  state = { ...state, current: null };
  emit();
}

export function resetKeepAlive() {
  state = { current: null, visited: [], snaps: {} };
  emit();
}

export function getKeepAliveState(): State {
  return state;
}

const PaneContext = createContext<KeepAliveId | null>(null);

export function useKeepAlivePaneId(): KeepAliveId | null {
  return useContext(PaneContext);
}

export function useKeepAliveState(): State {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
}

export function useKeepAlivePaneActive(): boolean {
  const pane = useKeepAlivePaneId();
  const { current } = useKeepAliveState();
  return pane == null || pane === current;
}

/** Host nằm ngoài Route — params URL lấy từ snapshot Gate ghi lúc vào trang. */
export function useAliveParams(): Record<string, string | undefined> {
  const pane = useKeepAlivePaneId();
  const { snaps } = useKeepAliveState();
  const live = useParams();
  if (pane) return snaps[pane]?.params ?? {};
  return live;
}

/** Route khớp — đánh dấu pane đang xem; nội dung thật nằm ở KeepAliveHost. */
export function KeepAliveGate({ id }: { id: KeepAliveId }) {
  const location = useLocation();
  const params = useParams();
  const filterKey = params.filterKey;
  useLayoutEffect(() => {
    activateKeepAlive(id, {
      pathname: location.pathname,
      search: location.search,
      params: { filterKey },
    });
  }, [id, location.pathname, location.search, filterKey]);
  return null;
}

/** Rời các trang keep-alive (Portal, hồ sơ NV, …) thì ẩn pane — không xen current=null khi đổi giữa 3 lưới. */
export function KeepAliveRouteSync() {
  const location = useLocation();
  useLayoutEffect(() => {
    const p = location.pathname;
    const onKept =
      p.startsWith("/m/hr/lists/") || p === "/m/timekeeping" || p === "/m/payroll";
    if (!onKept) deactivateKeepAlive();
  }, [location.pathname]);
  return null;
}

type HostProps = {
  render: (id: KeepAliveId, snap: KeepAliveSnapshot | undefined) => ReactNode;
};

/** Pane ẩn vẫn giữ DOM — phải inert + bỏ focus, không thì ESC bị ô tìm cũ nuốt. */
function KeepAlivePane({
  id,
  active,
  children,
}: {
  id: KeepAliveId;
  active: boolean;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (active) return;
    const root = ref.current;
    const el = document.activeElement;
    if (root && el instanceof HTMLElement && root.contains(el)) {
      el.blur();
    }
  }, [active]);

  return (
    <div
      ref={ref}
      className={`keep-alive-pane${active ? " is-active" : ""}`}
      aria-hidden={!active}
      inert={!active}
    >
      <PaneContext.Provider value={id}>{children}</PaneContext.Provider>
    </div>
  );
}

export function KeepAliveHost({ render }: HostProps) {
  const { current, visited, snaps } = useKeepAliveState();

  useEffect(() => {
    if (!current) return;
    const t = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 0);
    return () => window.clearTimeout(t);
  }, [current]);

  return (
    <div className="keep-alive-host">
      {visited.map((id) => (
        <KeepAlivePane key={id} id={id} active={current === id}>
          {render(id, snaps[id])}
        </KeepAlivePane>
      ))}
    </div>
  );
}
