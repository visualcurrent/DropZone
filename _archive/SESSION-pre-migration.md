# DropZone — Session Handoff

Read this first at the start of every session. Update it last.
See `docs/DEVELOPMENT.md` for how the workflow runs, `BACKLOG.md` for what's next.

## Current focus
Running build is **v0.2.09 (nightly)** (deploy to the phone via Syncthing
-> Downloads -> /storage/emulated/0/Backups/DropZone). DEBUG=True is on.

Logs persist to `DropZone.log` beside the script (survives a Termux crash), so
instead of copying terminal scrollback, just send that file's contents back.

BACKLOG 1 (upload freeze) is CLOSED — confirmed on the phone in the 2026-08-30
field run: single files of 2.4 GB, 2.6 GB and 1.8 GB, plus a 4.4 GB two-file
batch, all uploaded byte-exact with server RSS flat at 12-16 MB. No freeze, no
OOM, no traceback. The streaming fix (v0.2.05) holds at real >2 GB single-file
sizes.

**Running build now v0.2.14 (nightly).** BACKLOG 10 fixes in:
- v0.2.10 — HTTP Range support on `/api/download` (206 + `Content-Range`,
  `Accept-Ranges`/`ETag`/`Last-Modified`/`If-Range`, `416` past EOF). Fixes the iOS
  Safari duplicate (Safari probes with a Range request and re-fetched against a
  200-only server). Zips unchanged.
- v0.2.11 — Android re-fire fix (client only): the single-file button routed
  through one detached, debounced (1.5 s/URL) trigger on `<body>`, plus the file
  lists skip no-op re-renders. The bare button node used to be destroyed by the
  2.5 s poll mid-download, so the browser aborted+retried (same `[id]` ~3x). Now
  one click = one request.
Whole test suite green; embedded JS `node --check`s clean; boot smoke confirms the
served page carries the new code.

**v0.2.12** no-stored the app shell so client changes actually deploy. With that
confirmed on the phone (header showed v0.2.12, cache cleared) the small-file
duplicates PERSISTED — proving the root cause: the **browser's** download manager
issues a probe request + the real one, so a small file completes 2-3x and the OS
saves duplicates. A JS debounce (v0.2.11) can't stop browser-issued requests.

**v0.2.13 blob was REVERTED** — it fixed the dupe (one fetch = one file, proven in
the log) but the UX was unacceptable: it buffered the whole file with no feedback,
so downloads felt dead and re-taps stacked multiple save dialogs.

**v0.2.14 — the keeper:** root cause is advertising `Accept-Ranges` (v0.2.10, for
Safari) — it makes Chrome start/cancel/re-segment, so a small file completes twice
(saved twice) while a large file gets cancelled (one file). Fix: `/api/download`
no longer advertises `Accept-Ranges`, so the browser does ONE plain download (one
file) with the instant native UI Gabe wants; an explicit `Range` request is still
honored with `206` (Safari/resume). Downloads are native for all sizes again. Also
clears the `\*`-regex SyntaxWarning from the reverted blob code.

**v0.2.14 field log (2026-08-30) looks fixed:** downloads show NO range
segmentation (no `(partial)` lines) and exactly ONE completed download per file
(extra attempts are cancelled) — i.e. one saved file, no dupes. Strong indication
BACKLOG 10 is resolved on Android; the only confirmation left is an eyeball of the
Downloads folder (no `name (1).ext`). iPhone check still waits for an iPhone.

Then next code target: the host connected-users panel (BACKLOG 4).

## Last session — 2026-08-30 (later 12)
- Checked v0.2.14 field log for the upload "hang": NOT a regression — the upload
  path is untouched since BACKLOG 1. A 61 MB upload on public wifi showed no moving
  bar for several seconds (slow first byte before `upload.onprogress` fires), so it
  was re-selected -> the SAME file uploaded twice (two `upload start`, two saves,
  same name / different id) and the single shared progress bar bounced between the
  two. Logged as BACKLOG 15 (upload dedup + earlier feedback + per-upload progress).
