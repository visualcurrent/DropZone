# Upload-freeze session — saved terminal log

Context from the user: uploads run fast then freeze near 90%; even one large
file freezes near 80%; rough ceiling ~1.8 GB. Host is a phone in Termux with
~70 GB free, ~1 GB per user, 2 users. F5 after a freeze shows the file listed
but with a cut-off size.

Note: the traceback below is on the **download** path (`stream_zip` ->
`copyfileobj` -> socket `sendall`) and is a `BrokenPipeError` (client
disconnected mid-download). That is relevant to BACKLOG item 6, not necessarily
to the upload freeze (item 1). Keep the two separate during analysis.

## Raw log

```
  ╔══════════════════════════════════════════╗
  ║         DropZone is running!             ║
  ╠══════════════════════════════════════════╣
  ║  Host page  →  http://localhost:7070    ║
  ║  Remote URL →  http://53.183.254.0:7070/remote
  ╠══════════════════════════════════════════╣
  ║  Ctrl+C to stop (cleans up temp files)  ║
  ╚══════════════════════════════════════════╝

----------------------------------------
Exception occurred during processing of request from ('127.0.0.1', 46202)
Traceback (most recent call last):
  File "/data/data/com.termux/files/usr/lib/python3.13/socketserver.py", line 697, in process_request_thread
    self.finish_request(request, client_address)
  File "/data/data/com.termux/files/usr/lib/python3.13/socketserver.py", line 362, in finish_request
    self.RequestHandlerClass(request, client_address, self)
  File "/data/data/com.termux/files/usr/lib/python3.13/socketserver.py", line 766, in __init__
    self.handle()
  File "/data/data/com.termux/files/usr/lib/python3.13/http/server.py", line 447, in handle
    self.handle_one_request()
  File "/data/data/com.termux/files/usr/lib/python3.13/http/server.py", line 435, in handle_one_request
    method()
  File "/storage/emulated/0/Backups/DropZone/DropZone_v2.py", line 222, in do_GET
    self.stream_zip(entries, f"DropZone-{safe}.zip")
  File "/storage/emulated/0/Backups/DropZone/DropZone_v2.py", line 157, in stream_zip
    shutil.copyfileobj(fh, self.wfile, 256 * 1024)
  File "/data/data/com.termux/files/usr/lib/python3.13/shutil.py", line 204, in copyfileobj
    fdst_write(buf)
  File "/data/data/com.termux/files/usr/lib/python3.13/socketserver.py", line 845, in write
    self._sock.sendall(b)
BrokenPipeError: [Errno 32] Broken pipe
```

---

## Confirmation — 2026-08-29 (v0.2.04 field run, phone/Termux)

**Verdict: hypothesis CONFIRMED.** The server holds the whole upload in RAM,
peak memory is a multiple of file size, and the phone OOM-kills the process on
large uploads. This is the freeze, and the OS kill mid-read is the cut-off
(partial) size seen on F5.

### Evidence — RSS tracks file size

Read the RSS values from `DropZone.log` at each upload stage:

| Upload size | RSS after `body read` | RSS after `parsed` | Outcome |
|---|---|---|---|
| 285 MB | 288.6 MB | 555.7 MB | done (~2x file) |
| 567 MB | 553.3 MB | 548.1 MB | done (~1x) |
| 691 MB | 667.7 MB | 883.6 MB | done (~1.3x) |
| 372.8 MB (2 parts) | 386.5 MB | 759.2 MB | done (~2x) |
| 700.2 MB | 714.0 MB | — | **process died** (restart follows, no "done") |
| 3.5 GB | 2573.6 MB | — | **process died** (log ends, no "done"/"stopped") |

RSS after `body read` equals the file size almost exactly, then `parsed`
roughly doubles it. The two largest uploads produced no `parsed` / `done` line
and the process restarted or the log simply ended — an OOM kill, not a clean
stop.

### Source lines that cause it

- `do_POST` line 334: `body = self.rfile.read(length)` — reads the entire
  request body into one bytes object. RSS ≈ file size confirms this.
- `parse_multipart` (line 108): `data.split(b"--" + boundary)` plus the
  per-part `split` / `rstrip` create more full-size copies. RSS ≈ 2x file
  after this stage confirms it.
- The part body stays in RAM until `tmp.write_bytes(data)` at line ~338.

Peak memory therefore reaches ~2x (up to ~3x with several parts) the upload
size. On a phone a ~1.8 GB file drives peak past what the OS allows and the
process is killed — matching the observed ~1.8 GB ceiling.

### Side observations (separate concerns, not the freeze)
- `ConnectionAbortedError [Errno 103]` at line 334 during a 271.8 MB upload:
  the client socket died mid-`read`. Consistent with a cut-off body.
- `BrokenPipeError [Errno 32]` at line 142 `send_json` (a `/api/state` GET):
  a client disconnected while state was being written. Belongs with item 6
  (unhandled broken pipes), not item 1.

### Fix direction (unchanged, now justified by data)
Stream the request body from `self.rfile` to the temp file in bounded chunks
and parse the multipart framing incrementally, so peak RSS stays flat
regardless of upload size. Never hold the full body or the full part in RAM.

### Raw log — v0.2.04 run
See `DropZone.log` beside the script (source of the table above).
