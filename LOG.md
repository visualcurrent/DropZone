# LOG — DropZone

Append-only. Newest on top. One dated entry per working session: built / decided / rejected / retracted, with evidence. Every claim tagged. Never edit an old entry.

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
