# SESSION — DropZone

> Read first, update last. Current-state block under 15 lines. It is a prompt, not a history.

## Current state
- Build **v0.2.15 (nightly)**: fixes single-file download of names outside latin-1 (BACKLOG 16). [verified: `tests/test_download_filename.py` 17/17 + `test_download_range.py` PASS on Windows via a scratch shim, 2026-11-11] The full `tests/run_all.py` has NOT been run on v0.2.15 (needs Linux/Termux). [assumed: other three tests unaffected]
- Merging the Android app in (decided 2026-11-11): step 1 of 4 done (this fix); steps 2-4 pending — move `PROJECTS\DropZone-Android` into `android\`, fold docs as milestone M1, rebuild and re-verify. Plan and decisions: LOG.md top entry.
- v0.2.14 state before this session: the whole test suite was green and the served page carried the new client. [verified: node --check + boot smoke, last work session 2026-08-30]
- BACKLOG 1 (upload freeze) CLOSED — field-confirmed on the phone. [verified: 2026-08-30 field run — 2.4/2.6/1.8 GB singles + 4.4 GB batch byte-exact, RSS flat 12–16 MB]
- BACKLOG 10 (duplicate downloads) fix shipped v0.2.14 (stop advertising `Accept-Ranges`); the v0.2.14 Android field log shows one completed download per file and no range segmentation. [est_ from field log 2026-08-30] An Android eyeball of the Downloads folder and an iPhone check are still owed.
- Migrated into AI-dev on 2026-09-11; full git history (17 commits) and `origin` carried by copy. [verified: git log/fsck in the copy]

## Open user questions
- Confirm on Android that a small file lands once (no `name (1).ext`), and likewise on an iPhone. [assumed: pending]
- Audit decision (BACKLOG 8): keep or remove Range support wholesale — depends on whether Safari/resume matters. [assumed: pending]

## Resume
- Next action: after Gabe commits v0.2.15, do merge step 2 (move the Android project into `android\`, build from `..\DropZone.py`, delete the wrapper's header patch). Parked behind the merge: field-confirm BACKLOG 10 on Android; host connected-users panel (BACKLOG 4).
- Pending gate: `python3 tests/run_all.py` on the Termux phone at v0.2.15 — all five tests PASS. [assumed: pending]
- Read: PLAN.md > M0 core app, and the Backlog section.
- Read: SCRIPT_INDEX.md > DropZone.py map for the download/upload/zip entry points before touching them.
- Read: ARCHITECTURE.md > Contracts to preserve before any change to `/api/download` or `send_html`.
- Pending gate: v0.2.14 Android field-confirm of BACKLOG 10 — [assumed: pending] a small file downloads once, no `name (1).ext`.
