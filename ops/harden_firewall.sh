#!/usr/bin/env bash
# Bật UFW (22/80/443) + swap 1G — chạy trên VPS khi deploy.
# Không reset UFW (tránh cắt SSH giữa chừng).
set -euo pipefail

echo "→ Swap 1G (phòng hết RAM)..."
if [[ "$(swapon --show 2>/dev/null | wc -l)" -eq 0 ]]; then
  if [[ ! -f /swapfile ]]; then
    fallocate -l 1G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=1024 status=none
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
  fi
  swapon /swapfile 2>/dev/null || true
  if ! grep -q '^/swapfile ' /etc/fstab 2>/dev/null; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
fi

if ! command -v ufw >/dev/null 2>&1; then
  echo "→ Cài ufw..."
  apt-get update -qq
  apt-get install -y -qq ufw
fi

echo "→ Firewall: chỉ SSH + HTTPS (chặn 8080/5432/6379 từ Internet)..."
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
echo "y" | ufw enable >/dev/null || ufw --force enable >/dev/null
ufw status | head -20
