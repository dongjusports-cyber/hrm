import { useEffect, useMemo, useState } from "react";
import { fetchLookupValues, type LookupValue } from "./api";

type Props = {
  groupCode: string;
  value: string;
  onChange: (code: string) => void;
  label?: string;
  required?: boolean;
  allowEmpty?: boolean;
  emptyLabel?: string;
  className?: string;
};

const cache = new Map<string, LookupValue[]>();

export function LookupSelect({
  groupCode,
  value,
  onChange,
  label,
  required,
  allowEmpty = true,
  emptyLabel = "— Chọn —",
  className = "field",
}: Props) {
  const [options, setOptions] = useState<LookupValue[]>(() => cache.get(groupCode) ?? []);
  const [loading, setLoading] = useState(!cache.has(groupCode));

  useEffect(() => {
    if (cache.has(groupCode)) {
      setOptions(cache.get(groupCode)!);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void fetchLookupValues(groupCode)
      .then((rows) => {
        if (cancelled) return;
        cache.set(groupCode, rows);
        setOptions(rows);
      })
      .catch(() => {
        if (!cancelled) setOptions([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [groupCode]);

  const selectedName = useMemo(() => {
    if (!value) return "";
    return options.find((o) => o.code === value)?.name ?? value;
  }, [options, value]);

  return (
    <label className={className}>
      {label && <span>{label}</span>}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        disabled={loading && options.length === 0}
        title={selectedName || undefined}
      >
        {allowEmpty && <option value="">{loading ? "Đang tải…" : emptyLabel}</option>}
        {options.map((o) => (
          <option key={o.code} value={o.code}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );
}
