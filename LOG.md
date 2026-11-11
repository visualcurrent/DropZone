# LOG — DropZone

Append-only. Newest on top. One dated entry per working session: built / decided / rejected / retracted, with evidence. Every claim tagged. Never edit an old entry.

## 2026-11-11 — Session 3: host uploads hang on the Xiaomi — the phone froze the app
- Reported (Gabe): on the host phone, uploads from the host page fail, and a remote phone connecting times out. App `0.1.03-dz0.2.15`, phone `fc0f334f` (Xiaomi 23116PN5BC, Android 16), browser Via.
- Observed: the server log has nothing between the start line (12:21:43) and 12:25:32, when two uploads arrive in the same second and finish normally (8.4 MB; 508.6 MB in 8 s). A state request from the PC at about 12:25 got no answer in 5 s; seconds later the same request answered in 12 ms. [verified: `files/DropZone.log`, curl timings]
- Cause: Xiaomi's app freezer froze the whole app process while its foreground service was running and the screen was on. System log: `12:22:01.981 PowerManagerServiceImpl: Partial wakeLock 'DropZone:server' … disabled: true, procState: 4, reason: greeze` and `setUidState, uid = 10305 allow = false`; then `12:25:32.713 GreezeManager: THAW uid = 10305 pid = [8077] reason : screen on`. While frozen the kernel still accepts connections, so requests wait instead of failing; at the thaw they all run. [verified: logcat lines; `dumpsys greezer` history]
- Trigger, both times it happened: the system file picker (`com.google.android.documentsui … PickActivity`) handing back to the browser — i.e. the moment a host upload begins. 09:46:33 it thawed after 3 s; 12:22:01 it stayed frozen 3 min 31 s until the screen cycled. [verified: logcat context at both timestamps; est_: that the picker hand-off is the trigger, from two events]
- Not reproduced on demand: with the app sent to the background by the Home key, six probes over 60 s all answered in about 20 ms and no freeze was logged. [verified]
- The app is not on the battery-optimisation exemption list (`dumpsys deviceidle whitelist` has no entry). Whether an exemption, or Xiaomi's per-app "Battery saver: No restrictions", stops this freezer is not known. [assumed: it does — to be tested]
- The morning's 2.6 GB screen-off run did not hit it: no freeze entries for the app in that window. [verified: greezer history]
- No code changed. Next (user): set DropZone's battery setting to "No restrictions" on the phone and repeat host uploads through the file picker; then the agent reads the freezer history for any new `FZ uid = 10305`.

