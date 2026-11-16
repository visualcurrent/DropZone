# GLOSSARY — DropZone

Every project-coined term in plain English. A term not here is not used in LOG, SESSION, or a reply.

- **DropCast** — working name (Gabe, 2026-11-13) for the second app planned in PLAN M2: share one file, show its QR, guests download it and can share one back. Not checked against existing products.
- **Pair (DropCast)** — one shared file together with its own address and QR.
- **Host's phone / guest's phone (DropCast)** — the phone running the DropCast app, and any other device that opens its pages in a browser. Always named in full; never a bare "the phone".
- **Check, or claim (DropCast)** — what the host's phone does to a guest's upload once it has arrived: computes its MD5, looks for an identical file already held, makes its thumbnail. `claim` is the code name. Until it finishes the file is "being checked" and not yet shown to the host.
- **Received file (DropCast)** — a file a guest shared, as it appears on the host's screen under "Shared with you".
- **Landing page (DropCast)** — the page at `/` behind the host's receive-a-file QR: only "Share a file", nothing to download.
- **Copy-in (DropCast)** — copying a file the host shares into the app's own storage before serving it.
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
- **Preview, or peek** (`#peek`, `openPeek`, `fillPeek`, `peekStep`, `closePeek` / `peekShut`) — the full-screen overlay a tap on a network row opens (v0.2.24): the file's 320 px thumbnail at its own size or a large icon, its name, size and owner, Star and Download, and previous/next.
- **Sequence (preview)** — the list of file ids the preview steps through, copied when it opens and not reshuffled by later polls: the starred files when opened from the Starred section, otherwise every network file in page order.
- **Neighbours (preview)** — the previous and next file's pictures, drawn faded at the sides of the preview to show there is more to swipe to.
- **Star / Starred section** (`_stars`, `toggleStar`) — a viewer's own shortlist of files, kept only in that browser tab (`sessionStorage` key `dz-stars`); the Starred section lists them first in "Available on Network" and zips them through `/api/download_starred`. The host stores nothing about stars.
- **Marker** (`_mark`, class `mark`) — the one highlighted row in "Available on Network": the file last shown in the preview, or the owner's row of a file just unstarred in the Starred section.
- **Activity banner** — the ambient "Host activity" line on every page, fed by the `/api/state` poll, listing in-flight transfers with phase and, when queued, a position.
