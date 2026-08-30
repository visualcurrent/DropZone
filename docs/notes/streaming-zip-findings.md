# Streaming the ZIP as it is built — investigation (2026-08-30)

Question: replace "spool the whole archive to a temp file, then send it" with
"stream the archive straight to the socket as it is built"? Decision: worth
doing, as its own change (BACKLOG 13), after the activity feedback. Below is the
evidence from a scratch test, so the choice is informed.

## What was tested
A STORE (no-compression) zip written by Python's `zipfile` to a **non-seekable**
sink (mimicking the socket), compared with the normal seekable build.

## Findings
1. **Feasible with little code.** Pointing `zipfile.ZipFile` at the socket
   produces a valid archive: `testzip()` passes, contents byte-exact, unicode
   filenames intact, extracts cleanly.
2. **Data descriptors.** On a non-seekable sink `zipfile` sets general-purpose
   bit 3 and writes each file's CRC *after* its data. Standard and widely
   supported (Windows Explorer, macOS, 7-Zip, Android). Round-trips fine.
3. **Exact length is predictable in advance.** For STORE with known file sizes,
   a simple formula matched the streamed output to the byte:
   per file `30 + name + 16 + data` (local header + data descriptor + data) plus
   `46 + name` (central directory) plus `22` (end record). So we keep sending an
   accurate Content-Length → the browser keeps a *real* progress bar, not an
   indeterminate spinner. This was the main worry and it does not apply.
4. **zip64 is the catch.** The moment any single file reaches 4 GiB, or the whole
   archive reaches 4 GiB, the format switches to zip64 and the overhead changes
   (+~28 bytes/file plus an archive-level record). Realistic here (large media,
   "download everything"). The length calculator MUST branch on both thresholds;
   a one-byte error breaks the transfer.

## Trade-offs
Streaming pros: no silent spool delay (first bytes immediately, native browser
progress from t=0); no temp file (removes ~archive-size scratch per download —
~4 GB in the 3-way field test — and cuts disk I/O from 3 passes to 1); cancel
stops instantly; flat memory; keeps the exact progress bar.
Streaming cons: the exact Content-Length calculator incl. the zip64 branch is the
real cost and test burden; relies on data descriptors (fine on modern tools);
once headers are sent you are committed (a mid-stream source failure can only
drop the connection, whereas build-first can still return a clean error); a
transfer holds its semaphore slot for the whole network send.

## Recommendation
Implement as a hand-rolled STORE streamer (~120 lines) so one code path owns both
the byte layout and the length calc, instead of predicting `zipfile`'s internal
zip64 decisions. Headline test: streamed byte count == the Content-Length we
computed, across ascii/space/unicode names and across the 4 GiB thresholds;
validate the archives open on Windows, macOS, and Android.
