#!/usr/bin/env python3
"""Chay TREN VPS host — do GET /api/employees qua HTTPS.

Tach TTFB (server nghi) khoi transfer (tai payload), va do theo so dong tra ve de
biet chi phi la co dinh hay tang theo tung NV.
"""
import json
import statistics
import subprocess

BASE = "https://hrm.dongju-v.com"
RUNS = 5

login = subprocess.check_output(
    [
        "curl", "-sk", "-X", "POST", f"{BASE}/api/auth/login",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"username": "hr.demo", "password": "demo123456"}),
    ]
)
token = json.loads(login)["access_token"]
AUTH = f"Authorization: Bearer {token}"
FMT = "%{time_appconnect} %{time_starttransfer} %{time_total} %{size_download}"


def measure(url: str, gzip: bool = True) -> dict:
    rows = []
    for _ in range(RUNS):
        cmd = ["curl", "-sk", "-o", "/dev/null", "-w", FMT, "-H", AUTH]
        if gzip:
            cmd += ["-H", "Accept-Encoding: gzip"]
        cmd.append(url)
        rows.append([float(x) for x in subprocess.check_output(cmd).decode().split()])
    ttfb = statistics.median(r[1] for r in rows)
    total = statistics.median(r[2] for r in rows)
    return {
        "tls_ms": round(statistics.median(r[0] for r in rows) * 1000, 1),
        "ttfb_ms": round(ttfb * 1000, 1),
        "transfer_ms": round((total - ttfb) * 1000, 1),
        "total_ms": round(total * 1000, 1),
        "download_kb": round(statistics.median(r[3] for r in rows) / 1024, 1),
    }


def row_count(url: str) -> int:
    out = subprocess.check_output(["curl", "-sk", "-H", AUTH, url])
    try:
        data = json.loads(out)
        return len(data) if isinstance(data, list) else -1
    except Exception:
        return -1


targets = {
    "health": f"{BASE}/health",
    "employees 0 dong": f"{BASE}/api/employees?q=zzz-khong-co-ai",
    "employees 1 dong": f"{BASE}/api/employees?q=1519",
    "employees day du": f"{BASE}/api/employees",
}

out: dict[str, dict] = {}
for label, url in targets.items():
    m = measure(url)
    if "/api/employees" in url:
        m["rows"] = row_count(url)
    out[label] = m
out["employees day du (khong gzip)"] = measure(f"{BASE}/api/employees", gzip=False)

print(json.dumps(out, indent=2, ensure_ascii=False))
