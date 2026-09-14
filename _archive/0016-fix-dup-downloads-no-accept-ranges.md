Fix duplicate downloads via no-Accept-Ranges; revert blob (v0.2.14)

BACKLOG 10, take 4 — and the one that keeps the good UX. v0.2.13 proved the
duplicate could be killed (the blob path made exactly one request per small file
in the field log) but its UX was unacceptable: `fetch()`-to-blob buffers the whole
file before the save dialog, so a download over WiFi felt dead with no feedback,
and re-taps queued multiple fetches that popped multiple save dialogs at once.
Gabe: instant feedback (the native path, used above 64 MB) is far better.

Root cause of the duplicate (now understood): advertising `Accept-Ranges: bytes`
(added in v0.2.10 for Safari) makes Chrome's download manager start a plain
download, cancel it, and re-fetch the file in parallel `206` range segments. On a
LARGE file the plain attempt is cancelled before it finishes -> one file. On a
SMALL file the plain attempt completes before the cancel lands, AND the segmented
fetch completes -> two saved files (`name (1).ext`). This matches the field logs
(every native file did two full-200 attempts then split into ranges) and the
long-standing "duplicates only on small files" report.

Fix:
- Server: `/api/download` no longer sends `Accept-Ranges` on its responses (the
  416 branch keeps its own, which is range-specific and rare). The browser no
  longer knows to segment, so it does ONE plain download -> one file, with the
  instant native download UI. We STILL honor an explicit `Range` request with a
  `206` (parse_range/If-Range/Content-Range unchanged), so iOS Safari's probe and
  resume still work; we just stopped inviting segmentation on the plain 200.
- Client: reverted v0.2.13's blob machinery (blobSave/cdFilename/startDownload/
  BLOB_DL_MAX). `downloadOne` is native again (detached anchor via
  triggerDownload); `confirmBulk` likewise. The 1.5 s debounce stays as a guard
  against an accidental rapid double-tap. Removing the blob regex also clears the
  `SyntaxWarning: invalid escape sequence '\*'` seen at startup.

Trade-off: single-file downloads are single-connection (no parallel range
segmentation) and the plain 200 is non-resumable — both fine for a LAN one-shot
transfer, and explicit-Range clients still get 206.

Verified: no SyntaxWarning (compiled with warnings-as-errors); `node --check` on
the embedded JS; full server suite green (test_download_range updated to assert
the 200 does NOT advertise Accept-Ranges while a Range request still returns 206);
boot smoke confirms the served page is native (no blob), the 200 omits
Accept-Ranges, and a Range request returns 206. Field step (Android): a small file
downloads once, instantly, with no stacked dialogs.
