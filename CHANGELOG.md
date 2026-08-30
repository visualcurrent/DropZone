# Changelog

All notable changes to DropZone are recorded here. Format loosely follows
Keep a Changelog; versions follow SemVer with a channel suffix (see
`docs/DEVELOPMENT.md`).

## [Unreleased]
- Investigate duplicate/double downloads (now that per-file [id] logging exists).
- Stream the ZIP as it is built to remove the spool delay (BACKLOG 13; findings
  in docs/notes/streaming-zip-findings.md).
- Field-test the v0.2.05 streaming upload on the phone (a ~2 GB single file and a
  multi-user run) to fully close BACKLOG 1's Definition of done.

## [0.2.08] — nightly
- Fix: bulk ZIP downloads no longer navigate the page. Clicking "All N files"
  or "Download everything" used to send the whole page to the download URL —
  which sat blank while the archive spooled, and re-fired (duplicate) on a
  refresh. Downloads now trigger a background `download` anchor and leave the
  page in place.
- Host activity panel now floats at the bottom, out of normal flow: always
  visible without scrolling to the top, and its updates no longer shift the
  page content below it.

## [0.2.07] — nightly
- Live transfer activity feedback (BACKLOG 6, feedback half): every page now
  shows an ambient "Host activity" banner listing in-flight downloads/zips
  with phase (queued / preparing / sending) and, for queued transfers, a
  position ("#N of M"). Fed by the existing /api/state poll, so a waiting
  device sees progress even while its own download request is blocked. No
  change to the download mechanism itself.

## [0.2.06] — nightly
- Upload read-chunk hoisted to a named `UPLOAD_CHUNK` constant (in the
  transfer-tuning block) and set to 4 MB, up from 1 MB. Sits on the socket
  read-efficiency plateau while keeping peak memory small even under the
  4-way transfer concurrency. No behavioural change beyond buffer size.

## [0.2.05] — nightly
- Streaming uploads: the multipart body is now parsed from the socket in 1 MB
  chunks and each file is written straight to disk, so peak memory stays flat no
  matter how large the upload is. Fixes the large-file upload freeze (BACKLOG 1),
  whose cause — the whole body read into RAM by `self.rfile.read(length)` and
  copied again by `parse_multipart` — was confirmed from the v0.2.04 field log.
  In container testing a 1.2 GB upload peaked at ~23 MB server RSS, byte-exact.
  New per-file "upload saved" log line.
- Real upload progress bar (BACKLOG 9): the client uploads via XMLHttpRequest and
  drives the bar from true bytes sent (percent, bytes, ETA); on a stall it stops
  at the real point instead of creeping to ~100%. Replaces the fake timer.

## [0.2.04] — nightly
- Persistent logging: log() now also appends to `DropZone.log` beside the script
  (flushed per line), so records survive a Termux crash. Unhandled per-request
  errors and a fatal in serve_forever are logged too. Startup writes a
  version/pid line; the log rolls to `DropZone.log.1` past 5 MB; the banner
  prints the log path.

## [0.2.03] — nightly
- ZIP downloads now STORE files (no compression). Faster on a phone and the
  archive size is predictable; media is already compressed anyway.
- Terminal now logs the full download lifecycle: single-file downloads (with
  file id) and zip requested/building/sending/done/cancelled. Answers "nothing
  is happening" and reveals if the same file id is requested twice.
## [0.2.02] — nightly
- Startup banner now prints the build version and stage.
- Diagnostics for the upload-freeze investigation: DEBUG log() and rss_mb();
  the upload path now logs Content-Length, bytes read, part count, and resident
  memory at each stage.
- Downloads no longer print a traceback when a client cancels mid-transfer;
  BrokenPipeError / ConnectionResetError are caught and logged as a cancel.

## [0.2.01] — beta
- Added `__version__` and `VERSION_STAGE`; the header now shows the running
  build and release stage (e.g. "v0.2.01 · beta").

## [Workflow setup]
- Development workflow established (docs-driven, one-task-at-a-time).
- Added BACKLOG.md, SESSION.md, CHANGELOG.md, and docs/ (DEVELOPMENT.md,
  commit notes, investigation notes). No application behavior changed.

## [0.2.00] — baseline
Baseline snapshot of the existing app at the time the workflow was set up.
- LAN file sharing: host installs nothing but Python; guests use a browser.
- Host and remote pages, QR-code join, editable display names.
- Per-file download plus bulk ZIP: per-user "All files" and a
  "Download everything" archive foldered by user.
- Memory-safe transfers: small transfers buffered, large ones streamed from
  disk; concurrency capped by a semaphore.
- Files stored in a temp folder, cleared on Ctrl+C; state is in-memory.

Version format is `release.beta.incremental` (see docs/DEVELOPMENT.md).
The version constant gets wired into the app in BACKLOG item 3.
