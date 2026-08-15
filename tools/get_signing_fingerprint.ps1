param(
    [Parameter(Mandatory=$true)][string]$Keystore,
    [string]$Alias = ""
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command keytool -ErrorAction SilentlyContinue)) {
    throw "keytool not found. Install a JDK and reopen PowerShell."
}
if (-not (Test-Path $Keystore)) {
    throw "Keystore not found: $Keystore"
}

Write-Host "Reading signing certificate fingerprint from:" -ForegroundColor Cyan
Write-Host $Keystore
Write-Host "keytool will ask for the keystore password interactively; the password is not saved by this script." -ForegroundColor Yellow

$args = @('-list','-v','-keystore',$Keystore)
if ($Alias) { $args += @('-alias',$Alias) }
& keytool @args | Select-String -Pattern 'SHA256:|SHA-256:'

Write-Host "Use the SHA-256 value with REAL_DEVICE_INSTALL.ps1 and Huawei Developer configuration." -ForegroundColor Green
