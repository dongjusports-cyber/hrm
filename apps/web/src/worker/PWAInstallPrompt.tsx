import { useEffect, useState } from "react";
import { useEscLayer } from "../shared/useEscLayer";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isStandalone(): boolean {
  if (typeof window === "undefined") return true;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    nav.standalone === true
  );
}

function isIosDevice(): boolean {
  const ua = navigator.userAgent || "";
  return /iphone|ipad|ipod/i.test(ua);
}

/**
 * Cài PWA 1-click — banner lớn cho công nhân (Login + Dashboard).
 * Android/Chrome: beforeinstallprompt → prompt() gốc.
 * iOS Safari: hướng dẫn Share → Thêm vào MH chính.
 */
export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(
    null,
  );
  const [installed, setInstalled] = useState(isStandalone);
  const [showIosGuide, setShowIosGuide] = useState(false);
  const [iosOpen, setIosOpen] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isStandalone()) {
      setInstalled(true);
      return;
    }

    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setDeferredPrompt(null);
      setIosOpen(false);
    };

    window.addEventListener("beforeinstallprompt", onBip);
    window.addEventListener("appinstalled", onInstalled);

    if (isIosDevice()) {
      setShowIosGuide(true);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", onBip);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  useEscLayer(iosOpen, () => setIosOpen(false));

  if (installed) return null;

  const canOneClick = Boolean(deferredPrompt);
  if (!canOneClick && !showIosGuide) return null;

  async function onInstallClick() {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      setDeferredPrompt(null);
      if (choice.outcome === "accepted") {
        setInstalled(true);
      }
      return;
    }
    if (showIosGuide) {
      setIosOpen(true);
    }
  }

  return (
    <>
      <div className="pwa-oneclick-wrap">
        <button
          type="button"
          className="pwa-oneclick-btn"
          onClick={() => void onInstallClick()}
        >
          <span className="pwa-oneclick-icon" aria-hidden>
            📲
          </span>
          <span className="pwa-oneclick-text">
            BẤM VÀO ĐÂY ĐỂ CÀI ĐẶT ỨNG DỤNG RA MÀN HÌNH
          </span>
        </button>
      </div>

      {iosOpen && (
        <div
          className="pwa-ios-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="pwa-ios-title"
          onClick={() => setIosOpen(false)}
        >
          <div className="pwa-ios-card" onClick={(e) => e.stopPropagation()}>
            <div className="pwa-ios-arrow" aria-hidden>
              ↓
            </div>
            <h2 id="pwa-ios-title">Cài DJ HRM trên iPhone</h2>
            <p>
              Bấm nút <strong>Chia sẻ (Share ⎘)</strong> ở đáy màn hình
              <br />➔ Chọn <strong>«Thêm vào MH chính»</strong>
            </p>
            <button
              type="button"
              className="worker-btn-secondary"
              onClick={() => setIosOpen(false)}
            >
              Đã hiểu
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/** @deprecated dùng PWAInstallPrompt */
export const InstallPrompt = PWAInstallPrompt;
