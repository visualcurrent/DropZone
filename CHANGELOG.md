# Changelog

All notable changes to DropZone are recorded here. Format loosely follows
Keep a Changelog; versions follow SemVer with a channel suffix (see
`docs/DEVELOPMENT.md`).

## [Unreleased]
- Field-confirm BACKLOG 10 on Android (v0.2.14): small files download once each
  with the instant native download UI — no `name (1).ext`, no delay, no stacked
  save dialogs.

## [0.2.16] — nightly
- Thumbnails for photos and videos in the file lists (BACKLOG 18). The uploader's browser makes them: after an upload is saved, the page draws each photo, or a frame from just past the start of a video, to a canvas 320 px on its long side and posts the JPEG to the new `POST /api/thumb` (owner only, 256 KB cap, must be a JPEG). `GET /api/thumb` serves it, the file carries `thumb: true` in `/api/state`, and rows show it as a 48 px square in place of the icon, loaded lazily. The server decodes nothing and no dependency is added. A file the browser cannot decode keeps its icon and the browser reports the reason, which is logged. Removing a file removes its thumbnail. The row's first column is now 48 px wide for every row so names line up.
- Logging for field tests: `upload start` and every thumbnail line end with the browser's User-Agent; `thumb saved` lines carry the browser's own time (`ms=`) and the source pixel size (`src=`). New test `tests/test_thumb.py`.

## [0.2.15] — nightly
- Fix single-file downloads of files whose name is not plain latin-1 (an emoji, a curly apostrophe, non-European scripts). `/api/download` put the raw name in the `Content-Disposition` header; `http.server` can only send latin-1 header text, so the request died with `UnicodeEncodeError` and the browser reported a failed download, while the zip of the same files worked. The quoted `filename=""` part now carries a plain-ASCII stand-in (other characters, `"` and `\` become `_`); the real name still travels in the percent-encoded `filename*=UTF-8''` part. New test `tests/test_download_filename.py`.

## [0.2.14] — nightly
- Fix duplicate downloads the right way, and revert v0.2.13's blob approach (it
  had unacceptable UX: it buffered the whole file with no feedback, so downloads
  felt dead and re-taps stacked up multiple save dialogs). Root cause: advertising
  `Accept-Ranges` made Chrome start a download, cancel it, and re-fetch in parallel
  ranges — a small file finished the first attempt before the cancel landed, so it
  saved twice. Fix: `/api/download` no longer advertises `Accept-Ranges`, so the
  browser does one plain download (one file, instant native download UI); an
  explicit `Range` request is still honored with `206` for iOS Safari and resume.
  Downloads are back to native for all sizes. Also removes the SyntaxWarning from
  the blob code's regex.

## [0.2.13] — nightly
- Actually fix the small-file duplicate downloads (BACKLOG 10). v0.2.11's debounce
  did not help: with the fresh v0.2.12 client confirmed running (header showed
  v0.2.12, cache cleared), small files STILL completed 2-3x — proving the repeats
  come from the browser's own download manager (a probe request + the real one,
  plus range segmentation), not from our code or a double tap, so a JS debounce
  cannot stop them. Fix: for files at/below `BLOB_DL_MAX` (64 MB), the page now
  fetches the file itself and saves it once via a blob URL (`blobSave`). A
  `fetch()` is a single request the browser does not probe or split, so exactly
  one request and one saved file. Larger files keep the native download (the
  browser may segment it into parallel `206` ranges, which assemble into one
  file). Small "download all"/zip bulk downloads go through the same path.
  Client-only; server download path unchanged.

## [0.2.12] — nightly
- Serve the app shell with `Cache-Control: no-store` (+ `Pragma`/`Expires`). The
  page embeds all CSS/JS, so with no cache headers a browser kept running an OLD
  client across version bumps — which is why the v0.2.11 download debounce never
  actually ran on the phone (the v0.2.11 field log still showed the zip re-fire
  storm, while the server's new `206` range replies proved the server half WAS
  updated). Client-side changes now take effect on the next load.

## [0.2.11] — nightly
- Fix the Android download re-fire (BACKLOG 10): one click now sends exactly one
  request. The single-file button was a bare navigating `<a download>` whose node
  the 2.5 s `/api/state` poll destroyed mid-download (the list is rebuilt with
  `innerHTML`), so the browser aborted and retried — the log showed one `[id]`
  fired ~3× with two cancels. Now every download (single + bulk) goes through one
  detached, self-removing anchor on `<body>` that a list re-render can't touch,
  guarded by a 1.5 s per-URL debounce that drops duplicate fires. The file lists
  also skip their DOM rebuild when nothing changed, so buttons no longer churn
  under an in-flight click. Client-only; the server download path is unchanged.

## [0.2.10] — nightly
- Single-file downloads now support HTTP Range requests (BACKLOG 10).
  `/api/download` advertises `Accept-Ranges`, `ETag` and `Last-Modified`, answers
  a `Range:` header with `206 Partial Content` + `Content-Range` (gated by
  `If-Range`), and returns `416` for a range past EOF; a malformed or multi-range
  header falls back to a normal `200`. This fixes duplicate downloads from iOS
  Safari, which probes a file with a Range request and then re-fetched — creating
  an OS-suffixed `name (1).ext` — whenever the server only ever replied `200`.
  Ranges also make single-file downloads resumable and seekable. Streamed
  "download everything" zips are unchanged (still `200`). Covered by
  `tests/test_download_range.py`.
- BACKLOG 1 (upload freeze) confirmed CLOSED by the 2026-08-30 phone field run:
  single files of 2.4/2.6/1.8 GB and a 4.4 GB batch, all byte-exact, server RSS
  flat 12-16 MB, no freeze/OOM.

## [0.2.09] — nightly
- ZIP downloads now STREAM as they are built instead of spooling a whole temp
  copy first (BACKLOG 13). Downloads start immediately (time-to-first-byte went
  from tens of seconds to ~1 ms), use no temp disk, and keep a real progress bar
  (the uniformly-zip64 layout makes the exact size computable up front). Peak
  memory stays flat. Removes the spool delay that was causing re-clicks and
  duplicate downloads.
- Fix: non-ASCII upload filenames (accents, CJK) were mangled since v0.2.05
  (headers decoded latin-1); now decoded UTF-8 and round-trip correctly.
- Client connection drops now log one line instead of an unhandled traceback.

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
