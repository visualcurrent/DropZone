# GLOSSARY — DropZone

Every project-coined term in plain English. A term not here is not used in LOG, SESSION, or a reply.

- **Host page / Remote page** — the two served pages. Host is `http://localhost:7070` (the machine running DropZone); Remote is `http://<ip>:7070/remote` (what a QR-scanning guest opens).
- **sid** — per-visitor session id from `POST /api/session`; also keys the in-memory user (display name + files).
- **Transfer registry** — in-memory table of every heavy download/zip (`transfer_start/set/end`); `transfers_public` exposes it per viewer in `/api/state` so the activity banner can show phase and queue position.
- **`transfer_sem` / `MAX_CONCURRENT_TRANSFERS`** — semaphore capping simultaneous heavy transfers (default 4); a queued transfer waits on it.
- **`STREAM_THRESHOLD`** — 64 MB. At/under it a download or zip is buffered (exact size + progress bar); above it it is streamed from disk. Also the size split for the (removed) blob path.
- **`UPLOAD_CHUNK`** — 4 MB. Block size for reading the upload body off the socket in `stream_multipart`, keeping peak RAM flat.
- **`WARN_THRESHOLD`** — 512 MB. Above it a bulk zip runs a client speed probe and asks for confirmation (size + ETA) before starting.
- **`stream_multipart`** — parses the multipart upload body from the socket in `UPLOAD_CHUNK` blocks and writes each file straight to disk; replaced the whole-body `self.rfile.read(length)` that caused the OOM freeze.
- **Uniform-zip64 STORE streamer** (`zip_stream` / `zip_stream_size`) — the bulk-download zip builder. STORE = no compression; uniform zip64 = every file/archive uses zip64 fields so the exact byte length is computable up front.
- **Data descriptor** — zip general-purpose bit 3: each file's CRC is written after its data (needed when streaming to a non-seekable socket). Widely supported.
- **`triggerDownload` / `DL_DEBOUNCE_MS`** — the single detached, self-removing `<a>` on `<body>` that all downloads route through, plus a 1.5 s per-URL debounce guarding a double-tap.
- **Blob save** (`blobSave`, `startDownload`, `BLOB_DL_MAX`) — removed v0.2.13 approach that fetched a small file in JS and saved it via a blob URL. Reverted for bad UX; kept in the glossary only so it is recognised and not re-introduced.
- **Activity banner** — the ambient "Host activity" line on every page, fed by the `/api/state` poll, listing in-flight transfers with phase and, when queued, a position.
