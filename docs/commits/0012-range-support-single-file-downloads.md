Range support on single-file downloads (v0.2.10)

Fix duplicate downloads from iOS Safari (BACKLOG 10). Diagnosis from the
2026-08-30 field log + the code: `/api/download` always replied `200` with the
full body and no `Accept-Ranges`, and it ignored an incoming `Range:` header.
iOS Safari probes a downloadable media file with a Range request and, when the
server answers a plain `200` instead of `206`, treats the probe and the real
save as two independent complete downloads — the OS then suffixes the second as
`name (1).ext`. Android Chrome takes the single `200` cleanly, which is why the
duplicates only ever reproduced from an iPhone.

- New `parse_range(header, size)`: parses one byte-range (closed, open-ended,
  suffix). Returns `("unsatisfiable", None)` for a start at/after EOF, and
  `(None, None)` — meaning "serve a normal 200" — for an absent, malformed, or
  multi-range header (RFC 7233: an unparsable Range MUST be ignored).
- `/api/download` now sends `Accept-Ranges: bytes`, an `ETag` (mtime+size) and
  `Last-Modified` on every response. With a satisfiable `Range` it replies `206`
  + `Content-Range: bytes s-e/size` and streams just that slice; a range past
  EOF is `416` with `Content-Range: bytes */size`. `If-Range` gates the range —
  a validator mismatch falls back to the full `200`.
- Slice delivery: spans <= STREAM_THRESHOLD are one buffered `seek`+`read` (fast,
  and a tiny Safari probe never consumes a heavy-transfer slot); larger spans
  stream from disk via `seek` under the existing transfer registry/semaphore.
- Bonus: single-file downloads are now resumable and seekable. Streamed
  "download everything" zips are unchanged (still `200`, no ranges — the archive
  is generated on the fly and can't cheaply satisfy arbitrary byte ranges, and
  they were never the source of the `(1)` duplicates).

Test: `tests/test_download_range.py` (10 in the backlog map) — full 200 with the
new headers; closed/open-ended/suffix 206 with offset-exact slices on a
patterned body; 416 past EOF; stale `If-Range` and multi-range both -> 200; a
>STREAM_THRESHOLD slice streamed via seek, byte-exact; no traceback in the log.
Whole suite green (`python3 tests/run_all.py`).

Not done here (candidate follow-ups): the Android-side triple-fire seen in the
log (same `[id]` 3x, ~1 s apart ~ the `/api/state` poll) is a separate,
lower-confidence client issue — the file list is rebuilt with `el.innerHTML`
every second; a re-render guard would address it. And a `do_HEAD` for
`/api/download` would answer a HEAD probe cleanly (currently 501). Left out to
keep this change focused on the grounded Safari fix. Field step: confirm on an
iPhone that individual small-file downloads now land once each.
