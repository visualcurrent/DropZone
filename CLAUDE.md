# Project: DropZone — instant LAN file sharing where only the host installs anything

Doc tier: 3

## Goal
A host runs one pure-stdlib Python file; everyone else on the same WiFi opens a browser (via a QR code) to upload and download files — no app, no account, any OS. A correct result: on the phone host in Termux, multi-GB files upload and download byte-exact without freezing, server memory stays flat, and each file downloads exactly once (no OS-suffixed `name (1).ext` duplicates).

## Environment
- Python 3.6+ standard library only — zero third-party packages. A hard rule; a backlog item must explicitly approve any dependency. [verified: README + docs/DEVELOPMENT.md]
- Runs on Windows/macOS/Linux and on Android via Termux. Host page `http://localhost:7070`, remote page `http://<ip>:7070/remote`. Port and the four transfer limits are constants near the top of `DropZone.py`.
- Tests are dependency-free and start the real server over sockets: `python3 tests/run_all.py`. The memory checks read `/proc/<pid>/status`, so they measure memory only on Linux/Termux, not Windows/macOS. [verified: tests/README.md]
- Deploy to the phone: Syncthing pushes the PC dev folder to the phone's run folder; a Termux:Widget shortcut runs `DropZone.py`. The version constant, not the filename, identifies the running build.

## Settled decisions (dated, by Gabe)
- 2026-08-30 — Versioning is `release.beta.incremental` (e.g. v0.2.14); baseline v0.2.00. Bump in the same change that ships the work; pure-doc changes need not bump. The `VERSION_STAGE` label is judged redundant vs the number; hold at 0.2.xx.
- 2026-08-30 — Cross-session / between-session theme persistence is NOT wanted.
- Git commits are made manually by Gabe. While the project was off git, commit messages were staged as `docs/commits/NNNN-*.md` notes; those are superseded by the real git history carried in this migration (archived for reference).
- Keep the single-file, zero-dependency shape; prefer the smallest change that solves the problem.

## Do-not-re-derive (verified findings)
- Upload-freeze cause: `do_POST` read the whole request body into RAM (`self.rfile.read(length)`) and `parse_multipart` copied it again, so peak RSS was ~2–3× file size and the phone OOM-killed large uploads. Fixed v0.2.05 by streaming the body to disk in `UPLOAD_CHUNK` (4 MB) blocks. [verified: v0.2.04 field-log RSS table; field-confirmed closed v0.2.09 — 2.4/2.6/1.8 GB singles + 4.4 GB batch byte-exact, RSS flat 12–16 MB]
- Small-file duplicate downloads were caused by advertising `Accept-Ranges`, which makes Chrome start/cancel/re-segment a download (a small file finishes the first attempt before the cancel → saved twice; a large file is cancelled → one file). Fixed v0.2.14 by NOT advertising `Accept-Ranges`; an explicit `Range` request is still honored with 206. [verified: docs/commits/0016 + tests/test_download_range.py]
- The app shell must be served `Cache-Control: no-store`; the page inlines all CSS/JS, so without it browsers pin an old client across deploys (why the v0.2.11 client fix appeared not to work until v0.2.12). [verified: v0.2.11/0.2.12 field logs]
- The blob / in-page download (`blobSave`, v0.2.13) deduped but had unacceptable UX (buffered the whole file, no feedback, stacked save dialogs); REVERTED in v0.2.14 — do not resurrect. [verified: v0.2.13 log + revert note in docs/commits/0016]

## Read order
Root CLAUDE.md (auto) -> this file -> SESSION.md -> PLAN.md. Others only when pointed to. Do not read `DropZone.py` whole; use SCRIPT_INDEX.md. Contracts that break silently are in ARCHITECTURE.md.
