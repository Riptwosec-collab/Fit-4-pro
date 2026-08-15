$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host 'Python 3 is required.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path '.\\agent_config.json')) {
    python .\\generate_token.py
}
Write-Host ''
Write-Host 'PC Remote Deck Agent configuration:' -ForegroundColor Cyan
Get-Content .\\agent_config.json
Write-Host ''
Write-Host 'Starting PC Agent on port 8765. Keep this window open.' -ForegroundColor Green
python .\\pc_agent.py
