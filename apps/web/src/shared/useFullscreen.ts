import { useCallback, useEffect, useState } from "react";

type FsDocument = Document & {
  webkitFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void>;
};

type FsElement = HTMLElement & {
  webkitRequestFullscreen?: () => Promise<void>;
};

function getFullscreenElement(): Element | null {
  const doc = document as FsDocument;
  return doc.fullscreenElement ?? doc.webkitFullscreenElement ?? null;
}

function isSupported(): boolean {
  if (typeof document === "undefined") return false;
  const el = document.documentElement as FsElement;
  return Boolean(el.requestFullscreen || el.webkitRequestFullscreen);
}

async function enterFullscreen(): Promise<void> {
  const el = document.documentElement as FsElement;
  const fn = el.requestFullscreen?.bind(el) ?? el.webkitRequestFullscreen?.bind(el);
  if (!fn) throw new Error("unsupported");
  await fn();
}

async function leaveFullscreen(): Promise<void> {
  const doc = document as FsDocument;
  const fn = doc.exitFullscreen?.bind(doc) ?? doc.webkitExitFullscreen?.bind(doc);
  if (!fn) throw new Error("unsupported");
  await fn();
}

/** Bật/tắt fullscreen trình duyệt (ẩn thanh địa chỉ Chrome khi được phép). */
export function useFullscreen() {
  const [active, setActive] = useState(() => Boolean(getFullscreenElement()));
  const supported = isSupported();

  useEffect(() => {
    function sync() {
      setActive(Boolean(getFullscreenElement()));
    }
    document.addEventListener("fullscreenchange", sync);
    document.addEventListener("webkitfullscreenchange", sync);
    return () => {
      document.removeEventListener("fullscreenchange", sync);
      document.removeEventListener("webkitfullscreenchange", sync);
    };
  }, []);

  const toggle = useCallback(async () => {
    try {
      if (getFullscreenElement()) {
        await leaveFullscreen();
      } else {
        await enterFullscreen();
      }
    } catch {
      /* Chrome có thể chặn nếu không phải thao tác người dùng */
    }
  }, []);

  return { active, supported, toggle };
}
