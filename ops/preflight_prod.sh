#!/usr/bin/env bash
# Kiểm tra .env.prod trước khi lên VPS (không cần Docker chạy)
set -euo pipefail
ENV_FILE="${1:-.env.prod}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "COSMOS AI: không thấy $ENV_FILE" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

err=0
warn() { echo "CẢNH BÁO: $1"; }
fail() { echo "LỖI: $1"; err=1; }

[[ "${APP_ENV:-}" == "production" || "${APP_ENV:-}" == "prod" || "${APP_ENV:-}" == "cloud" ]] \
  || fail "APP_ENV phải là production (hiện: ${APP_ENV:-trống})"

[[ -n "${JWT_SECRET:-}" && ${#JWT_SECRET} -ge 24 ]] || fail "JWT_SECRET thiếu hoặc < 24 ký tự"
[[ "${JWT_SECRET}" != "change_me_to_a_long_random_string" ]] || fail "JWT_SECRET còn mẫu"

[[ -n "${AGENT_TOKEN:-}" && "${AGENT_TOKEN}" != "change_me_agent_token" ]] \
  || fail "AGENT_TOKEN còn mặc định"

[[ -n "${POSTGRES_PASSWORD:-}" && "${POSTGRES_PASSWORD}" != "doi_mat_khau_manh_o_day" ]] \
  || fail "POSTGRES_PASSWORD chưa đổi"

[[ "${CORS_ORIGINS:-}" != *"*"* ]] || fail "CORS_ORIGINS không được *"
[[ "${CORS_ORIGINS:-}" == https://* ]] || warn "CORS_ORIGINS nên là https://domain"

if [[ -n "${DOMAIN:-}" ]]; then
  [[ -n "${CADDY_EMAIL:-}" ]] || warn "Có DOMAIN nhưng thiếu CADDY_EMAIL (cần cho --ssl)"
  echo "DOMAIN=$DOMAIN"
else
  warn "Chưa đặt DOMAIN — deploy HTTP :8080; SSL = ./ops/deploy.sh --ssl sau khi trỏ DNS"
fi

if [[ "$err" -ne 0 ]]; then
  echo "Preflight FAILED."
  exit 1
fi
echo "Preflight OK — có thể chạy ./ops/deploy.sh [--ssl]"
