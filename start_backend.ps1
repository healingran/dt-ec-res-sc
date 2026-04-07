<#!
  EdgeTwin：启动 FastAPI 后端（默认 127.0.0.1:8000）
  用法：
    .\start_backend.ps1              # 激活 .venv（若存在）并运行 python main.py
    .\start_backend.ps1 -HealthOnly  # 仅检测 /openapi.json 是否可访问
#>
param(
    [switch]$HealthOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if ($HealthOnly) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/openapi.json" -UseBasicParsing -TimeoutSec 5 | Out-Null
        Write-Host "[health] OK - http://127.0.0.1:8000/openapi.json"
        exit 0
    }
    catch {
        Write-Host "[health] FAIL - backend not reachable on port 8000"
        exit 1
    }
}

$venvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
    Write-Host "[start] Using virtualenv: .venv"
}
else {
    Write-Host "[start] No .venv found; using current Python on PATH"
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[start] ERROR: python not found on PATH"
    exit 1
}

$port = 8000
try {
    $probe = New-Object System.Net.Sockets.TcpClient
    $probe.Connect("127.0.0.1", $port)
    if ($probe.Connected) {
        Write-Host "[start] WARNING: port $port already accepts connections. Stop the other process or change port in main.py."
    }
    $probe.Close()
}
catch {
    # 拒绝连接表示端口空闲，可启动
}

Write-Host "[start] Starting: python main.py (http://127.0.0.1:$port/docs)"
python main.py
