import { useEffect } from "react";

/** Trang worker: nền sáng — không dùng gradient xanh portal trên body. */
export function useWorkerSurface() {
  useEffect(() => {
    document.documentElement.classList.add("worker-surface");
    document.body.classList.add("worker-surface");
    return () => {
      document.documentElement.classList.remove("worker-surface");
      document.body.classList.remove("worker-surface");
    };
  }, []);
}
