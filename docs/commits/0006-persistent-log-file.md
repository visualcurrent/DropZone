Persist logs to DropZone.log so records survive a Termux crash (v0.2.04)

From a field note: Termux terminal output vanishes when it crashes — exactly
when the freeze logs matter most.

- log() now always appends to `DropZone.log` beside the script, flushed and
  closed per line (verified to survive kill -9). DEBUG still controls console
  echo only.
- Route unhandled per-request errors into the log via a _LogErrors mixin on both
  the threaded and single-threaded servers; log a fatal in serve_forever.
- Startup writes a "=== starting; version; pid ===" marker; the log rolls to
  DropZone.log.1 once it passes 5 MB; the banner prints the log path.
- .gitignore: ignore DropZone.log and DropZone.log.1 (runtime data).
- Bump __version__ to 0.2.04 (nightly).
