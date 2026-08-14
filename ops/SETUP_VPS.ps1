# Tu may Windows (nha hoac cong ty): tu dong SSH len VPS AZVPS va cai dj-hrm.
# Truoc khi chay: tao ops\vps-root.txt (xem ops\vps-root.txt.example)
param(
    [switch]$SkipSsl
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$CredFile = Join-Path $Root "ops\vps-root.txt"
$Example = Join-Path $Root "ops\vps-root.txt.example"

if (-not (Test-Path $CredFile)) {
    Write-Host ""
    Write-Host "Chua co ops\vps-root.txt" -ForegroundColor Yellow
    Write-Host "Copy tu example va dien IP + mat khau root VPS:" -ForegroundColor Yellow
    Write-Host "  $Example" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

$lines = Get-Content $CredFile | Where-Object { $_ -and -not $_.TrimStart().StartsWith("#") }
if ($lines.Count -lt 2) {
    Write-Host "vps-root.txt can it nhat 2 dong: IP va mat khau root" -ForegroundColor Red
    exit 1
}

$VpsIp = $lines[0].Trim()
$VpsPass = $lines[1].Trim()
$Domain = "hrm.dongju-v.com"
if ($lines.Count -ge 3 -and $lines[2].Trim()) { $Domain = $lines[2].Trim() }
$AgentToken = "DjHrm-Mitapro-20260812-571983"
if ($lines.Count -ge 4 -and $lines[3].Trim()) { $AgentToken = $lines[3].Trim() }

function New-Secret([int]$Len = 32) {
    $chars = (48..57) + (65..90) + (97..122)
    -join (1..$Len | ForEach-Object { [char]($chars | Get-Random) })
}

$Jwt = New-Secret 40
$PgPass = New-Secret 24
$AdminPass = New-Secret 16

$EnvContent = @"
APP_ENV=production
APP_NAME=DJ HRM
POSTGRES_USER=djhrm
POSTGRES_PASSWORD=$PgPass
POSTGRES_DB=djhrm
JWT_SECRET=$Jwt
JWT_ACCESS_HOURS=8
JWT_REFRESH_DAYS=7
CORS_ORIGINS=https://$Domain
TRUSTED_HOSTS=$Domain,localhost
AGENT_TOKEN=$AgentToken
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$AdminPass
ADMIN_FULL_NAME=Nguyen Thanh Thien
WEB_PUBLISH_PORT=8080
LOG_DIR=/var/log/djhrm
DOCS_ENABLED=false
DOMAIN=$Domain
CADDY_EMAIL=admin@dongju-v.com
"@

$EnvLocal = Join-Path $Root "ops\djhrm-vps.env"
$EnvContent | Out-File -FilePath $EnvLocal -Encoding utf8

Write-Host "== SETUP VPS $VpsIp ==" -ForegroundColor Green

if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Write-Host "Cai Posh-SSH (lan dau)..." -ForegroundColor Yellow
    Install-Module -Name Posh-SSH -Scope CurrentUser -Force -AllowClobber
}
Import-Module Posh-SSH

$SecPass = ConvertTo-SecureString $VpsPass -AsPlainText -Force
$Cred = New-Object System.Management.Automation.PSCredential("root", $SecPass)

$session = $null
try {
    Write-Host "-> Ket noi SSH..."
    $session = New-SSHSession -ComputerName $VpsIp -Credential $Cred -AcceptKey -ConnectionTimeout 60
    if (-not $session) { throw "Khong ket noi duoc SSH - kiem tra IP, mat khau, VPS da bat chua." }

    Write-Host "-> Upload file..."
    Set-SCPItem -ComputerName $VpsIp -Credential $Cred -AcceptKey `
        -Path (Join-Path $Root "ops\bootstrap-vps.sh") -Destination "/root/bootstrap-vps.sh"
    Set-SCPItem -ComputerName $VpsIp -Credential $Cred -AcceptKey `
        -Path $EnvLocal -Destination "/root/djhrm-vps.env"

    $Dump = Join-Path $Root "backups\djhrm_local_latest.dump"
    if (Test-Path $Dump) {
        $dumpKb = [math]::Round((Get-Item $Dump).Length / 1KB)
        Write-Host "-> Upload backup DB ($dumpKb KB)..."
        Set-SCPItem -ComputerName $VpsIp -Credential $Cred -AcceptKey `
            -Path $Dump -Destination "/root/djhrm_local_latest.dump"
    } else {
        Write-Host "Khong thay backups\djhrm_local_latest.dump - VPS se seed demo." -ForegroundColor Yellow
    }

    Write-Host "-> Chay bootstrap tren VPS (5-15 phut)..."
    $cmd = "chmod +x /root/bootstrap-vps.sh && bash /root/bootstrap-vps.sh"
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command $cmd -TimeOut 900
    Write-Host $result.Output
    if ($result.Error) { Write-Host $result.Error -ForegroundColor DarkYellow }
    if ($result.ExitStatus -ne 0) {
        Write-Host "Bootstrap co loi (exit $($result.ExitStatus)) - xem output tren." -ForegroundColor Red
        exit $result.ExitStatus
    }

    Write-Host ""
    Write-Host "=== XONG ===" -ForegroundColor Green
    Write-Host "  URL:      https://$Domain  (hoac http://${VpsIp}:8080 neu chua SSL)"
    Write-Host "  Admin:    admin / $AdminPass"
    Write-Host "  Agent:    DJ_AGENT_TOKEN=$AgentToken"
    Write-Host ""
    Write-Host "Luu mat khau admin vao password manager - khong commit file nay." -ForegroundColor Yellow
    $CredOut = Join-Path $Root "ops\vps-admin-credentials.txt"
    @(
        "VPS IP: $VpsIp"
        "Domain: https://$Domain"
        "Admin: admin / $AdminPass"
        "AGENT_TOKEN: $AgentToken"
        "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    ) | Out-File -FilePath $CredOut -Encoding utf8
    Write-Host "Da ghi ops\vps-admin-credentials.txt (local, gitignore)"
}
finally {
    if ($session) { Remove-SSHSession -SessionId $session.SessionId | Out-Null }
}
