# SESSION — DropZone

> Read first, update last. Current-state block under 15 lines. It is a prompt, not a history.

## Current state
- Core **v0.2.17 (nightly)**: thumbnails made by the uploader's browser (BACKLOG 18, v0.2.16) plus a field test page for several downloads from one tap (U4): tap the header's version number, then the TEST button. [verified: `tests/test_thumb.py` 14/14; headless Edge checks on the PC, 2026-11-12] Not pushed.
- Thumbnails in the field (Gabe, v0.2.16): portrait upright, look right, delay acceptable; some videos black, taken as fade-ins. [verified: Gabe's report; phones unrecorded] iPhone, undecodable file, removal and memory not yet reported. [assumed: pending]
- Field logging: `upload start` and every thumbnail line carry the User-Agent; a thumbnail that fails in a guest's browser is reported and logged with its reason. [verified: test + Edge check] Android Chrome's User-Agent hides the phone model, so Gabe notes model against the page's user name.
- APK `android\DropZone-debug.apk` built 2026-11-12 14:39 as `0.1.05-dz0.2.17` (wrapper 0.1.05: Copy button confirms with "Copied"); not installed by the agent. [verified: build output]
- Tests on v0.2.17: 5 of 6 pass on Windows through a scratch shim; `test_zip_streaming.py` not run (cannot run on Windows); memory not measured (needs Linux). [verified: shim run 2026-11-12] No Linux run of `tests/run_all.py` yet; Termux is now a test bench only. [assumed: would pass]
- Designed, not built: tap regions, peek, selection, one list-wide download button (`UNEXPLORED_IDEAS.md` U1); the per-row download arrow's fate waits on the multi-download field test (U4).
- M1 Android app merged in (2026-11-11): `android\build.bat` builds from the repo's own `DropZone.py`. [verified: build + odd-filename round trip on PC and phone] Build on the phone `0.1.04-dz0.2.15`: screen restyled after the web page (three-row card, Copy button, version footer, light/dark) plus a Battery notice shown until the phone's battery restriction is lifted (the Xiaomi froze the app without it — LOG Session 3; fixed by App info > Power > No restrictions, 34 transfers with no freeze [verified: greezer history 2026-11-11]). Installed on phone `fc0f334f`. [verified: emulator + phone screenshots 2026-11-11; screen accepted by Gabe as is, including the lighter bold on the Xiaomi]
- M1 field so far: one phone, by script — 2.6 GB up and down byte-exact with the screen off, app memory flat. [verified: sha256, 2026-11-11] Second phone and browser-driven checks pending. [assumed: pending]
- BACKLOG 10 (duplicate downloads, v0.2.14): Android Downloads-folder eyeball and iPhone check still owed. [assumed: pending]

## Open user questions
- Keep or remove the wake lock + WiFi lock the app holds while the server runs (added without a request)? [assumed: keep]
- DropZone-Android is retired and checked as safe to delete. Gabe deletes `PROJECTS\DropZone-Android` (Windows locked it on 2026-11-11) and the GitHub repo `visualcurrent/DropZone-Android` (browser shows 404; see LOG 2026-11-11 Retire). [verified: LOG entry]
- Audit decision (BACKLOG 8): keep or remove Range support wholesale — depends on whether Safari/resume matters. [assumed: pending]

## Resume
- Next action: take Gabe's multi-download counts per phone (files arrived out of files started) and read `files/DropZone.log` for `multi-test`, `thumb saved` and `thumb FAILED` lines; the result decides U1's open point (does the per-row arrow stay). Then the M1 open items.
- Read: PLAN.md > Backlog — active, item 18 (its DoD is the field gate).
- Read: SCRIPT_INDEX.md > DropZone.py map > Thumbnails in the page script, for any fix to rotation or video frames.
- Read: PLAN.md > M1 — Android app (sideloadable APK).
- Read: ARCHITECTURE.md > Contracts to preserve (7-9 are the Android ones) before any change to module-level names in `DropZone.py`.
- Read: SCRIPT_INDEX.md > `android/...` rows for the wrapper and build files.
- Pending gate: multi-download, user-run — on Android Chrome and iPhone Safari, with 5 files shared by someone else, tap the version number then the TEST button; pass on a phone is all 5 files arriving.
- Pending gate: thumbnails, user-run (partly reported) — from Android Chrome and iPhone Safari upload a JPEG, a PNG, a portrait photo and an MP4; a second device shows each thumbnail, portrait upright; an undecodable file keeps its icon; removing a file removes its row; log memory at "upload done" stays 12–16 MB.
- Pending gate: M1 field gate, user-run — on each test phone a multi-GB upload and download byte-exact with the screen off, app not killed, each file downloads once in the browser.
