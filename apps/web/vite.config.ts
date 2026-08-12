import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react()],
    test: {
      environment: "node",
    },
    resolve: {
      alias: {
        "@": "/src",
      },
    },
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      // ĐT/LAN: cho phép mọi host (dev local) — tránh Blocked request
      allowedHosts: true,
      // ĐT mở http://IP:5173 → /api proxy sang API (tránh Failed to fetch / localhost)
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
      // HMR qua IP LAN — tránh ERR_CONNECTION_ABORTED khi không phải localhost
      hmr: {
        clientPort: 5173,
      },
      // Docker Desktop (Windows): bind-mount không bắn inotify → cần poll
      watch: {
        usePolling: true,
        interval: 1000,
      },
    },
  };
});
