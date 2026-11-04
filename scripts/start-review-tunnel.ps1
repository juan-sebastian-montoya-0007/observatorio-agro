$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$logs = Join-Path $root 'tmp'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$pidFile = Join-Path $logs 'review-tunnel.pid'
if (Test-Path $pidFile) {
    $previous = Get-Process -Id ([int](Get-Content $pidFile)) -ErrorAction SilentlyContinue
    if ($previous -and $previous.ProcessName -eq 'cloudflared') {
        Write-Output 'El túnel ya está ejecutándose. Consulta tmp/review-tunnel.err.log para ver el enlace.'
        exit 0
    }
}
Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:3000/api/v1/agriculture/summary?year_from=2025&year_to=2025' -TimeoutSec 30 | Out-Null
$binary = (Get-Command cloudflared -ErrorAction Stop).Source
$process = Start-Process -FilePath $binary -ArgumentList @('tunnel','--url','http://127.0.0.1:3000','--no-autoupdate') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'review-tunnel.out.log') -RedirectStandardError (Join-Path $logs 'review-tunnel.err.log')
$process.Id | Set-Content $pidFile
Write-Output 'Túnel iniciado. El enlace aparecerá en tmp/review-tunnel.err.log. Quien tenga el enlace podrá acceder.'
