$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".\agent_config.json")) {
    python .\generate_token.py
}

$discovery = Start-Process python -ArgumentList ".\discovery_service.py" -PassThru -WindowStyle Hidden
Write-Host "Discovery service started (PID $($discovery.Id), UDP 8766)"
Write-Host "Starting PC Remote Deck V8 Pro Agent..."
try {
    python .\pc_agent_pro.py
}
finally {
    if ($discovery -and -not $discovery.HasExited) { Stop-Process -Id $discovery.Id -Force }
}
