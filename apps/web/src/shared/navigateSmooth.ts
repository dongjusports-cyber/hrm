import type { NavigateFunction } from "react-router-dom";

/** Điều hướng mượt — dùng View Transition khi trình duyệt hỗ trợ. */
export function navigateSmooth(navigate: NavigateFunction, to: string) {
  const go = () => navigate(to);
  const doc = document as Document & {
    startViewTransition?: (cb: () => void) => void;
  };
  if (typeof doc.startViewTransition !== "function") {
    go();
    return;
  }
  try {
    doc.startViewTransition(go);
  } catch {
    go();
  }
}
