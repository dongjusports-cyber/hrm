const STORAGE_KEY = "djhrm_worker_device_id";
const COOKIE_KEY = "djhrm_wid";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 10;

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

function writeCookie(name: string, value: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${COOKIE_MAX_AGE}; Path=/; SameSite=Lax`;
}

function newDeviceId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `dev-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

/** Mã máy bền trên điện thoại — lần đầu login gắn MSNV, không đổi khi đăng xuất. */
export function getWorkerDeviceId(): string {
  let id: string | null = null;
  try {
    id = localStorage.getItem(STORAGE_KEY);
  } catch {
    id = null;
  }
  if (!id || id.length < 8) {
    id = readCookie(COOKIE_KEY);
  }
  if (!id || id.length < 8) {
    id = newDeviceId();
  }
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* private mode */
  }
  writeCookie(COOKIE_KEY, id);
  return id;
}
