"""Dong goi 1 folder USB cho may .122 — chay tren may .123."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = Path(r"C:\DATA\HRM\USB-122-AGENT")
AGENT_SRC = REPO / "apps" / "agent"
SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".git"}
SKIP_FILES = {".env", "agent_state.json", "agent.log"}


def _token() -> str:
    vps = REPO / "ops" / "vps-root.txt"
    if vps.is_file():
        lines = [
            ln.strip()
            for ln in vps.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
        if len(lines) >= 4:
            return lines[3]
    raise SystemExit("LOI: thieu AGENT_TOKEN (ops/vps-root.txt dong 4).")


def _copy_agent(dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    for path in AGENT_SRC.rglob("*"):
        rel = path.relative_to(AGENT_SRC)
        if any(p in SKIP_DIRS for p in rel.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _write_env(agent_dir: Path, token: str) -> None:
    text = f"""DJ_API_BASE_URL=https://hrm.dongju-v.com
DJ_AGENT_TOKEN={token}
DJ_AGENT_REQUIRE_HTTPS=1

MITAPRO_ODBC=Driver={{ODBC Driver 17 for SQL Server}};Server=.\\SQLEXPRESS;Database=MITACOSQL;Trusted_Connection=yes;TrustServerCertificate=yes;

SYNC_INTERVAL_MINUTES=2
SYNC_OVERLAP_MINUTES=30
SYNC_LOOKBACK_DAYS=3
PUSH_CHUNK_SIZE=800
DJ_AGENT_MOCK_SQL=0
STATE_FILE=./agent_state.json
AGENT_NAME=dj-agent-hr122
"""
    (agent_dir / ".env").write_text(text, encoding="utf-8")


def main() -> int:
    if not (AGENT_SRC / "dj_agent" / "main.py").is_file():
        print("LOI: thieu apps/agent/dj_agent/main.py")
        return 1
    token = _token()
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    bats = [
        "DOC_BAT_DAU.txt",
        "README.txt",
        "HUONG-DAN-ODBC.txt",
        "01-KIEM-TRA-ODBC.bat",
        "02-CAI-DAT.bat",
        "03-CHAY-THU.bat",
        "04-CAI-TU-CHAY.bat",
        "04-cai-tu-chay.ps1",
        "05-TAT-TU-CHAY.bat",
        "05-tat-tu-chay.ps1",
    ]
    src_122 = REPO / "122"
    for name in bats:
        shutil.copy2(src_122 / name, DEST / name)

    _copy_agent(DEST / "agent")
    _write_env(DEST / "agent", token)

    print(f"XONG. Copy CA folder nay sang USB:")
    print(f"  {DEST}")
    print("Tren may .122: xoa agent/122 cu, dan thanh D:\\122-AGENT")
    print("Roi chay: 01 -> 02 -> 04 (04 chuot phai Run as administrator)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
