import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AllCommunityModule, ModuleRegistry, provideGlobalGridOptions } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import App from "./App";
import "./styles/global.css";
import "./styles/ag-grid-djhrm.css";

/* AG Grid 33: dùng file CSS (ag-grid.css) — tránh error #239 xung đột Theming API */
provideGlobalGridOptions({ theme: "legacy" });

ModuleRegistry.registerModules([AllCommunityModule]);

// Dev: gỡ SW cũ (cache-first từng chặn CSS/JS mới)
if (import.meta.env.DEV && "serviceWorker" in navigator) {
  void navigator.serviceWorker.getRegistrations().then((regs) => {
    for (const reg of regs) void reg.unregister();
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);

// PWA Worker — chỉ production (dev: tránh cache CSS/JS cũ gây “sửa mà không đổi”)
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").catch(() => {
      /* bỏ qua nếu môi trường dev không hỗ trợ */
    });
  });
}
