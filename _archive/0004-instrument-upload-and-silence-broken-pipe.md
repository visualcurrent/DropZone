Instrument upload path and silence benign broken pipes (v0.2.02)

BACKLOG item 1, step 1 (diagnostics before fix). No behavior change beyond
logging and cleaner error handling.

- Add DEBUG-gated log() and rss_mb() (reads /proc/self/status VmRSS, falls back
  to resource.getrusage). rss_mb() exposes whether the whole upload body is held
  in RAM.
- Log Content-Length, bytes read, part count, and RSS at each stage of
  /api/upload.
- Catch BrokenPipeError / ConnectionResetError around single-file and ZIP
  download writes; log as a client cancel instead of dumping a traceback (the
  noise seen in docs/notes/upload-freeze-log.md).
- Bump __version__ to 0.2.02, stage nightly (debug build).

Next: read the RSS logs from one large phone upload to confirm the memory cause,
then rework the upload to stream to disk in bounded chunks (v0.2.03).

- Startup banner also prints "build v{__version__} · {VERSION_STAGE}".
