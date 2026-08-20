#!/usr/bin/env bash
# UAT live API — hr.demo
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8000}"
LOGIN=$(curl -sf -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"username":"hr.demo","password":"HrDemo@123456"}')
TOKEN=$(echo "$LOGIN" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
H=(-H "Authorization: Bearer $TOKEN")
PASS=0
FAIL=0

check() {
  local name="$1" method="$2" path="$3" expect="$4"
  local body="${5:-}"
  local code
  if [ "$method" = GET ]; then
    code=$(curl -s -o /tmp/hr_uat_body.txt -w "%{http_code}" "${H[@]}" "$BASE$path")
  else
    code=$(curl -s -o /tmp/hr_uat_body.txt -w "%{http_code}" -X POST "${H[@]}" -H 'Content-Type: application/json' \
      -d "$body" "$BASE$path")
  fi
  if [ "$code" = "$expect" ]; then
    echo "OK  $name ($code)"
    PASS=$((PASS+1))
  else
    echo "FAIL $name expected=$expect got=$code $(head -c 120 /tmp/hr_uat_body.txt)"
    FAIL=$((FAIL+1))
  fi
}

echo "=== HR live UAT @ $BASE ==="
check "portal tabs" GET /api/portal/tabs 200
check "employees" GET /api/employees 200
check "departments" GET /api/departments 200
check "attendance days" GET "/api/attendance/days?from=2025-10-01&to=2025-10-31" 200
check "payslips" GET "/api/payroll/payslips?period=2025-10" 200
# GET kỳ chưa tính → 404 (không tự INSERT). Đã tính lương → 200.
code=$(curl -s -o /tmp/hr_uat_body.txt -w "%{http_code}" "${H[@]}" "$BASE/api/payroll/periods/2025-10")
if [ "$code" = "200" ] || [ "$code" = "404" ]; then
  echo "OK  payroll period ($code)"
  PASS=$((PASS+1))
else
  echo "FAIL payroll period expected=200|404 got=$code $(head -c 120 /tmp/hr_uat_body.txt)"
  FAIL=$((FAIL+1))
fi
check "disputes" GET /api/disputes 200
check "insurance" GET "/api/insurance/declarations?effective_month=2025-10" 200
check "kpi" GET "/api/reports/kpi?period=2025-10" 200
check "ai todos" GET /api/ai/todos 200
check "ai alerts" GET /api/ai/alerts/mine 200
check "config denied" GET /api/config/roles 403
check "users denied" GET /api/users 403
check "ai query denied" POST /api/ai/query 403 '{"message":"test"}'
check "contracts" GET /api/labour-contracts 200
# Resignations are per-employee, not a global list
EMP_ID=$(curl -sf "${H[@]}" "$BASE/api/employees" | python3 -c 'import sys,json; print(next(e["id"] for e in json.load(sys.stdin) if e["employee_code"]=="5290"))')
check "resignations list" GET "/api/employees/$EMP_ID/resignations" 200
echo "--- $PASS pass, $FAIL fail ---"
[ "$FAIL" -eq 0 ]
