import { useCallback, useEffect, useRef, useState } from "react";
import type { GridApi, GridReadyEvent, IRowNode } from "ag-grid-community";

/**
 * Lọc AG Grid tại chỗ — không thay rowData (~360 dòng) mỗi lần gõ MSNV.
 */
export function useAgGridExternalFilter<T>(opts: {
  active: boolean;
  queryKey: string;
  pass: (row: T) => boolean;
}) {
  const activeRef = useRef(opts.active);
  const passRef = useRef(opts.pass);
  activeRef.current = opts.active;
  passRef.current = opts.pass;

  const [api, setApi] = useState<GridApi<T> | null>(null);

  const isExternalFilterPresent = useCallback(() => activeRef.current, []);
  const doesExternalFilterPass = useCallback((node: IRowNode<T>) => {
    return !!node.data && passRef.current(node.data);
  }, []);

  useEffect(() => {
    api?.onFilterChanged();
  }, [opts.active, opts.queryKey, api]);

  const onGridReady = useCallback((e: GridReadyEvent<T>) => {
    setApi(e.api);
    e.api.onFilterChanged();
  }, []);

  return { isExternalFilterPresent, doesExternalFilterPass, onGridReady, api };
}
