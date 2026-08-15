param(
    [string]$HuaweiAppId = "",
    [string]$AndroidFingerprint = "",
    [string]$WatchFingerprint = "",
    [switch]$StartPcAgent,
    [switch]$BuildAndroid,
    [switch]$InstallAndroid,
    [switch]$OpenWatchProject
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Banner($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Has-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Find-Executable($candidates) {
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    return $null
}

Banner "PC REMOTE DECK - FIT 4 PRO REAL DEVICE INSTALL"
Write-Host "Repository: $Root"

Banner "1. PREREQUISITE CHECK"
$pythonOk = Has-Command "python"
$javaOk   = Has-Command "java"
$keytoolOk = Has-Command "keytool"
$adbOk    = Has-Command "adb"

Write-Host ("Python   : " + ($(if($pythonOk){"OK"}else{"MISSING"})))
Write-Host ("Java     : " + ($(if($javaOk){"OK"}else{"MISSING"})))
Write-Host ("keytool  : " + ($(if($keytoolOk){"OK"}else{"MISSING"})))
Write-Host ("ADB      : " + ($(if($adbOk){"OK"}else{"OPTIONAL / NOT FOUND"})))

if (-not $pythonOk) {
    throw "Python 3 is required. Install Python 3 and rerun this script."
}

$androidStudio = Find-Executable @(
    "$env:ProgramFiles\Android\Android Studio\bin\studio64.exe",
    "$env:LOCALAPPDATA\Programs\Android Studio\bin\studio64.exe"
)
$devEco = Find-Executable @(
    "$env:ProgramFiles\Huawei\DevEco Studio\bin\devecostudio64.exe",
    "$env:LOCALAPPDATA\Huawei\DevEco Studio\bin\devecostudio64.exe",
    "$env:LOCALAPPDATA\Programs\Huawei\DevEco Studio\bin\devecostudio64.exe"
)

Write-Host ("Android Studio : " + ($(if($androidStudio){$androidStudio}else{"NOT FOUND - manual open may be required"})))
Write-Host ("DevEco Studio  : " + ($(if($devEco){$devEco}else{"NOT FOUND - install/open manually"})))

Banner "2. PC AGENT TOKEN"
$agentConfig = Join-Path $Root "pc-agent\agent_config.json"
if (-not (Test-Path $agentConfig)) {
    Push-Location (Join-Path $Root "pc-agent")
    python generate_token.py
    Pop-Location
    Write-Host "Created pc-agent/agent_config.json (gitignored)." -ForegroundColor Green
} else {
    Write-Host "Existing pc-agent/agent_config.json preserved." -ForegroundColor Yellow
}

$agent = Get-Content $agentConfig -Raw | ConvertFrom-Json
Write-Host "PC Agent port: $($agent.port)"
Write-Host "PC token created/preserved locally. Do NOT commit it."

Banner "3. HUAWEI IDENTITY"
$haveIdentity = $HuaweiAppId -and $AndroidFingerprint -and $WatchFingerprint
if ($haveIdentity) {
    python tools/configure_identity.py `
        --huawei-app-id $HuaweiAppId `
        --android-fingerprint $AndroidFingerprint `
        --watch-fingerprint $WatchFingerprint
    Write-Host "Huawei identity values patched into local source." -ForegroundColor Green
} else {
    Write-Host "Identity not supplied yet." -ForegroundColor Yellow
    Write-Host "Required before real Wear Engine communication:"
    Write-Host "  - Huawei App ID"
    Write-Host "  - Android signing SHA-256 fingerprint"
    Write-Host "  - Watch/Lite Wearable signing SHA-256 fingerprint"
    Write-Host "Rerun example:"
    Write-Host '.\REAL_DEVICE_INSTALL.ps1 -HuaweiAppId "123456789" -AndroidFingerprint "AA:BB:..." -WatchFingerprint "11:22:..." -BuildAndroid -InstallAndroid -OpenWatchProject'
}

Banner "4. PREFLIGHT"
python tools/preflight.py

if ($StartPcAgent) {
    Banner "5. START WINDOWS PC AGENT"
    $agentScript = Join-Path $Root "pc-agent\pc_agent.py"
    Start-Process powershell -ArgumentList @("-NoExit", "-Command", "python `"$agentScript`"")
    Write-Host "PC Agent started in a new PowerShell window." -ForegroundColor Green
}

if ($BuildAndroid) {
    Banner "6. BUILD ANDROID COMPANION"
    $gradlew = Join-Path $Root "android-companion\gradlew.bat"
    if (Test-Path $gradlew) {
        Push-Location (Join-Path $Root "android-companion")
        & .\gradlew.bat assembleDebug
        Pop-Location
    } elseif ($androidStudio) {
        Write-Host "Gradle wrapper is not present. Opening Android Studio for Sync/Build." -ForegroundColor Yellow
        Start-Process $androidStudio -ArgumentList (Join-Path $Root "android-companion")
    } else {
        Write-Host "Open android-companion/ in Android Studio and Build APK manually." -ForegroundColor Yellow
    }
}

if ($InstallAndroid) {
    Banner "7. INSTALL ANDROID APK TO PHONE"
    $apks = Get-ChildItem -Path (Join-Path $Root "android-companion") -Recurse -Filter *.apk -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if (-not $apks) {
        Write-Host "No APK found yet. Build Android Companion first." -ForegroundColor Yellow
    } elseif (-not $adbOk) {
        Write-Host "ADB not found. Install Android SDK Platform Tools or install the APK manually on the paired phone." -ForegroundColor Yellow
    } else {
        $apk = $apks[0].FullName
        Write-Host "Using APK: $apk"
        adb devices
        adb install -r "$apk"
    }
}

if ($OpenWatchProject) {
    Banner "8. OPEN WATCH PROJECT"
    if ($devEco) {
        Start-Process $devEco -ArgumentList (Join-Path $Root "watch-lite")
        Write-Host "DevEco Studio opened. Sign the Lite Wearable app and select the real wearable deployment target." -ForegroundColor Green
    } else {
        Write-Host "Open watch-lite/ in DevEco Studio manually." -ForegroundColor Yellow
    }
}

Banner "REAL DEVICE FINAL CHECK"
Write-Host "For the actual FIT 4 Pro install, these steps are intentionally interactive because Huawei validates package name, App ID, and signing certificate fingerprint." -ForegroundColor White
Write-Host "1) Phone is paired with FIT 4 Pro in HUAWEI Health"
Write-Host "2) Android Companion is signed with the registered Android certificate"
Write-Host "3) Watch app is signed with the registered Lite Wearable certificate"
Write-Host "4) Official Wear Engine wearengine.js replaces the offline stub"
Write-Host "5) Install/run Android Companion on phone"
Write-Host "6) In DevEco Studio choose the real wearable target and Run/Install the watch app"
Write-Host "7) Authorize Wear Engine and register the watch in the Companion app"
Write-Host "8) Start PC Agent and test LOCK / PLAY / WI-FI RECON end-to-end"

Write-Host "`nThe script cannot bypass Huawei signing/account/device authorization and will never upload your keys or tokens." -ForegroundColor Green
