#!/usr/bin/env bash
# DJ HRM — khởi động mỗi lần boot: Postgres + Redis + seed (idempotent).
# API và Web chạy ở các terminal riêng (xem .cursor/environment.json).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/dbsetup.sh"
