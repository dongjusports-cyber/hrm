/**
 * Base URL API — trên ĐT không được dùng localhost (trỏ về chính máy ĐT).
 * - `same-origin` / rỗng → gọi `/api/...` qua Vite proxy (khuyên dùng local).
 * - URL tuyệt đối có localhost nhưng page mở bằng IP LAN → đổi host theo page.
 */
export function getApiBase(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  if (!raw || raw === "same-origin" || raw === "/") {
    return "";
  }

  const configured = raw.replace(/\/$/, "");
  if (typeof window === "undefined") return configured;

  try {
    const apiUrl = new URL(configured);
    const pageHost = window.location.hostname;
    const apiIsLoopback =
      apiUrl.hostname === "localhost" || apiUrl.hostname === "127.0.0.1";
    const pageIsLoopback = pageHost === "localhost" || pageHost === "127.0.0.1";
    if (apiIsLoopback && !pageIsLoopback) {
      const port = apiUrl.port || "8000";
      return `${window.location.protocol}//${pageHost}:${port}`;
    }
  } catch {
    /* giữ configured */
  }
  return configured;
}
