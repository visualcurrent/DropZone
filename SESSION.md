# SESSION — DropZone

> Read first, update last. Current-state block under 15 lines. It is a prompt, not a history.

## Current state
- Source is **core v0.2.22, wrapper 0.1.06**; `android\DropZone-debug.apk` is `0.1.06-dz0.2.22`, installed on the Samsung `RFCXA10KBPZ` as an update (main profile only, log, files and battery setting kept); the Xiaomi updated the same way to `0.1.06-dz0.2.22`. Nothing since 2026-11-12 is pushed. [verified: build output, `dumpsys package`, `deviceidle whitelist`, `git log`]
- Stopped-host notice (PLAN Backlog 19, v0.2.20): PASSED on phones, "pages react to host presence". [verified: Gabe 2026-11-16; which devices and the timing not stated] v0.2.22: the page shows the version number alone, no stage label; app 0.1.06 drops it from the app's footer too; the label stays in the log and the console banner. [verified: page text checked by script] Tests not run since v0.2.18. [assumed: unaffected]
- v0.2.16 thumbnails (BACKLOG 18): the uploader's browser posts a 320 px JPEG to `/api/thumb`; rows show a 48 px square. [verified: `tests/test_thumb.py` 14/14; headless Edge check] Field (Gabe, v0.2.16): portrait upright, look right, delay acceptable, some videos black. [verified: Gabe's report; phones unrecorded] iPhone, undecodable file, removal and memory lines of the DoD not yet reported. [assumed: pending]
- Several separate downloads from one tap (U4) is DROPPED (Gabe, 2026-11-16): Android Firefox keeps 2 to 4 of 5 under every method; iPhone Safari 1 of 5 by link click, 5 of 5 by hidden frames; PC Chrome saves nothing once its permission is blocked. Every file keeps its download button. [verified: Gabe's counts and `multi-test` lines, LOG 2026-11-13 to 2026-11-16; `LESSONS_LEARNED.md` L8] The TEST page and its log tag were removed in v0.2.21. [verified: grep finds no test-page name; headless Edge shows no TEST button]
- v0.2.18 video thumbnails take the frame 10% into the clip instead of 0.1 s in, to get past fade-ins. [est_: script passes `node --check`; never run on a video in any browser]
- Wrapper 0.1.05: Copy button reads "Copied" for 1.5 s. [verified: builds; not yet seen on a phone]
- Field logging: `upload start`, and thumbnail lines carry the User-Agent; a thumbnail that fails in a guest's browser is logged with its reason. Android Chrome hides the phone model, so Gabe notes model against the page's user name. [verified: test + Edge checks]
- Tests on v0.2.18: 5 of 6 pass on Windows through a scratch shim; `test_zip_streaming.py` not run (cannot run on Windows); memory not measured. [verified: shim run 2026-11-12] No Linux run yet; Termux is a test bench only. [assumed: would pass]
- Designed, not built (`UNEXPLORED_IDEAS.md` U1): tap thumbnail = peek, tap row = select, one list-wide download button, header select circles. The per-row download arrow stays (settled 2026-11-16).
- M1 field so far: one phone, by script — 2.6 GB up and down byte-exact, screen off, memory flat. [verified: sha256, 2026-11-11] Second phone, browser-driven checks, and BACKLOG 10's Downloads-folder and iPhone checks still owed. [assumed: pending]

- **DropCast (PLAN M2), new 2026-11-13:** a second app in `android\dropcast\`, `0.1.11-dz0.2.18`, installed on phone `fc0f334f`; APK `android\DropCast-debug.apk`. Share one file, the host's phone shows a QR, a guest downloads and can share one back; the host saves received files; core unedited. Every built step passed Gabe's phone tests except the receive-without-sharing QR, not yet reported. [verified: LOG 2026-11-13] Field gate not run; icon on hold. [assumed: pending]
- DropCast was always built alone (Gradle `:dropcast:assembleDebug`); the edited `build.bat` has never been run and will also rebuild the DropZone APK with core 0.2.18. `dz_host.start` gained `port` and `addon` arguments; DropZone's own app has not been rebuilt or run with that change. [est_: DropZone's call is unchanged]
- Phone-to-PC transfers run at about 5 MB/s; not the app (phone to phone about 47 MB/s). Closed for this project; `HANDOFF_slow_phone_to_pc.md` holds the measurements. [verified: logs 2026-11-13]

## Open user questions
- Reword `README.md`? It still presents Termux as a way to host (6 mentions); `CLAUDE.md` now says test bench only. [assumed: yes, awaiting Gabe's word]
- Which phones and browsers gave the v0.2.16 thumbnail result? [assumed: unknown]
- Keep or remove the wake lock + WiFi lock the app holds while the server runs (added without a request)? [assumed: keep]
- Gabe deletes `PROJECTS\DropZone-Android` and the GitHub repo `visualcurrent/DropZone-Android` (retired; see LOG 2026-11-11 Retire). [verified: LOG entry]
- Audit decision (BACKLOG 8): keep or remove Range support wholesale. [assumed: pending]
- Close M1's slow-download item now that the cause is placed outside the app? [assumed: yes]
- Delete the test copies left by 2026-11-13's transfers: about 5.0 GB in the host phone's `Download` and 2.8 GB in the PC's `Downloads` (listed in LOG 2026-11-13, the 2026-11-14 lines)? The agent deletes nothing without his word. [verified: listings 2026-11-14]
- New names for the DropZone / DropCast pair (Gabe's brainstorm) before the icon work resumes. [verified: Gabe 2026-11-14]

## Resume
- Next action (Gabe): video thumbnail is still black on v0.2.22 (FAIL; flat black at the right size, LOG 2026-11-16 top entry). Upload the same `.mp4` from Chrome on the Samsung and from a PC browser and report black or picture for each; that tells a frame-not-ready cause from a browser that cannot copy video to a canvas, and decides the fix. Also: the footer check on either phone. Decide on `HANDOFF_slow_phone_to_pc.md` (deleted from disk before this session, not committed, still referenced).
- For DropCast instead: read PLAN.md > M2 (status, open items, gate), then SCRIPT_INDEX.md rows under `android/dropcast/`, and ARCHITECTURE.md > Contracts to preserve, 7 (the core names DropCast leans on). Next DropCast action (Gabe): open DropCast with nothing shared and have a guest send a file through the QR it shows; then the M2 field gate.
- Read: UNEXPLORED_IDEAS.md > U1 (agreed design); U4 is dropped (`LESSONS_LEARNED.md` > L8).
- Read: PLAN.md > Backlog — active, item 18 (its DoD is the thumbnail field gate).
- Read: SCRIPT_INDEX.md > DropZone.py map > Thumbnails in the page script, and Host-unreachable notice in the page script.
- Read: ARCHITECTURE.md > Contracts to preserve (7-9 Android, 10 thumbnails) before changing module-level names or the thumbnail routes.
- Pending gate: thumbnails, user-run (partly reported) — iPhone Safari upload of a JPEG, PNG, portrait photo and MP4 shows thumbnails on a second device; an undecodable file keeps its icon; removing a file removes its row; log memory at "upload done" stays 12–16 MB.
- Pending gate: video thumbnail, user-run: a film that thumbnails black on v0.2.22 shows a picture. FAILED on v0.2.22 (Firefox 160 on the Samsung, `.mp4` and `.mkv`); fix waits on the diagnosis above.
- Pending gate: M2 field gate, user-run — DropCast on one phone, two other devices (one iPhone): a 2 GB+ video down byte-exact with the host's screen off, a guest's file back and saved byte-exact, no internet on the WiFi, Stop leaves the app's storage empty.
- Pending gate: M1 field gate, user-run — on each test phone a multi-GB upload and download byte-exact with the screen off, app not killed, each file downloads once in the browser.
