# ARCHITECTURE — DropZone

As-built structure. Update when a layer lands or a contract changes.

## Layers
| Layer | Modules | Status |
|---|---|---|
| HTTP server | `ThreadingServer` / `SingleServer` (`THREADED`), `Handler(BaseHTTPRequestHandler)`, `make_server` | shipped |
| Upload | `do_POST` `/api/upload` -> `stream_multipart` (socket -> disk in `UPLOAD_CHUNK` blocks) | shipped, field-confirmed |
| Download (single) | `do_GET` `/api/download` -> `parse_range` + buffered/streamed split at `STREAM_THRESHOLD` | shipped |
| Download (bulk zip) | `/api/download_all`, `/api/download_everything` -> `zip_stream` / `zip_stream_size` (hand-rolled uniform-zip64 STORE streamer) | shipped |
| Transfer registry | `transfer_start/set/end`, `transfers_public`, `transfer_sem` (`MAX_CONCURRENT_TRANSFERS`) | shipped |
| State / API | `/api/state` (1 s poll), `/api/session`, `/api/rename`, `/api/remove_file`, `/api/speedtest` | shipped |
| UI (embedded) | `CSS`/`JS`/`HOST_*`/`REMOTE_*` strings -> `make_page`; host + remote pages, QR join, activity banner | shipped |

## Data flow
Guest browser -> `POST /api/session` (gets a sid + friendly name) -> uploads via `XMLHttpRequest` to `/api/upload` (real progress from `upload.onprogress`); the server streams the multipart body to a temp file and keeps only metadata (name/size/path) in RAM. Every page polls `/api/state` each second for the file list (grouped by user, own section pinned to the bottom) and the host-activity banner. Downloads: single files via `/api/download` (plain 200, native browser UI); bulk via `/api/download_all` (one user) and `/api/download_everything` (everyone else, foldered per user), streamed as built. Uploads live on disk in a temp folder cleared on Ctrl+C; state is in-memory and clears on restart.

## Contracts to preserve (break silently if drifted)
1. `/api/download` must NOT advertise `Accept-Ranges` on its 200/206 responses. It looks like a missing header; it is deliberate — advertising it makes Chrome start/cancel/re-segment and duplicates small files. The 416 branch keeps its own `Accept-Ranges` (range-specific, rarely hit, harmless).
2. `send_html` must stay `Cache-Control: no-store` (+ `Pragma`/`Expires`). The page inlines all CSS/JS; without it browsers pin an old client across deploys.
3. The Range apparatus (`parse_range`, the 206/416 branch, `ETag`, `Last-Modified`, `If-Range`) is reached only on an explicit `Range:` header (iOS Safari probe + resume). Keep it whole or remove it wholesale — never half-remove.
4. Bulk-zip byte layout is uniform zip64 so the length is a closed form; `zip_stream` output bytes MUST equal `zip_stream_size(entries)` exactly. A one-byte error breaks the transfer. Covered by `tests/test_zip_streaming.py`. The closed form: per file `= 30 + name + 20 + size + 24 + 46 + name + 28` (i.e. `size + 2*name + 148`); end `= 56 + 20 + 22` (i.e. `98`).
5. The upload path (`uploadFiles` client, `stream_multipart` / `do_POST` server) is memory-bounded and untouched since the upload-freeze fix — peak RSS must not scale with upload size. Covered by `tests/test_upload_memory.py`.
6. The `/api/state` `transfers` list drives the activity banner (queued / preparing / sending + queue position); every page polls it each second. Covered by `tests/test_queue_feedback.py`.

## Streaming-zip design (v0.2.09)
A hand-rolled STORE streamer (`zip_stream` / `zip_stream_size`), chosen over predicting `zipfile`'s per-field zip64 decisions (it decides zip64 per field by actual value). Uniformly zip64: every file gets 8-byte size/offset fields and a data descriptor, and the archive always ends with a zip64 EOCD + locator + EOCD, so the byte layout is fixed and the exact size is a closed form (above) — the browser keeps a real progress bar, not a spinner. Uniform zip64 costs ~148 bytes/file regardless of size — negligible. Verified byte-exact including a 5 GiB single file past the 4 GiB boundary; archives pass `zipfile.testzip()` and Info-ZIP `unzip -t` and extract byte-exact; time-to-first-byte ~1 ms; peak RSS ~30 MB for a 364 MB archive; mid-stream cancel logs cleanly. Full evidence: `_archive/streaming-zip-findings.md`.
