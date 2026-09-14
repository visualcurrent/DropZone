In-page blob save for small downloads — the real duplicate fix (v0.2.13)

BACKLOG 10, take 3. v0.2.10 fixed the iOS-Safari case via Range; v0.2.11 added a
click debounce for the Android re-fire; v0.2.12 no-stored the shell so client
changes actually deploy. With v0.2.12 confirmed running on the phone (header
showed v0.2.12, browser data cleared) the small-file duplicates PERSISTED — a
128 KB jpg completed three times, a 3 MB pdf twice-plus-segments, etc.

Conclusion: the repeats are the browser's own download manager, not our code and
not a double tap. Tapping a download link makes the browser issue a probe/preview
request AND the real download request; on a SMALL file both complete, so the OS
saves two copies (`name (1).ext`) — which matches the original field report that
duplicates only happened on small files. On a LARGE file the probe is aborted
before it finishes, so there is one file. A JS click-debounce cannot touch this
because the extra requests are issued by the browser, below our anchor.

Fix (client-only): route downloads through one `startDownload(url, size)`:
- size <= BLOB_DL_MAX (64 MB): `blobSave(url)` — `fetch()` the file into memory and
  save it once via an object URL (filename from Content-Disposition). A fetch is a
  single request the browser neither probes nor segments, so it is exactly one GET
  and one saved file. Falls back to the native path on any fetch error.
- size >  BLOB_DL_MAX: `nativeDownload(url)` — detached anchor; the browser may
  segment into parallel 206 ranges, which assemble into one file (too big to hold
  in memory anyway).
Single-file buttons pass `f.size`; small "download all"/everything zips take the
same path via `confirmBulk`. The 1.5 s debounce is kept as a cheap guard on our
own fires. Server `/api/download` is unchanged (still serves 200/206 correctly).

Trade-off: a blob download shows no native progress bar and buffers the file in
memory, which is why it is gated to <= 64 MB; the dupe victims (photos,
screenshots, small pdfs/apks) are all well under that.

Verified: `node --check` on JS/HOST_INIT/REMOTE_INIT; full server suite green;
boot smoke shows the page carries `blobSave`/`startDownload`/`BLOB_DL_MAX` and the
`no-store` header. Field step (Android, cache already clears via no-store): tap a
small file — it should save once, and the log should show a single full `200`
`download [id]` with no repeats.
