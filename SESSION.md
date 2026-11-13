# SESSION — DropZone

> Read first, update last. Current-state block under 15 lines. It is a prompt, not a history.

## Current state
- Source is **core v0.2.18 (nightly), wrapper 0.1.05**; the APK on disk is one step behind: `android\DropZone-debug.apk`, built 2026-11-12 14:39, is `0.1.05-dz0.2.17`. v0.2.18 is in NO build yet. Nothing from 2026-11-12 is pushed. [verified: build output, `git log`]
- v0.2.16 thumbnails (BACKLOG 18): the uploader's browser posts a 320 px JPEG to `/api/thumb`; rows show a 48 px square. [verified: `tests/test_thumb.py` 14/14; headless Edge check] Field (Gabe, v0.2.16): portrait upright, look right, delay acceptable, some videos black. [verified: Gabe's report; phones unrecorded] iPhone, undecodable file, removal and memory lines of the DoD not yet reported. [assumed: pending]
- v0.2.17 field test page for several downloads from one tap (U4): tap the header's version number, then the TEST button. [verified: headless Edge check] On the PC only the first of 3 downloads reached the server while the page said 3 started, so only the files on the phone and the `multi-test` log lines count. [verified: scratch check, twice] Field, partial (Gabe, 2026-11-13, 5 files): Android Chrome 5/5 after one permission prompt; Android Via 5/5 with a dialog per file; Android Firefox 2/5 FAIL; PC Chrome and PC Firefox 5/5 with a save dialog per file, PC Chrome 0 after the first when the permission is blocked. [verified: Gabe's report; host log not read] iPhone Safari untested. [assumed: pending]
- v0.2.18 video thumbnails take the frame 10% into the clip instead of 0.1 s in, to get past fade-ins. [est_: script passes `node --check`; never run on a video in any browser]
- Wrapper 0.1.05: Copy button reads "Copied" for 1.5 s. [verified: builds; not yet seen on a phone]
- Field logging: `upload start`, thumbnail and `multi-test` lines carry the User-Agent; a thumbnail that fails in a guest's browser is logged with its reason. Android Chrome hides the phone model, so Gabe notes model against the page's user name. [verified: test + Edge checks]
- Tests on v0.2.18: 5 of 6 pass on Windows through a scratch shim; `test_zip_streaming.py` not run (cannot run on Windows); memory not measured. [verified: shim run 2026-11-12] No Linux run yet; Termux is a test bench only. [assumed: would pass]
- Designed, not built (`UNEXPLORED_IDEAS.md` U1): tap thumbnail = peek, tap row = select, one list-wide download button, header select circles. Open point: whether the per-row download arrow stays, decided by the U4 field test.
- M1 field so far: one phone, by script — 2.6 GB up and down byte-exact, screen off, memory flat. [verified: sha256, 2026-11-11] Second phone, browser-driven checks, and BACKLOG 10's Downloads-folder and iPhone checks still owed. [assumed: pending]

## Open user questions
- Reword `README.md`? It still presents Termux as a way to host (6 mentions); `CLAUDE.md` now says test bench only. [assumed: yes, awaiting Gabe's word]
- Which phones and browsers gave the v0.2.16 thumbnail result? [assumed: unknown]
- Keep or remove the wake lock + WiFi lock the app holds while the server runs (added without a request)? [assumed: keep]
- Gabe deletes `PROJECTS\DropZone-Android` and the GitHub repo `visualcurrent/DropZone-Android` (retired; see LOG 2026-11-11 Retire). [verified: LOG entry]
- Audit decision (BACKLOG 8): keep or remove Range support wholesale. [assumed: pending]

## Resume
- Next action: take Gabe's field results from the `0.1.05-dz0.2.17` APK — per phone, files arrived out of files started on the TEST page, and whether a permission prompt appeared — and read `files/DropZone.log` (`adb shell run-as com.visualcurrent.dropzone cat files/DropZone.log`) for `multi-test`, `thumb saved` and `thumb FAILED` lines. The counts settle U1's open point. Then rebuild the APK so v0.2.18 reaches a phone, and check a video thumbnail.
- Read: UNEXPLORED_IDEAS.md > U1 (agreed design) and U4 (the test and its hurdles).
- Read: PLAN.md > Backlog — active, item 18 (its DoD is the thumbnail field gate).
- Read: SCRIPT_INDEX.md > DropZone.py map > Thumbnails in the page script, and Field test page in the page script.
- Read: ARCHITECTURE.md > Contracts to preserve (7-9 Android, 10 thumbnails) before changing module-level names or the thumbnail routes.
- Pending gate: multi-download, user-run — Android Chrome half PASSED 2026-11-13 (5/5). Still owed: iPhone Safari, with 5 files shared by someone else, tap the version number then the TEST button; pass is all 5 files arriving. Also owed: on Android Firefox (2/5) note which 2 arrived, then read the host's `multi-test` log lines over adb.
- Pending gate: thumbnails, user-run (partly reported) — iPhone Safari upload of a JPEG, PNG, portrait photo and MP4 shows thumbnails on a second device; an undecodable file keeps its icon; removing a file removes its row; log memory at "upload done" stays 12–16 MB.
- Pending gate: v0.2.18 video frame, user-run after the next build — a clip that showed black on v0.2.16 shows a picture.
- Pending gate: M1 field gate, user-run — on each test phone a multi-GB upload and download byte-exact with the screen off, app not killed, each file downloads once in the browser.
