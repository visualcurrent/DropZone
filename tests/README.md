# DropZone tests

A lightweight safety net for the behaviours that were hard to get right. There is
no test framework and no third-party dependency (same rule as the app) — each
test is a plain Python script that starts the **real** server and checks what it
actually does over the wire.

## How to run

From the project root:

```
python3 tests/run_all.py          # run everything
python3 tests/test_zip_streaming.py   # or one at a time
```

Each script prints a short result and exits `0` on pass, non-zero on fail.
`run_all.py` runs all three and fails if any fails.

## What each test covers

| Test | Backlog | Checks |
|------|---------|--------|
| `test_upload_memory.py`  | 1  | Uploads (small / multi / 800 MB) save byte-exact (size + sha256) **and** peak server memory stays flat — it must not scale with upload size (the old OOM-on-big-files bug). |
| `test_queue_feedback.py` | 6  | With the transfer cap forced to 1, three concurrent downloads show up in `/api/state` as one `sending` + others `queued` with positions, and the registry drains to empty. |
| `test_zip_streaming.py`  | 13 | The per-user ZIP streams as it is built: advertised `Content-Length` == bytes streamed == `DropZone.zip_stream_size()`, first byte is near-instant, the archive is valid (Python `zipfile`, and Info-ZIP `unzip -t` if installed) and extracts byte-exact, and a mid-stream cancel leaves no traceback. |

## How it works (for the next agent)

- `_dz_harness.py` copies `../DropZone.py` to a temp file with only `PORT`
  (and, where needed, `MAX_CONCURRENT_TRANSFERS`) patched, launches it on a high
  port (8071–8073), and drives it with raw sockets. So the tests never touch a
  running instance and never edit the real file. They always test the CURRENT
  `DropZone.py` next to `tests/`.
- Requirements: Python 3 standard library only. The memory checks read
  `/proc/<pid>/status`, so they need Linux/Termux (they run on the phone host and
  in a Linux container; they will not measure memory on Windows/macOS).
  `unzip` is optional — the ZIP test skips the Info-ZIP cross-check if it is absent.

## When to run them

After any change to the upload path, the download/ZIP path, the transfer
registry, or `/api/state`. They are the Definition-of-done check for backlog
items 1, 6, and 13, and cheap insurance against regressing them. If you add a new
behaviour worth locking down, add a `test_*.py` here the same way and list it in
`run_all.py`.
