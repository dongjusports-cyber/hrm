import { useEffect, useMemo, useRef, useState } from "react";

export type EmployeePickOption = {
  employee_code: string;
  full_name: string;
};

type Props = {
  options: EmployeePickOption[];
  value: string;
  onChange: (employeeCode: string) => void;
  disabled?: boolean;
  placeholder?: string;
  inputId?: string;
};

/** Chọn MSNV có ô tìm — tránh dropdown 300+ option. */
export function EmployeeCodePicker({
  options,
  value,
  onChange,
  disabled,
  placeholder = "Tìm MSNV / họ tên…",
  inputId,
}: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = useMemo(
    () => options.find((o) => o.employee_code === value) ?? null,
    [options, value],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q
      ? options.filter(
          (o) =>
            o.employee_code.toLowerCase().includes(q) ||
            o.full_name.toLowerCase().includes(q),
        )
      : options;
    const collator = new Intl.Collator("vi", { numeric: true, sensitivity: "base" });
    return [...list]
      .sort((a, b) => collator.compare(a.full_name, b.full_name) || collator.compare(a.employee_code, b.employee_code))
      .slice(0, 40);
  }, [options, query]);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  function pick(code: string) {
    onChange(code);
    setOpen(false);
    setQuery("");
  }

  function clear() {
    onChange("");
    setQuery("");
    setOpen(false);
  }

  const showList = open && !disabled && (filtered.length > 0 || query.trim());

  return (
    <div className="emp-code-picker" ref={rootRef}>
      <div className="emp-code-picker-row">
        <input
          id={inputId}
          type="text"
          className="emp-code-picker-input"
          value={open ? query : selected ? `${selected.employee_code} — ${selected.full_name}` : query}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            if (value) onChange("");
          }}
          onFocus={() => {
            setOpen(true);
            if (selected && !query) {
              setQuery(selected.employee_code);
              onChange("");
            }
          }}
        />
        {value && !disabled && (
          <button
            type="button"
            className="emp-code-picker-clear"
            aria-label="Bỏ chọn MSNV"
            onClick={clear}
          >
            ×
          </button>
        )}
      </div>
      {showList && filtered.length > 0 && (
        <ul className="emp-code-picker-list" role="listbox">
          {filtered.map((o) => (
            <li key={o.employee_code}>
              <button
                type="button"
                role="option"
                className="emp-code-picker-option"
                onClick={() => pick(o.employee_code)}
              >
                <strong>{o.employee_code}</strong> {o.full_name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {showList && query.trim() && filtered.length === 0 && (
        <p className="emp-code-picker-empty">Không thấy MSNV / họ tên khớp.</p>
      )}
      {!query.trim() && open && !disabled && options.length > 40 && (
        <p className="emp-code-picker-hint">Gõ MSNV hoặc họ tên để lọc ({options.length} NV).</p>
      )}
    </div>
  );
}
