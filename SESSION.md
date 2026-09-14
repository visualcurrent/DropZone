# SESSION — DropZone

> Read first, update last. Current-state block under 15 lines. It is a prompt, not a history.

## Current state
- Running build **v0.2.14 (nightly)**; the whole test suite is green and the served page carries the new client. [verified: node --check + boot smoke, last work session 2026-08-30]
- BACKLOG 1 (upload freeze) CLOSED — field-confirmed on the phone. [verified: 2026-08-30 field run — 2.4/2.6/1.8 GB singles + 4.4 GB batch byte-exact, RSS flat 12–16 MB]
- BACKLOG 10 (duplicate downloads) fix shipped v0.2.14 (stop advertising `Accept-Ranges`); the v0.2.14 Android field log shows one completed download per file and no range segmentation. [est_ from field log 2026-08-30] An Android eyeball of the Downloads folder and an iPhone check are still owed.
- Migrated into AI-dev on 2026-09-11; full git history (17 commits) and `origin` carried by copy. [verified: git log/fsck in the copy]

## Open user questions
- Confirm on Android that a small file lands once (no `name (1).ext`), and likewise on an iPhone. [assumed: pending]
- Audit decision (BACKLOG 8): keep or remove Range support wholesale — depends on whether Safari/resume matters. [assumed: pending]

## Resume
- Next action: field-confirm v0.2.14 BACKLOG 10 on Android; then the next code target is the host connected-users panel (BACKLOG 4).
- Read: PLAN.md > M0 core app, and the Backlog section.
- Read: SCRIPT_INDEX.md > DropZone.py map for the download/upload/zip entry points before touching them.
- Read: ARCHITECTURE.md > Contracts to preserve before any change to `/api/download` or `send_html`.
- Pending gate: v0.2.14 Android field-confirm of BACKLOG 10 — [assumed: pending] a small file downloads once, no `name (1).ext`.
