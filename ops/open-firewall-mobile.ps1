# Mở cổng DJ-HRM cho điện thoại trong LAN (chạy PowerShell **Run as Administrator**)
# Sau khi chạy: ĐT mở http://<IP-máy-tính>:5173/worker/login (cùng WiFi nhà máy)

$ErrorActionPreference = "Stop"

$rules = @(
    @{ Name = "DJ-HRM Web 5173"; Port = 5173 },
    @{ Name = "DJ-HRM API 8000"; Port = 8000 }
)

foreach ($r in $rules) {
    $existing = netsh advfirewall firewall show rule name=$($r.Name) 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Rule already exists: $($r.Name)"
        continue
    }
    netsh advfirewall firewall add rule name=$($r.Name) dir=in action=allow protocol=TCP localport=$($r.Port)
    Write-Host "Added: $($r.Name) TCP $($r.Port)"
}

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.IPAddress -like "192.168.*" -and $_.PrefixOrigin -ne "WellKnown"
    } | Select-Object -First 1).IPAddress

if (-not $ip) {
    $ip = "192.168.1.123"
}

Write-Host ""
Write-Host "Done. On phone (same WiFi), open:"
Write-Host "  http://${ip}:5173/worker/login"
Write-Host "MSNV + password 1234 (first login)."
