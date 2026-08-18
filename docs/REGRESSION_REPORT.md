# Regression / Validation Report — V6

## Preserved
- PC Remote Deck remains separate from Field Core.
- Existing PC media, lock, screenshot, keyboard, app launch, protocols, Motion Command, Voice, Network and Wi-Fi Recon concepts remain.
- Security remains whitelist-only; no arbitrary shell endpoint added.

## Added
- 27 PC Remote Deck modules in Watch catalog.
- PC dashboard / windows / audio / network / context / macros / notifications.
- Air Mouse gyro streaming.
- Android auto-sync, local PC-link persistence, macro builder and bilingual Voice.

## Static validation performed before publish
- `python -m py_compile pc_agent.py`: PASS
- `node --check featureCatalog.js`: PASS
- `node --check index.js`: PASS
- Watch HML XML parse: PASS
- Brace-balance checks for edited Android Java: PASS (not a substitute for Android Gradle compilation)

## Not claimed as PASS in this environment
- Android Gradle build: NOT RUN (Android SDK/toolchain unavailable here)
- DevEco/Hvigor HAP build: NOT RUN
- Huawei signing / physical FIT 4 Pro end-to-end: NOT RUN
- Windows runtime telemetry behavior on a real Windows host: NOT RUN in this Linux tool environment
