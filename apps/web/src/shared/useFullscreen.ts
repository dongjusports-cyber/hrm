import { useCallback, useEffect, useState } from "react";

const APP_FS_CLASS = "app-fullscreen";

type FsDocument = Document & {
  webkitFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void>;
};

type FsElement = HTMLElement & {
  webkitRequestFullscreen?: () => Promise<void>;
};

/** Chỉ thoát khi bấm «Thoát» — ESC/F11 thoát browser fs thì tự bật lại. */
let locked = false;

function getBrowserFullscreenElement(): Element | null {
  if (typeof document === "undefined") return null;
  const doc = document as FsDocument;
  return doc.fullscreenElement ?? doc.webkitFullscreenElement ?? null;
}

function isSupported(): boolean {
  if (typeof document === "undefined") return false;
  const el = document.documentElement as FsElement;
  return Boolean(el.requestFullscreen || el.webkitRequestFullscreen);
}

async function enterBrowserFullscreen(): Promise<void> {
  const el = document.documentElement as FsElement;
  const fn = el.requestFullscreen?.bind(el) ?? el.webkitRequestFullscreen?.bind(el);
  if (!fn) throw new Error("unsupported");
  await fn();
}

async function exitBrowserFullscreenIfAny(): Promise<void> {
  if (!getBrowserFullscreenElement()) return;
  const doc = document as FsDocument;
  const fn = doc.exitFullscreen?.bind(doc) ?? doc.webkitExitFullscreen?.bind(doc);
  if (!fn) return;
  await fn();
}

/** Bật/tắt fullscreen trình duyệt — ESC không thoát; chỉ nút «Thoát». */
export function useFullscreen() {
  const [active, setActive] = useState(false);
  const supported = isSupported();

  useEffect(() => {
    function sync() {
      if (locked && !getBrowserFullscreenElement()) {
        void enterBrowserFullscreen().catch(() => {});
      }
      setActive(locked);
    }
    document.addEventListener("fullscreenchange", sync);
    document.addEventListener("webkitfullscreenchange", sync);
    return () => {
      document.removeEventListener("fullscreenchange", sync);
      document.removeEventListener("webkitfullscreenchange", sync);
    };
  }, []);

  const enter = useCallback(async () => {
    locked = true;
    document.documentElement.classList.add(APP_FS_CLASS);
    setActive(true);
    try {
      if (!getBrowserFullscreenElement()) {
        await enterBrowserFullscreen();
      }
    } catch {
      /* Giữ locked + CSS nếu trình duyệt chặn API */
    }
  }, []);

  const leave = useCallback(async () => {
    locked = false;
    document.documentElement.classList.remove(APP_FS_CLASS);
    setActive(false);
    try {
      await exitBrowserFullscreenIfAny();
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = useCallback(async () => {
    if (locked) await leave();
    else await enter();
  }, [enter, leave]);

  return { active, supported, toggle };
}
