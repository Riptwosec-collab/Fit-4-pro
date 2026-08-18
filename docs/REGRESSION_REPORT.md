# Regression / Validation Report — PC Remote Deck Only

## Scope

Repository นี้ถูกแยกให้เหลือเฉพาะ **PC Remote Deck** แล้ว

Field Core / Bio / Sport / Outdoor / Tactical navigation modules ถูกนำออกจาก Watch catalog, Watch UI และ Watch runtime logic ของ repo นี้

## Preserved PC Remote Deck baseline

- Favorites / quick controls
- PC Monitor
- Media controls
- Air Mouse
- D-Pad
- Pro Tools
- Terminal shortcuts
- App Launcher
- Stream Hub
- Camera Pro
- AI Limits
- Context Aware
- Smart Room
- Asset Radar
- Protocol Engine actions
- Motion Command
- Voice Command
- Network Status
- Wi-Fi Recon
- System / System Log
- Command System

## Current module set

22 feature IDs:

```text
0,1,2,3,4,5,6,7,8,9,10,11,12,14,15,18,21,23,25,26,31,39
```

## Removed from this repository

- Bio Telemetry / Daily Hub / Sleep
- Running / Sports HUD / Aqua / Golf
- Navigation / Silent Nav / Tactical Nav
- Atmospheric / Acoustic
- Depth HUD / Tactical Light / Grid-Down
- Field Systems / Breadcrumb / Geo Anchor
- Solar / Thermal / Altitude / Transit / Sky / Emergency
- Field legacy baseline

## Validation rules

`tools/preflight.py` now checks:

- Lite Wearable device type
- HML XML parse
- exactly 22 PC Remote Deck feature IDs
- expected PC-only ID set
- Field Core module names are not exposed in Watch UI/catalog
- identity placeholders
- official Wear Engine SDK replacement
- PC Agent token presence

## Security preserved

- PC Agent remains whitelist-only
- no arbitrary shell endpoint
- Wi-Fi Recon keeps `OPEN != FREE VERIFIED`
- Wi-Fi raw scan processing stays on Android side

## Still requires physical environment

- DevEco/Hvigor Watch build
- Android Gradle APK build
- Huawei signing
- real FIT 4 Pro pairing
- end-to-end Watch → Phone → PC test

These remain `NOT RUN` until executed on the user's real development machine/device.
