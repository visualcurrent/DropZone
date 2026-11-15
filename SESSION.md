# SESSION — DropZone

> Read first, update last. Current-state block under 15 lines. It is a prompt, not a history.

## Current state
- Source is **core v0.2.23, wrapper 0.1.06**; `android\DropZone-debug.apk` is `0.1.06-dz0.2.23`, installed as an update on the Samsung `RFCXA10KBPZ` and the Xiaomi `fc0f334f` (main profile only, battery setting kept). Nothing pushed since 2026-11-12. [verified: `dumpsys package`, `deviceidle whitelist`, `git log`]
- Page and app show the version without a stage label. [verified: page text by script; app footer seen by Gabe 2026-11-16]
- Stopped-host notice (Backlog 19, v0.2.20): PASSED on phones. [verified: Gabe 2026-11-16]
- Several separate downloads from one tap (U4) is DROPPED; every file keeps its download button; the test page is removed. [verified: Gabe's decision 2026-11-16; `LESSONS_LEARNED.md` L8]
- Thumbnails (Backlog 18): photos good; video thumbnails fixed in v0.2.23 (jump waits for the first frame) and PASSED on PC Chrome, one film. Android Firefox cannot make video thumbnails by any page method; its uploads stay black, accepted. [verified: LOG 2026-11-16; `CLAUDE.md` > Do-not-re-derive] Android Chrome and Via video uploads, iPhone, undecodable-file, removal and memory lines not yet reported. [assumed: pending]
- Tests not run since v0.2.18 (5 of 6 passed on Windows through a scratch shim; `test_zip_streaming.py` cannot run on Windows). [assumed: v0.2.19-0.2.23 page-script changes do not affect them]
- Designed, not built (`UNEXPLORED_IDEAS.md` U1): tap thumbnail = peek, tap row = select, one list-wide download button, header select circles; the per-row download arrow stays.
- M1 field: one phone by script, 2.6 GB up and down byte-exact. [verified: sha256, 2026-11-11] Second phone and browser-driven checks still owed. [assumed: pending]
- **DropCast (PLAN M2):** `0.1.11-dz0.2.18` on the Xiaomi; every built step passed except the receive-without-sharing QR, not yet reported; field gate not run; icon on hold. [verified: LOG 2026-11-13] DropCast was not rebuilt this session; `build.bat` still never run in its two-app form.
- Installs: update in place with `adb install --user 0 -r`; the Samsung's dual-app profile stays empty. [verified: `CLAUDE.md` settled decision 2026-11-16]

## Open user questions
- Reword `README.md`? It still presents Termux as a way to host (6 mentions). [assumed: yes, awaiting Gabe's word]
- Keep or remove the wake lock + WiFi lock the app holds while the server runs (added without a request)? [assumed: keep]
- Gabe deletes `PROJECTS\DropZone-Android` and the GitHub repo `visualcurrent/DropZone-Android` (retired; LOG 2026-11-11). [verified: LOG entry]
- Audit decision (Backlog 8): keep or remove Range support wholesale. [assumed: pending]
- Close M1's slow-download item now that the cause is outside the app (`LESSONS_LEARNED.md` L10)? [assumed: yes]
- Delete the test copies of films left on the phones and the PC by the transfer tests (LOG 2026-11-13, 2026-11-14 lines), and the four films now stored in the Samsung's DropZone (removed when the host stops or a file is removed)? [verified: listings 2026-11-14, `ls files/uploads` 2026-11-16]
- New names for the DropZone / DropCast pair before the icon work resumes. [verified: Gabe 2026-11-14]

## Resume
- Next action: Gabe picks the next item from PLAN Backlog — active (open: 2, 4, 6, 8, 15, 17, 18's remaining DoD lines); or DropCast, below. Start with a planning round.
- For DropCast instead: read PLAN.md > M2 (status, open items, gate), SCRIPT_INDEX.md rows under `android/dropcast/`, and ARCHITECTURE.md > Contracts to preserve, 7. Next DropCast action (Gabe): open DropCast with nothing shared and have a guest send a file through its QR; then the M2 field gate.
- Read: PLAN.md > Backlog — active, item 18 (remaining DoD lines).
- Read: SCRIPT_INDEX.md > DropZone.py map > Thumbnails in the page script, and Host-unreachable notice in the page script.
- Read: ARCHITECTURE.md > Contracts to preserve (7-9 Android, 10 thumbnails) before changing module-level names or the thumbnail routes.
- Pending gate: thumbnails, user-run (partly reported) — an MP4 from Android Chrome and from iPhone Safari shows a thumbnail on a second device; an undecodable file keeps its icon; removing a file removes its row; log memory at "upload done" stays flat.
- Pending gate: M2 field gate, user-run — DropCast on one phone, two other devices (one iPhone): a 2 GB+ video down byte-exact with the host's screen off, a guest's file back and saved byte-exact, no internet on the WiFi, Stop leaves the app's storage empty.
- Pending gate: M1 field gate, user-run — on each test phone a multi-GB upload and download byte-exact with the screen off, app not killed, each file downloads once in the browser.
