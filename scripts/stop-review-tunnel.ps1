$ErrorActionPreference = 'Stop'
$pidFile = Join-Path (Split-Path $PSScriptRoot -Parent) 'tmp/review-tunnel.pid'
if (!(Test-Path $pidFile)) { Write-Output 'No hay túnel registrado.'; exit 0 }
$tunnelPid = [int](Get-Content $pidFile)
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $tunnelPid"
if ($process -and $process.Name -eq 'cloudflared.exe' -and $process.CommandLine -like '*http://127.0.0.1:3000*') {
    Stop-Process -Id $tunnelPid
    Write-Output 'Enlace de revisión desactivado.'
} else { Write-Output 'El proceso registrado ya no corresponde al túnel.' }
