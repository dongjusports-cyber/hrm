/** Tooltip khi nút bị disabled — §23 P2. */
export function disabledTitle(disabled: boolean, reason: string): string | undefined {
  return disabled ? reason : undefined;
}
