# V6 Upgrade — PC Control OS on the Wrist

## Implemented

1. **PC Monitor Pro** — dashboard action returns CPU, GPU best-effort counter, RAM, disk, network, active app, context, top processes, notifications.
2. **Audio Mixer Pro** — master media keys always available; per-app sessions enabled when optional `pycaw` is installed.
3. **Window Center** — enumerates visible top-level windows and validates HWND before focus/min/max/close.
4. **Air Mouse Pro** — Watch gyroscope samples are throttled (~120 ms) and sent as bounded relative cursor deltas.
5. **Macro Deck Builder** — Android saves only 1–12 macro steps and PC validates every step against `SAFE_MACRO_ACTIONS`.
6. **Context Engine** — profiles Browser/Dev/Media/Game/Meeting/Generic with four safe contextual slots.
7. **Protocol Engine V2** — Battle/Focus plus stored macros.
8. **Voice Command Pro** — Thai/English intents; risk actions require phone confirmation.
9. **App Launcher Pro** — PC-local definitions in ignored `apps.json`; examples in `apps.example.json`.
10. **Network Command Center** — IP/gateway/DNS, throughput delta and ping.
11. **Wi-Fi Recon Pro** — preserves OPEN != FREE VERIFIED; adds per-SSID RSSI trend.
12. **Watch Home V2** — live compact command dashboard.
13. **Companion Auto Sync** — SharedPreferences persistence and 12-second dashboard refresh while Companion process/activity is alive.
14. **Trust Center** — displays local trust state and can revoke stored PC link.
15. **Notification Bridge** — local PC agent alert queue exposed to Watch.

## Explicit limitations

- GPU and temperature values are best-effort Windows telemetry and may return null on unsupported drivers/hardware.
- Output-device switching is not implemented; current output name is informational. Master volume keys and optional per-app mixer are implemented.
- Background Android auto-sync after the app process is killed is not claimed. A foreground/background service can be added later if desired.
- AI Limits, Smart Room, Camera Pro, Asset Radar and OBS scene provider remain explicit extension points if their external provider is not configured.
