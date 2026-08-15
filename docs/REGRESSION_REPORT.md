# Regression / Validation Report — REAL V5

## Preserved baseline
- Original V4 HTML retained unchanged under `legacy/`
- 49 feature IDs represented in Watch feature catalog
- Existing PC Remote / Bio / Tactical / Sports / Field / Wi‑Fi concepts preserved

## Static checks performed
- Watch JavaScript parsed with `node --check`: PASS
- PC Agent Python compiled with `py_compile`: PASS
- Watch HML parsed as XML: PASS
- Feature catalog IDs 0–48 present: PASS
- No arbitrary shell command endpoint in PC Agent: PASS
- Wi‑Fi classification rule `OPEN != FREE VERIFIED`: PASS by implementation path
- Wi‑Fi full raw scan is not sent to Watch snapshot: PASS

## Not executable in this environment
- DevEco/Hvigor HAP build: NOT RUN (IDE/toolchain unavailable)
- Android Gradle APK build: NOT RUN (Android SDK/Gradle unavailable)
- Huawei signing: NOT RUN (user certificate/app identity required)
- End-to-end real Watch pairing: NOT RUN (physical device unavailable)

These are intentionally reported as NOT RUN rather than PASS.
