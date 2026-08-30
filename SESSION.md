# DropZone — Session Handoff

Read this first at the start of every session. Update it last.
See `docs/DEVELOPMENT.md` for how the workflow runs, `BACKLOG.md` for what's next.

## Current focus
Running build is **v0.2.06 (nightly)** (deploy to the phone via Syncthing
-> Downloads -> /storage/emulated/0/Backups/DropZone). DEBUG=True is on.

Logs persist to `DropZone.log` beside the script (survives a Termux crash), so
instead of copying terminal scrollback, just send that file's contents back.

v0.2.05 shipped the streaming upload fix (BACKLOG 1) and the real progress bar
(BACKLOG 9). The freeze cause is confirmed and the fix is verified in the
container (a 1.2 GB upload peaked at ~23 MB RSS, byte-exact). What remains is
field confirmation on the phone.

**Two things to do on the phone next:**
1. Close BACKLOG 1: run a single ~2 GB upload and a multi-user ~1 GB-per-user
   run on the phone. Confirm from `DropZone.log` that the RSS lines stay flat,
   there is no freeze, and the listed size matches the real file. While there,
   watch the new real progress bar halt at the true point if an upload stalls
   (BACKLOG 9).
2. Duplicate downloads (BACKLOG 10): repeat the download test and read the
   per-file `[id]` logs — same id twice = real double-fire; different ids same
   name = OS dedup on save.

Then next code target: the duplicate-downloads decision (BACKLOG 10), then the
host connected-users panel (BACKLOG 4).

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
- Workflow: docs-driven loop, one backlog item per session (see DEVELOPMENT.md).
- Versioning: `release.beta.incremental` (e.g. v0.2.01). Baseline v0.2.00;
  next shipped app change v0.2.01.
- Commits: staged as Markdown notes in docs/commits/ while off git, replayed
  later.
- First tackle: upload freeze, starting with logging to confirm the cause.

## Open questions / watch-outs
- Two machines: this session edits the PC dev copy at
  `D:\\ClauDev_20260822\\DropZone`. The phone's Termux runs a separate copy
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