- Wrote `docs/notes/audit-guide-downloads.md` for the eventual audit (BACKLOG 8):
  the download saga (v0.2.10-0.2.14) invariants NOT to break (no Accept-Ranges
  advertisement; no-store shell; keep-or-remove Range wholesale), what to keep,
  what to scrutinize, and what NOT to resurrect (blob). BACKLOG 8 now points to it.
- No code changed this session — analysis + notes only. Running build stays v0.2.14.

## Last session — 2026-08-30 (later 11)
- v0.2.13's in-page blob download fixed the dupe (log: one fetch per small file)
  but had unacceptable UX (no feedback while buffering; re-taps stacked save
  dialogs). REVERTED.
- Final root cause: advertising `Accept-Ranges` (added v0.2.10 for Safari) makes
  Chrome start/cancel/re-segment a download; small files complete the first plain
  attempt before the cancel => saved twice; large files get cancelled => one file.
- Shipped **v0.2.14**: `/api/download` no longer advertises `Accept-Ranges` (416
  keeps its own), so the browser does ONE plain native download (instant UI, one
  file). Still honors an explicit `Range` with `206` (Safari/resume) — parse_range
  etc. unchanged. Client reverted to native (`downloadOne`->`triggerDownload`);
  debounce kept for double-tap. Removing the blob regex also cleared the startup
  `SyntaxWarning: invalid escape sequence '\*'`.
- Verified: no SyntaxWarning (warnings-as-errors compile), node --check, full suite
  green (test_download_range now asserts the 200 omits Accept-Ranges while a Range
  request still returns 206), boot smoke. Commit note docs/commits/0016. Backup
  docs/notes/DropZone.py.bak8-*.
- Trade-off accepted: single-file downloads are single-connection + non-resumable
  on the plain 200 (fine for LAN one-shots; explicit-Range clients still get 206).
- Item 10 `[~]`: v0.2.14 should be the keeper; needs the Android field check.

## Last session — 2026-08-30 (later 10)
- Confirmed the download re-fire is the BROWSER's download manager, not our code:
  with v0.2.12 verified running on the phone (header + cleared cache), small files
  still completed 2-3x. A tap => browser probe request + real request; small files
  complete both => duplicate saves (matches the original "small files only"
  report). JS debounce can't stop browser-issued requests — v0.2.11 was the wrong
  tool.
- Shipped **v0.2.13** (client only): `startDownload(url,size)` routes small
  downloads (<=64 MB) through `blobSave` — `fetch()` the file and save once via a
  blob URL (one request, one file, no browser probe/segmentation). Large files
  keep the native path. Single files pass `f.size`; small zips use it via
  `confirmBulk`. Server download path unchanged.
- Verified: `node --check` on JS/HOST_INIT/REMOTE_INIT, full suite green, boot
  smoke shows the page carries `blobSave`/`startDownload`/`BLOB_DL_MAX` + no-store.
  Commit note docs/commits/0015. Backup docs/notes/DropZone.py.bak7-*.
- Item 10 `[~]`: v0.2.13 is the expected fix; needs the Android field check (small
  file saves once, single full `200` in the log). iPhone dupe check still pending.

## Last session — 2026-08-30 (later 9)
- Read the v0.2.11 field log: the Android re-fire was NOT fixed in the field — but
  the debounce was correct; the phone was running a CACHED old page. Tell: the zip
  re-fire storm was unchanged, yet the same log had the server's new `206` range
  replies (server updated, client not). Root gap: `send_html` sent the HTML shell
  with no cache headers, so browsers pin an old client across deploys.
- Shipped **v0.2.12**: `send_html` now `Cache-Control: no-store` (+ Pragma/Expires).
  Client-side changes take effect on the next load. Boot smoke confirms `GET /`
  carries no-store and still serves the v0.2.12 client; full suite green. Commit
  note docs/commits/0014. Backup docs/notes/DropZone.py.bak6-*.
- Log-reading note for the future: with Range support (v0.2.10), a browser may
  split ONE single-file download into parallel `206` range parts — that is one
  saved file, NOT a duplicate. Only multiple full `200` completions are a dupe.
