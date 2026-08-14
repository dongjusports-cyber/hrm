import { useCallback, useEffect, useState } from "react";

const APP_FS_CLASS = "app-fullscreen";

type FsDocument = Document & {
  webkitFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void>;
};

/** Chỉ thoát khi bấm «Thoát» — CSS full viewport, không dùng Fullscreen API (ESC không thoát). */
let locked = false;

function getBrowserFullscreenElement(): Element | null {
  if (typeof document === "undefined") return null;
  const doc = document as FsDocument;
  return doc.fullscreenElement ?? doc.webkitFullscreenElement ?? null;
}

async function exitBrowserFullscreenIfAny(): Promise<void> {
  if (!getBrowserFullscreenElement()) return;
  const doc = document as FsDocument;
  const fn = doc.exitFullscreen?.bind(doc) ?? doc.webkitExitFullscreen?.bind(doc);
  if (!fn) return;
  await fn();
}

/** Bật/tắt fullscreen — chỉ nút «Full/Thoát»; ESC không ảnh hưởng. */
export function useFullscreen() {
  const [active, setActive] = useState(() => {
    if (typeof document === "undefined") return false;
    return document.documentElement.classList.contains(APP_FS_CLASS);
  });

  const enter = useCallback(async () => {
    locked = true;
    document.documentElement.classList.add(APP_FS_CLASS);
    setActive(true);
  }, []);

  const leave = useCallback(async () => {
    locked = false;
    document.documentElement.classList.remove(APP_FS_CLASS);
    setActive(false);
    try {
      await exitBrowserFullscreenIfAny();
    } catch {
      /* dọn API cũ nếu còn */
    }
  }, []);

  const toggle = useCallback(async () => {
    if (locked) await leave();
    else await enter();
  }, [enter, leave]);

  useEffect(() => {
    if (locked) document.documentElement.classList.add(APP_FS_CLASS);
  }, []);

  return { active, supported: true, toggle };
}
