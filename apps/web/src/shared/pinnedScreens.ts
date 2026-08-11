/** Ghim màn hình yêu thích — localStorage (5.7). */

export type PinnedScreen = {
  id: string;
  label: string;
  href: string;
};

const KEY = "djhrm.pinnedScreens";

export function getPinnedScreens(): PinnedScreen[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as PinnedScreen[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function savePinnedScreens(rows: PinnedScreen[]): void {
  localStorage.setItem(KEY, JSON.stringify(rows.slice(0, 12)));
}

export function isPinned(href: string): boolean {
  return getPinnedScreens().some((p) => p.href === href);
}

export function togglePinned(screen: PinnedScreen): PinnedScreen[] {
  const cur = getPinnedScreens();
  const exists = cur.some((p) => p.href === screen.href);
  const next = exists
    ? cur.filter((p) => p.href !== screen.href)
    : [...cur, screen].slice(0, 12);
  savePinnedScreens(next);
  return next;
}
