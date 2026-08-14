/** Vị trí nút Trợ Lý AI — kéo thả, nhớ localStorage. */

export type FabPosition = { left: number; top: number };

const STORAGE_KEY = "djhrm.aiFab.pos";
const FAB_SIZE = 56;
const MARGIN = 12;

export function clampFabPosition(
  left: number,
  top: number,
  viewportWidth: number,
  viewportHeight: number,
  fabSize = FAB_SIZE,
  margin = MARGIN,
): FabPosition {
  const maxLeft = Math.max(margin, viewportWidth - fabSize - margin);
  const maxTop = Math.max(margin, viewportHeight - fabSize - margin);
  return {
    left: Math.min(Math.max(margin, left), maxLeft),
    top: Math.min(Math.max(margin, top), maxTop),
  };
}

export function defaultFabPosition(
  viewportWidth: number,
  viewportHeight: number,
  fabSize = FAB_SIZE,
  margin = MARGIN,
): FabPosition {
  return {
    left: viewportWidth - fabSize - margin,
    top: viewportHeight - fabSize - margin,
  };
}

/** Chrome toolbar + tiêu đề module — FAB không nên đè vùng lưới phía trên. */
const GRID_TOP_CHROME = 100;
/** FAB lệch trái quá mức này thường che cột MSNV/Họ tên/BP. */
const GRID_LEFT_MAX = 420;
const GRID_LEFT_VIEWPORT_RATIO = 0.45;

/** FAB đè lên vùng lưới staff (trái viewport, dưới toolbar). */
export function isFabOverGridZone(
  pos: FabPosition,
  viewportWidth: number,
  viewportHeight: number,
  fabSize = FAB_SIZE,
): boolean {
  const gridLeftBound = Math.min(GRID_LEFT_MAX, viewportWidth * GRID_LEFT_VIEWPORT_RATIO);
  const cx = pos.left + fabSize / 2;
  const cy = pos.top + fabSize / 2;
  return (
    cx < gridLeftBound &&
    cy > GRID_TOP_CHROME &&
    cy < viewportHeight - fabSize
  );
}

/** Đẩy FAB về góc dưới-phải nếu đang che lưới. */
export function nudgeFabFromGrid(
  pos: FabPosition,
  viewportWidth: number,
  viewportHeight: number,
  fabSize = FAB_SIZE,
): FabPosition {
  if (!isFabOverGridZone(pos, viewportWidth, viewportHeight, fabSize)) {
    return clampFabPosition(pos.left, pos.top, viewportWidth, viewportHeight, fabSize);
  }
  return defaultFabPosition(viewportWidth, viewportHeight, fabSize);
}

export function loadFabPosition(viewportWidth?: number, viewportHeight?: number): FabPosition {
  const w = viewportWidth ?? (typeof window !== "undefined" ? window.innerWidth : 1280);
  const h = viewportHeight ?? (typeof window !== "undefined" ? window.innerHeight : 720);
  try {
    if (typeof localStorage === "undefined") {
      return defaultFabPosition(w, h);
    }
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultFabPosition(w, h);
    const parsed = JSON.parse(raw) as Partial<FabPosition>;
    if (typeof parsed.left !== "number" || typeof parsed.top !== "number") {
      return defaultFabPosition(w, h);
    }
    return nudgeFabFromGrid({ left: parsed.left, top: parsed.top }, w, h);
  } catch {
    return defaultFabPosition(w, h);
  }
}

export function saveFabPosition(pos: FabPosition): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(pos));
}

export function clearFabPosition(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export type PanelBox = { left: number; top: number; width: number; maxHeight: number };

/**
 * Đặt panel trong khung màn — tránh tràn góc trên/phải khiến không bấm Đóng được.
 * Ưu tiên: mở sang trái nếu FAB gần cạnh phải; mở xuống nếu còn chỗ, không thì mở lên.
 */
export function computePanelBox(
  fab: FabPosition,
  viewportWidth: number,
  viewportHeight: number,
  opts?: {
    fabSize?: number;
    panelWidth?: number;
    preferredHeight?: number;
    margin?: number;
    gap?: number;
  },
): PanelBox {
  const fabSize = opts?.fabSize ?? FAB_SIZE;
  const panelWidth = opts?.panelWidth ?? 400;
  const preferredHeight = opts?.preferredHeight ?? 520;
  const margin = opts?.margin ?? MARGIN;
  const gap = opts?.gap ?? 10;

  const width = Math.min(panelWidth, Math.max(240, viewportWidth - margin * 2));
  const maxHeight = Math.min(preferredHeight, Math.max(200, viewportHeight - margin * 2));

  let left = fab.left + fabSize - width;
  if (left < margin) left = margin;
  if (left + width > viewportWidth - margin) {
    left = Math.max(margin, viewportWidth - margin - width);
  }

  const belowTop = fab.top + fabSize + gap;
  const spaceBelow = viewportHeight - margin - belowTop;
  const spaceAbove = fab.top - margin - gap;

  let top: number;
  if (spaceBelow >= Math.min(280, maxHeight) || spaceBelow >= spaceAbove) {
    top = belowTop;
    if (top + maxHeight > viewportHeight - margin) {
      top = Math.max(margin, viewportHeight - margin - maxHeight);
    }
  } else {
    top = Math.max(margin, fab.top - gap - maxHeight);
  }

  return { left, top, width, maxHeight };
}