- Item 10 stays `[~]`: re-test on Android after loading the fresh (uncached) page.

## Last session — 2026-08-30 (later 8)
- BACKLOG 10 second fix shipped as **v0.2.11** (client only): fixed the Android
  download re-fire. Root cause was the single-file button being a bare navigating
  `<a download>` whose node the 2.5 s `/api/state` poll destroyed mid-download
  (list rebuilt via `innerHTML`), so the browser aborted+retried (same `[id]` ~3x,
  matching the poll cadence). Now: one detached, self-removing anchor on `<body>`
  for ALL downloads + a 1.5 s per-URL debounce, and `renderMyFiles`/`renderAllUsers`
  skip the rebuild when unchanged. Server download path untouched.
- Verified without a browser harness: `node --check` on JS/HOST_INIT/REMOTE_INIT,
  full server suite green, boot smoke shows the page carries `downloadOne`/
  `DL_DEBOUNCE_MS`/the render-skip guards. Commit note docs/commits/0013. Backup
  docs/notes/DropZone.py.bak5-*.
- Item 10 stays `[~]`: both fixes in, awaiting field confirm (Android re-fire gone
  = you can check now; iPhone dupe gone = when an iPhone is available).

## Last session — 2026-08-30 (later 7)
- BACKLOG 10 fix shipped as **v0.2.10**: HTTP Range support on `/api/download`
  (206 + `Content-Range`, `Accept-Ranges`/`ETag`/`Last-Modified`, `If-Range`, 416
  past EOF; malformed/multi-range -> 200). Root cause was iOS Safari's Range probe
  re-fetching against a 200-only server. Streamed zips untouched. Bonus: single
  downloads are now resumable/seekable. New `tests/test_download_range.py` (10
  checks) + whole suite green. Commit note docs/commits/0012. Pre-change backup at
  docs/notes/DropZone.py.bak4-*.
- Item 10 is `[~]` — code done, still owes an iPhone field confirm (small files,
  individual downloads, no `(1)` copies).
- Corrected the stale dev-copy path (was the travel-laptop `D:\\ClauDev_20260822\\
  DropZone`); this session edits `D:\\ClauDev\\DropZone`.
- Not done (deliberately): the Android triple-fire (client list re-render churning
  the anchor) and a `do_HEAD` for `/api/download` — logged as follow-ups.

## Last session — 2026-08-30 (later 6)
- BACKLOG 1 CLOSED by field test (v0.2.09): single 2.4/2.6/1.8 GB files + a 4.4 GB
  2-file batch, all byte-exact, RSS flat 12-16 MB, no freeze/OOM/traceback. The
  "single ~2 GB file" half of the DoD is now covered. Ticked in BACKLOG.md.
- Upload failures from device .94 were Android battery saver cutting the client
  radio (3x ConnectionResetError, 0 files, clean single-line log — no traceback,
  RSS low). Not a DropZone bug; server robustness worked. Upload completed after
  the browser was excluded from battery optimisation.
- "Everything felt slow" = the wifi path, NOT the app. Loopback (127.0.0.1) ran
  90-290 MB/s; real wifi devices ran 1.6-3.7 MB/s on the SAME server/disk/code.
  Cause: the host phone was the hotspot this round (serving + routing on one
  radio; dual-band selected but power-save likely engaged), and it was a
  different network (10.150.157.x vs the usual 192.168.7.x). Environmental.
- BACKLOG 10: re-fire CONFIRMED (same `[id]` 3x, 2 cancelled) but no `(1)` dupes
  on gigabyte files. Small-file race identified as the repro path (see Current
  focus). Still needs the small-file test to see the user-visible dupe.

## Last session — 2026-08-30 (later 5)
- Backlog cleanup from Gabe's field results: dropped BACKLOG 5 (long-list scroll)
  and BACKLOG 12 (light/dark theme). Item 5 tested clean at 1100 files (all
  listed, scrolls to bottom); item 12 was a browser forced-night-mode setting,
  not our bug. Both marked `[-]` in BACKLOG.md with the reason.

