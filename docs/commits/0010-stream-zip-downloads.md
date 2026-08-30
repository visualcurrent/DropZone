Stream ZIP downloads as they are built (v0.2.09)

Replace spool-whole-then-send with streaming the STORE archive straight to the
socket (BACKLOG 13). Motivated by the v0.2.08 field log: three concurrent
"download everything" archives (2.6-3.0 GB) each spooled a full temp copy before
the first byte — ~50-60 s of silence and ~8 GB of temp files — which invited
re-clicks (more concurrent spools, OS-suffixed duplicate downloads).

- New zip_stream() / zip_stream_size(): a hand-rolled STORE zip written to a
  write() callback as each source file is read in 1 MB chunks. No temp file, no
  whole file/archive in RAM. The layout is *uniformly* zip64, so the exact
  archive size is a closed form — we send a real Content-Length and the browser
  shows a true progress bar. Verified byte-exact vs the emitter across
  ascii/space/unicode names and past the 4 GiB boundary; archives validate under
  Python zipfile and Info-ZIP `unzip -t`.
- stream_zip() (the handler) now computes the length, sends headers, and streams;
  the RAM/spool branch and the temp file are gone. Phase goes straight to
  "sending" (no more "preparing"). Re-stats sources so the advertised length and
  the streamed bytes agree.
- Fix: upload filenames are decoded UTF-8, not latin-1 (RFC 7578). Non-ASCII
  names (accents, CJK) were being mangled on upload since the streaming multipart
  parser landed in v0.2.05; they now round-trip correctly (also into zip names).
- Robustness: handle_error() now logs a one-line note for client connection
  drops (ConnectionReset/BrokenPipe/Aborted/Timeout) instead of a full traceback
  — silences the request-read reset seen in the v0.2.08 log.

Measured in the container: time-to-first-byte ~1 ms (was tens of seconds),
Content-Length == streamed bytes == formula, peak RSS ~30 MB during a 364 MB
archive, valid archive, and a mid-stream cancel logged cleanly with no traceback.
