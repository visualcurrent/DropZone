Stream uploads to disk and add a real progress bar (v0.2.05)

Fix the P0 upload freeze (BACKLOG 1) and replace the fake upload timer with a
real one (BACKLOG 9). Confirmed cause first from the v0.2.04 field log: server
RSS tracked upload size (whole body read into RAM, then copied again by
parse_multipart), and the process was OOM-killed on the 700 MB and 3.5 GB
uploads. See docs/notes/upload-freeze-log.md.

Server:
- New stream_multipart(): parses the multipart body straight from the socket in
  1 MB chunks and writes each file part directly to its temp file. Never holds
  the whole body, or a whole part, in RAM. Peak buffer ~= one chunk + boundary.
- do_POST /api/upload now uses it instead of self.rfile.read(length) +
  parse_multipart. Per-file "upload saved" log line with id, size, and RSS;
  open file handles are closed on any mid-stream error.
- parse_multipart (the old whole-body parser) left in place, now unused.

Client:
- uploadFiles() now uploads via XMLHttpRequest and drives the bar from
  upload.onprogress (true bytes sent); fetch cannot report upload progress. The
  bar shows percent, bytes, and ETA, and stops at the real point on a stall. On
  full send it shows "Saving…" while the server writes to disk.

Verified in the container: small, 2-file, and 1.2 GB uploads all saved
byte-exact (size + sha256); server peak RSS stayed at ~23.5 MB (+2.2 MB over
idle) through the 1.2 GB upload. Field 2 GB test on the phone still owed to
fully close BACKLOG 1's Definition of done.
