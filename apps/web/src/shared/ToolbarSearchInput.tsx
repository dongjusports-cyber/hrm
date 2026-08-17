import { startTransition, useEffect, useRef, useState, type CSSProperties } from "react";

type Props = {
  className?: string;
  wrapClassName?: string;
  placeholder?: string;
  /** Tăng khi Đặt lại / đổi tab — xóa chữ trong ô, không re-render lưới mỗi phím. */
  resetToken?: number;
  /** Lọc live (startTransition) — lưới không chặn phím khi gõ 4 số MSNV dồn. */
  onQuery?: (q: string) => void;
  onSubmit?: (q: string) => void;
  onTyped?: (q: string) => void;
  autoComplete?: string;
  style?: CSSProperties;
  /** Giá trị ban đầu (vd. ?q= từ URL). */
  initialValue?: string;
};

/**
 * Ô tìm MSNV tách state local: gõ nhanh không setState trang cha / AG Grid.
 */
export function ToolbarSearchInput({
  className,
  wrapClassName,
  placeholder = "Tìm MSNV / họ tên…",
  resetToken = 0,
  onQuery,
  onSubmit,
  onTyped,
  autoComplete = "off",
  style,
  initialValue = "",
}: Props) {
  const [value, setValue] = useState(initialValue);
  const onQueryRef = useRef(onQuery);
  const onSubmitRef = useRef(onSubmit);
  const onTypedRef = useRef(onTyped);
  onQueryRef.current = onQuery;
  onSubmitRef.current = onSubmit;
  onTypedRef.current = onTyped;

  useEffect(() => {
    if (resetToken === 0) return;
    setValue("");
    onTypedRef.current?.("");
    onQueryRef.current?.("");
  }, [resetToken]);

  const input = (
    <input
      className={className}
      placeholder={placeholder}
      autoComplete={autoComplete}
      style={style}
      data-hotkey-search
      value={value}
      onChange={(e) => {
        const next = e.target.value;
        setValue(next);
        onTypedRef.current?.(next);
        if (onQueryRef.current) {
          const trimmed = next.trim();
          startTransition(() => onQueryRef.current?.(trimmed));
        }
      }}
      onKeyDown={(e) => {
        if (e.key !== "Enter") return;
        e.preventDefault();
        onSubmitRef.current?.(value.trim());
      }}
    />
  );

  if (wrapClassName) {
    return (
      <label className={wrapClassName}>
        <span className="sr-only">{placeholder}</span>
        {input}
      </label>
    );
  }
  return input;
}