## 2026-11-11 — Session 2: app screen restyled after the web page (wrapper 0.1.03)
- Requested (Gabe): make the app screen friendlier, like the DropZone web page — tagline, clarity of purpose, version info, buttons aligned with their information. Mockup reviewed first (two artboards, Stopped and Running); Gabe approved all of it, including the new Copy button, with no QR code in the app. [verified: user approval in session]
- Built: `MainActivity.java` rewritten (header with logo, name, "Host" badge, tagline; one card of three rows — Server -> Start/Stop, Your host page -> Open, Others join at -> Copy — with the buttons in one column; "How it works" in three steps; footer with core and app versions). Colours are the web page's CSS variables, light and dark, following the phone's dark mode. New `res/drawable/ic_logo.xml` (the page's logo strokes). `app/build.gradle` now writes `CORE_VERSION`, `CORE_STAGE`, `WRAPPER_VERSION` into `BuildConfig`. Wrapper 0.1.03, versionCode 4. No change to `DropZone.py`, `dz_host.py` or `ServerService.java`.
- Fixed in passing: the manifest theme was `Theme.DeviceDefault.DayNight`, which exists only from Android 10, while the app allows Android 8 and 9. Now `Theme.DeviceDefault.Light.NoActionBar`; the screen paints its own colours. [est_: the old theme would have failed on Android 8/9; never run there]
- Checked: build SUCCESSFUL; on the Android 15 emulator the Stopped, Running and Running-dark screens match the mockup with nothing clipped; Start works; Copy puts the full `http://…/remote` address on the clipboard; the Running state survives the light/dark switch. [verified: three screenshots + system clipboard bubble, 2026-11-11]
- Checked on the phone `fc0f334f` (Android 16, dark mode, Xiaomi system font): Stopped and Running screens lay out as in the mockup, nothing clipped, real address shown, Start works. [verified: two screenshots, 2026-11-11]
- Difference on that phone: bold text (app name, state, captions, button labels) draws at nearly regular weight; the emulator draws it bold. Cause: the Xiaomi system font does not honour the stock bold typeface. [est_: from the two renderings side by side] Changed `text()`/`button()` to derive bold from the view's own font (`makeBold`); buttons got slightly heavier, the app name did not. Left there; forcing synthetic bold is possible but would over-thicken phones that do have a real bold. [verified: third screenshot]
- NOT checked: Android 8-14 layouts, light mode on a real phone, large system font sizes, and the "Could not start" error text. [assumed: fine — the body scrolls]
- Next (user): look at it on the phones; say whether the lighter headings on the Xiaomi are acceptable.
- Accepted (Gabe): "Everything is good. Text is fine." The lighter headings stay as they are. Stated preferences recorded in `CLAUDE.md` > Settled decisions: balance of functional / good-looking / reasonably simple, and wider Android-version compatibility when a choice affects it. [verified: user statement 2026-11-11]

## 2026-11-11 — Retire DropZone-Android
- Checked before retiring: the `PROJECTS\DropZone-Android` repo is clean with nothing unpushed (`master` 60014fa, also on GitHub). Every file is in `android\` or was changed on purpose in the merge (DropZone.py 0.2.14→0.2.15, `_patch_header_encoding` removed, Gradle `rootProject.name`). [verified: `git status`, `git ls-remote`, `diff -rq` against `android\`]
- Removed from GitHub Desktop by Gabe. Moving the folder to `_to_delete\` failed: Windows reports it in use and does not name the process. Gabe deletes the folder later. [verified: `mv` and `Move-Item` both refused, 2026-11-11]
- GitHub repo `visualcurrent/DropZone-Android`: `git ls-remote` reaches it, but the browser returns 404 while logged in. Cause not found. [verified: ls-remote output; Gabe's report]
- Next (user): delete the local folder; delete or archive the GitHub repo.

## 2026-11-11 — Session 1: v0.2.15 filename fix (step 1 of merging in the Android app)
- Decided (Gabe, 2026-11-11): merge the separate DropZone-Android project into this one as a new milestone; the "do not touch the DropZone directory" rule set that morning ends; "single-file, zero-dependency" is scoped to `DropZone.py` and how it runs; the DropZone-Android repo is retired. Plan in four steps; this entry is step 1 only. [verified: user approval in session]
- Diagnosed: single-file download of a name outside latin-1 dies in `send_header("Content-Disposition", ...)` with `UnicodeEncodeError`; zip unaffected. [verified: 9 tracebacks in the Android app's `DropZone.log`, 2026-11-11 09:28-09:29, for a name with an emoji and one with a curly apostrophe]
- Fixed (v0.2.15, `/api/download`): the quoted `filename=""` carries an ASCII stand-in (`re.sub(r'[^\x20-\x7e]|["\\]', "_", name)`); `filename*=UTF-8''` unchanged. +7 lines. [verified: new `tests/test_download_filename.py` 17/17 PASS on v0.2.15 and fails on the committed v0.2.14 (server closes with no response); `test_download_range.py` PASS — both run on Windows through a scratch shim that replaces only the harness's Linux-only launch/stop]
- NOT run: `python3 tests/run_all.py` as written. The harness needs Linux (`os.setsid`), and this PC has no WSL. The three other tests were not run this session. [assumed: unaffected — the change is confined to one header in `/api/download`]
- Added: backlog 17 (Windows host, emoji filename fails the upload via `log()`'s `print`). Not fixed. [verified: reproduced on the PC]
- Updated: `SCRIPT_INDEX.md` line numbers (+7 below L494), `CHANGELOG.md`, `tests/README.md`, `run_all.py`.
- Next (user): commit; run `python3 tests/run_all.py` on the Termux phone. Next (agent): step 2, move the Android project into `android\`.
- Step 1 committed by Gabe as `b8a96b5 0.2.15`. [verified: git log]
- Step 2 done: Android project copied from `PROJECTS\DropZone-Android` into `android\` (Gradle files, `build.bat`, `app\src`); the old folder is untouched. `android\app\build.gradle` now copies `..\..\DropZone.py` into `app\src\main\python\` per build; that copy, build output and the APK are git-ignored. The wrapper's `_patch_header_encoding` is deleted (v0.2.15 replaces it). Wrapper 0.1.02, versionCode 3. [verified: `android\build.bat` BUILD SUCCESSFUL; `aapt2 dump badging` versionName `0.1.02-dz0.2.15`]
- Verified after the move: a file named 'Pickled Daikon Crunch (40’s) ☀️.txt' uploads and downloads byte-identical with header `filename="Pickled Daikon Crunch (40_s) __.txt"; filename*=UTF-8''...` — on the PC through `android\...\dz_host.py` (core 0.2.15, no header patch present), and on the phone `fc0f334f` running the installed 0.1.02 build. [verified: scratch `check_http.py`, both runs; phone log shows start v0.2.15 and the download done]
- Retracted within this step: a first PC re-check reported "started 0.2.14"; it had run the old project's files because a path substitution did not apply. Discarded and re-run against the right folder (result above).
- Rule conflict named: `docs-protocol.md` > Committing says the agent never commits; Gabe states (2026-11-11) the rule is now "agent commits, never pushes". Followed Gabe's statement for the step 2 commit; the rule-file edit is proposed, not yet made.
- Next (agent): step 3, fold the docs (M1 in PLAN.md, CLAUDE.md, ARCHITECTURE.md, `UNINSTALL.md`, archive the DropZone-Android docs, `~Projects.md`).
- Retracted: the "rule conflict" line above. The root rule was changed the same day (root commits `330d0f8`, `248f157`): the agent stages and commits, the user pushes. No rule edit is pending. [verified: `docs-protocol.md` > Committing as now on disk]
- Tests on v0.2.15, Windows via the scratch shim: `test_queue_feedback.py` PASS; `test_upload_memory.py` PASS (byte-exact part only; Windows cannot read RSS); `test_zip_streaming.py` could not run (its own cleanup deletes an open file, refused by Windows). With the two earlier results: 4 of 5 pass, 1 not run. [verified: shim runs 2026-11-11] The zip and upload code are untouched by v0.2.15. [verified: diff of `b8a96b5` touches only `/api/download`'s header]
- Corrected (Gabe): there is no Syncthing or Termux:Widget deploy; the Termux phone gets a new `DropZone.py` by manual download from GitHub, no rename. `CLAUDE.md` > Environment fixed. Gabe reports v0.2.15 pushed, on the Termux phone, and the new APK installed. [verified: user report]
- Step 3 done: `PLAN.md` > M1 — Android app (status + open items carried from the DropZone-Android plan and field notes); `CLAUDE.md` environment, three dated decisions, four findings; `ARCHITECTURE.md` Android layer + contracts 7-9; `UNINSTALL.md` at the project root with paths updated; DropZone-Android's `CLAUDE`/`SESSION`/`LOG`/`PLAN` copied to `_archive\DropZone-Android-*.md`; `~Projects.md` lines merged. The `PROJECTS\DropZone-Android` folder is untouched; retiring it and its GitHub repo is Gabe's. [verified: files present]
- Merge complete (steps 1-4). Next (user): field run on the second phone + browser-driven checks (PLAN.md > M1 field gate); push.

## 2026-09-11 — Session 0: migrated into AI-dev
- Migrated `D:\ClauDev\DropZone` into `projects\DropZone` by copying the whole folder including `.git`; full history and the `origin` link were preserved with no git write. [verified: git log --oneline = 17 commits, `remote -v` origin unchanged, git fsck clean in the copy]
- Set Doc tier 3 and built the nine standard docs. Folded BACKLOG.md -> PLAN.md + UNEXPLORED_IDEAS.md; docs/DEVELOPMENT.md -> CLAUDE.md (the generic session loop left to the root method + session skills); audit-guide-downloads.md + streaming-zip-findings.md -> ARCHITECTURE.md; the upload-freeze finding -> CLAUDE.md do-not-re-derive + LESSONS_LEARNED.md. Every version number, RSS figure, and root-cause finding was kept, not summarized. [verified: fold sources archived untouched in _archive/]
- Archived untouched to `_archive/`: DropZone.log, 8 `DropZone.py.bak*` backups, 16 `docs/commits` notes, and the full pre-migration SESSION narrative as `SESSION-pre-migration.md`. The user-flagged `docs/commits/_to_delete/0012` note was routed to `_to_delete/`. [verified: file moves only, no deletes]
- Carried-in working-tree change: `LICENSE` has an uncommitted line-ending-only edit from the source. Left for the user to keep or discard at commit. [verified: git status --porcelain = " M LICENSE"]
- Pre-migration session history and version history live in `_archive/SESSION-pre-migration.md` and `CHANGELOG.md`; this LOG starts fresh here. Next: run the safe-to-delete gate, then hand the user the commit. [assumed: gate pending at time of writing]

### Commit-note -> git version map (pre-migration history)
The old `docs/commits/00NN-*.md` notes (now in `_archive/`) were committed as files inside these versions. View a note at its commit with `git show <hash>:docs/commits/<note>`. Commit subjects are terse; the full CHANGELOG entry is the commit body (`git log` without `--oneline`).

| Notes | Committed in |
|---|---|
| 0001–0007 | `7971c5b` 0.2.06 |
| 0008 | `3e522af` 0.2.07 |
| 0009 | `dbca092` 0.2.08 |
| 0010 | `b1775fc` 0.2.09 |
| 0011 | `39ecf78` add safety net |
| 0012 | `f279bb1` 0.2.10 |
| 0013, 0014 | `06cc67e` 0.2.12 |
| 0015, 0016 | `566c327` 0.2.14 |
