import {
  type FocusEvent,
  type InputHTMLAttributes,
  type KeyboardEvent,
  type MouseEvent,
  useCallback,
  useRef,
  useState,
} from "react";
import { clearActiveFieldEsc, registerActiveFieldEsc } from "./formFieldEsc";

const TIME_RE = /^([01]\d|2[0-3]):([0-5]\d)$/;

/** Kiểm tra HH:mm 24 giờ (07:53, 17:00). */
export function isValidTimeHHMM(v: string): boolean {
  return TIME_RE.test(v.trim());
}

/** Chuẩn hoá nhập tay: 735 → 07:35, 1240 → 12:40. */
export function normalizeTimeHHMM(raw: string): string {
  const s = raw.trim();
  if (TIME_RE.test(s)) return s;
  const digits = s.replace(/\D/g, "");
  if (digits.length === 3) {
    const out = `${digits.slice(0, 1).padStart(2, "0")}:${digits.slice(1)}`;
    return TIME_RE.test(out) ? out : s;
  }
  if (digits.length === 4) {
    const out = `${digits.slice(0, 2)}:${digits.slice(2)}`;
    return TIME_RE.test(out) ? out : s;
  }
  return s;
}

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "onChange"> & {
  value: string;
  onChange: (value: string) => void;
  /** ESC trong ô — báo parent không lưu khi blur. */
  onEditCancel?: () => void;
};

/** Ô nhập giờ 24h — bôi đen khi focus; ESC hoàn tác (không thoát tab). */
export function TimeInput24({
  value,
  onChange,
  className,
  onBlur,
  onFocus,
  onKeyDown,
  onClick,
  onEditCancel,
  placeholder = "HH:mm",
  ...rest
}: Props) {
  const [, setEditing] = useState(false);
  const snapshotRef = useRef(value);
  const onEditCancelRef = useRef(onEditCancel);
  onEditCancelRef.current = onEditCancel;

  const selectAll = useCallback((el: HTMLInputElement) => {
    requestAnimationFrame(() => el.select());
  }, []);

  const handleFocus = useCallback(
    (e: FocusEvent<HTMLInputElement>) => {
      snapshotRef.current = value;
      setEditing(true);
      registerActiveFieldEsc(e.currentTarget, () => {
        onEditCancelRef.current?.();
        setEditing(false);
      });
      selectAll(e.currentTarget);
      onFocus?.(e);
    },
    [onFocus, selectAll, value],
  );

  const handleBlur = useCallback(
    (e: FocusEvent<HTMLInputElement>) => {
      setEditing(false);
      clearActiveFieldEsc(e.currentTarget);
      const n = normalizeTimeHHMM(e.target.value);
      if (n !== value) onChange(n);
      onBlur?.(e);
    },
    [onBlur, onChange, value],
  );

  const handleClick = useCallback(
    (e: MouseEvent<HTMLInputElement>) => {
      e.stopPropagation();
      selectAll(e.currentTarget);
      onClick?.(e);
    },
    [onClick, selectAll],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      e.stopPropagation();
      if (e.key === ":" && value.includes(":")) e.preventDefault();
      if (e.key === "Enter") {
        e.preventDefault();
        e.currentTarget.blur();
      }
      onKeyDown?.(e);
    },
    [onKeyDown, value],
  );

  return (
    <input
      {...rest}
      type="text"
      inputMode="numeric"
      className={className ? `tk-time-input24 ${className}` : "tk-time-input24"}
      placeholder={placeholder}
      maxLength={5}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      autoComplete="off"
      spellCheck={false}
      aria-label={rest["aria-label"] ?? "Giờ 24h HH:mm"}
    />
  );
}
