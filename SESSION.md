# SESSION — DropZone

> Read first, update last. Current-state block under 15 lines. It is a prompt, not a history.

## Current state
- Core **v0.2.15 (nightly)**: fixes single-file download of names outside latin-1 (BACKLOG 16). [verified: `tests/test_download_filename.py` 17/17, 2026-11-11] Pushed and on the Termux phone. [verified: Gabe's report]
- Tests on v0.2.15: 4 of 5 pass on Windows through a scratch shim; `test_zip_streaming.py` not run (cannot run on Windows); memory not measured (needs Linux). [verified: shim runs 2026-11-11] No Linux/Termux run of `tests/run_all.py` on v0.2.15 yet. [assumed: would pass — zip and upload code untouched]
- M1 Android app merged in (2026-11-11): `android\build.bat` builds `0.1.02-dz0.2.15` from the repo's own `DropZone.py`; installed and running on phone `fc0f334f`. [verified: build + odd-filename round trip on PC and phone]
- M1 field so far: one phone, by script — 2.6 GB up and down byte-exact with the screen off, app memory flat. [verified: sha256, 2026-11-11] Second phone and browser-driven checks pending. [assumed: pending]
- BACKLOG 10 (duplicate downloads, v0.2.14): Android Downloads-folder eyeball and iPhone check still owed. [assumed: pending]

## Open user questions
- Keep or remove the wake lock + WiFi lock the app holds while the server runs (added without a request)? [assumed: keep]
- DropZone-Android is retired and checked as safe to delete. Gabe deletes `PROJECTS\DropZone-Android` (Windows locked it on 2026-11-11) and the GitHub repo `visualcurrent/DropZone-Android` (browser shows 404; see LOG 2026-11-11 Retire). [verified: LOG entry]
- Audit decision (BACKLOG 8): keep or remove Range support wholesale — depends on whether Safari/resume matters. [assumed: pending]

## Resume
- Next action: take Gabe's field result for the second phone; then the first M1 open item (guard test for `dz_host.py`'s core names), then BACKLOG 4 (host connected-users panel).
- Read: PLAN.md > M1 — Android app (sideloadable APK).
- Read: ARCHITECTURE.md > Contracts to preserve (7-9 are the Android ones) before any change to module-level names in `DropZone.py`.
- Read: SCRIPT_INDEX.md > `android/...` rows for the wrapper and build files.
- Pending gate: M1 field gate, user-run — on each test phone a multi-GB upload and download byte-exact with the screen off, app not killed, each file downloads once in the browser.
