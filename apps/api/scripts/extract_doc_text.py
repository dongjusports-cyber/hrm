"""Extract readable text from legacy .doc (OLE) — dev utility."""
import re
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else path.with_suffix(".txt")
    data = path.read_bytes()
    text = data.decode("utf-16-le", errors="ignore")
    # Keep printable + Vietnamese
    cleaned = "".join(ch if (ch.isprintable() or ch in "\n\r\t") else "\n" for ch in text)
    lines = [ln.strip() for ln in cleaned.splitlines() if len(ln.strip()) >= 4]
    # dedupe consecutive
    out_lines: list[str] = []
    prev = None
    for ln in lines:
        if ln != prev:
            out_lines.append(ln)
            prev = ln
    out.write_text("\n".join(out_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
