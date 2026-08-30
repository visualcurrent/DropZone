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

**Running build now v0.2.10 (nightly)** — adds HTTP Range support to single-file
downloads (BACKLOG 10). Root cause of the `(1)` duplicates was iOS Safari probing
a download with a Range request and re-fetching because `/api/download` only ever
replied `200`; it now answers `206` + `Content-Range` (with `Accept-Ranges`/
`ETag`/`Last-Modified`/`If-Range`, `416` past EOF). Android's single-`200` path is
why it never reproduced Android-to-Android. Zips unchanged. Tested green
(`tests/test_download_range.py`, whole suite passes).

**Next on the phone — field-confirm the Range fix (closes BACKLOG 10):** on an
iPhone, download several SMALL files individually (one tap each) and confirm they
land once each — no `name (1).ext`. If a dupe still appears, capture the browser
and the `[id]` log lines. (Deploy v0.2.10 to the phone via Syncthing first.)

Then next code target: the host connected-users panel (BACKLOG 4). A separate,
lower-priority thread stays open: the Android download triple-fire (same `[id]`
3x ~ the 1 s `/api/state` poll) — a list-re-render guard on the client.

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
  (candidate cleanup). Hold at 0.2.xx. Git: Gabe commits manually (2.06-2.09 in).

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