## Last session — 2026-08-30 (later 4)
- Added tests/ safety net (dependency-free; items 1/6/13) with README; wired
  into DEVELOPMENT.md. `python3 tests/run_all.py`.
- Attempted CSS fixes for theme (12) + list scroll (5) as v0.2.10, but they were
  speculative (couldn't reproduce either bug). Gabe asked to REVERT them — done;
  build is back to v0.2.09. Between-session theme persistence is NOT wanted.
- Theme (12): CLOSED — the reported bug was a browser setting forcing night mode
  on the device, not a DropZone defect. Dropped from the backlog. (Prior lead
  about the sets falling through to the OS default is moot.)
- Versioning: number is major.beta.nightly; VERSION_STAGE label redundant
  (candidate cleanup). Hold at 0.2.xx. Git: Gabe commits manually.
- GIT STATE (2026-08-30): HEAD committed at **0.2.12** (includes commit notes
  0012-0014). UNCOMMITTED in the working tree: the net 0.2.13->0.2.14 code
  (DropZone.py now 0.2.14), the doc updates (BACKLOG/CHANGELOG/SESSION/
  test_download_range), and commit notes 0015-0016 + audit-guide-downloads.md.
  Commit the working tree as a single **0.2.14** — v0.2.13 (blob) was reverted
  within the tree, so the net diff from 0.2.12 is just the 0.2.14 state. Commit
  note 0015 documents that reverted blob (history only).

## Last session — 2026-08-30 (later 3)
- v0.2.09: ZIP downloads STREAM as built (BACKLOG 13 done). Hand-rolled,
  uniformly-zip64 STORE streamer with an exact-size formula, so downloads start
  instantly (TTFB ~1 ms vs tens of seconds), no temp file, real progress bar,
  flat memory. Verified byte-exact incl. >4 GiB, valid under python + unzip,
  clean mid-stream cancel. Findings in docs/notes/streaming-zip-findings.md.
- Fix: non-ASCII upload filenames were mangled since v0.2.05 (latin-1 header
  decode); now UTF-8, round-trip correct.
- Robustness: request-side connection resets log one line, not a traceback.
- Likely knock-on: this should defuse the duplicate-download re-clicks (BACKLOG
  10) since there is no spool wait to click through — confirm in the field.

## Last session — 2026-08-30 (later 2)
- Fixed a field-reported host-page bug: bulk ZIP clicks navigated the whole
  page to the download URL (confirmBulk did window.location.href; smaller zips
  let the plain anchor navigate), so the page went blank during the spool and a
  refresh re-fired the download (the log shows one host zip fired 8x). Downloads
  now go through a hidden `download` anchor — no navigation, no refresh-dupe.
- Host activity panel now floats bottom-centre, out of flow: always visible and
  no page jump on update. v0.2.08.
- Deferred (BACKLOG 14): optionally merge the upload progress bar and the host
  activity into one status area, per field feedback ('combine with the progress
  bar'). Floating panel is the interim.

## Last session — 2026-08-30 (later)
- Field run confirmed the streaming upload holds up: a 1.2 GB upload stayed at
  ~20 MB RSS and multi-file batches at 13-18 MB; a 3-device / 3-simultaneous
  1 GB+ zip-download pressure test completed with every cancel logged cleanly
  (no unhandled traceback). Note: transfers are NOT one-at-a-time —
  MAX_CONCURRENT_TRANSFERS=4 runs up to four at once; the felt delay is the
  silent spool-to-disk phase before the first byte is sent.
- v0.2.07: live transfer activity feedback (BACKLOG 6, feedback half). Every
  page shows a "Host activity" banner (phase + queue position) fed by the
  /api/state poll. Verified in the container (sem forced to 1: one sending, two
  queued #1/#2, drains clean).
- Investigated streaming the zip as it is built (BACKLOG 13): feasible, keeps an
  exact Content-Length, but the length calc must branch on the 4 GiB zip64
  thresholds. Findings in docs/notes/streaming-zip-findings.md; deferred as its
  own item.
- Reported: light/dark theme regression (BACKLOG 12) — not caused by the recent
  work (theme code unchanged vs backups); needs repro details to pin.

## Last session — 2026-08-30
- Confirmed the upload-freeze cause from the v0.2.04 field log: server RSS tracked
  upload size, and the 700 MB and 3.5 GB uploads were OOM-killed. Finding appended
  to `docs/notes/upload-freeze-log.md`.
- v0.2.05: streaming multipart upload — `stream_multipart()` parses the body from
  the socket in 1 MB chunks and writes each file straight to disk; `do_POST` no
  longer reads the whole body into RAM, so peak memory is now flat.
- v0.2.05: real upload progress bar via XMLHttpRequest `upload.onprogress`
  (percent, bytes, ETA), replacing the fake `setInterval` timer (BACKLOG 9).
- v0.2.06: hoisted the upload read size to a named `UPLOAD_CHUNK` constant and
  set it to 4 MB (was 1 MB). Re-verified in the container — the 1.2 GB upload
  peaked at ~30 MB RSS, byte-exact.
- Verified in the container: small, 2-file, and 1.2 GB uploads all byte-exact
  (size + sha256); server peak RSS ~23 MB through the 1.2 GB upload.
- Pre-change backup at `docs/notes/DropZone.py.bak3-20260830-*`. BACKLOG 1 kept
  `[~]` pending the phone field test; BACKLOG 9 ticked.

## Last session — 2026-08-27
- v0.2.01: added `__version__` / `VERSION_STAGE`; header + startup banner show
  the running build.
- v0.2.02: DEBUG log() + rss_mb(); instrumented the upload path; silenced benign
  download-side BrokenPipeError.
- v0.2.03: ZIP downloads now STORE (no compression); terminal logs the full
  download/zip lifecycle with file ids.
- Confirmed on the phone: banner and page show the version. Smoke-tested each
  build in the device VM (compile, boot, upload, zip=STORED, logs fire).
- Backlog updated from field notes: added items 9 (real progress bar), 10
  (duplicate downloads), 11 (split big archive); item 6 partly done.
- Pre-change backups in `docs/notes/DropZone.py.bak*`.

## Decisions
- Tests live in `tests/` (dependency-free; `python3 tests/run_all.py`). Run after
  any change to upload / download-ZIP / transfer / `/api/state` code. Covers
  backlog items 1, 6, 13. Added 2026-08-30.
- Workflow: docs-driven loop, one backlog item per session (see DEVELOPMENT.md).
- Versioning: `release.beta.incremental` (e.g. v0.2.01). Baseline v0.2.00;
  next shipped app change v0.2.01.
- Commits: staged as Markdown notes in docs/commits/ while off git, replayed
  later.
- First tackle: upload freeze, starting with logging to confirm the cause.

## Open questions / watch-outs
- Two machines: this session edits the PC dev copy at
  `D:\\ClauDev\\DropZone`. The phone's Termux runs a separate copy
  (traceback showed `/storage/emulated/0/Backups/DropZone/DropZone_v2.py`).
  Edits here do NOT reach the phone by themselves.
- Deploy transport = Syncthing (LAN). Target workflow: sync the PC dev folder to
  the phone's run folder, retire the `_v2` name, make the widget run
  `DropZone.py`, so deploying = save on PC -> Syncthing pushes -> tap widget.
  Confirm the phone's run folder is the Syncthing target (see below).
- Verify the running build from the banner/page: `build vX.Y.ZZ · stage`.
- Upload-freeze root cause CONFIRMED (whole body read into RAM, then copied
  again by `parse_multipart`) and fixed in v0.2.05 by streaming to disk. The
  only open risk is whether the phone's real ~2 GB behaviour matches the
  container test.

## How to pick up
1. Read this file, then the top item in BACKLOG.md.
2. Do that one item; verify with its Definition of done.
3. Update this file, tick BACKLOG.md, add CHANGELOG + a docs/commits/ note.
