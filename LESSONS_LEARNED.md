# LESSONS LEARNED — DropZone

What was tried and did not survive. The trip-wire list. Each entry: what was tried, why it failed, the evidence.

## Downloads (BACKLOG 10 saga, v0.2.10–v0.2.14)
### L1 Advertise `Accept-Ranges` to fix the iOS-Safari duplicate
**What was tried.** v0.2.10 advertised `Accept-Ranges`/`ETag`/`Last-Modified` and answered `Range:` with 206, to stop iOS Safari's Range probe from re-fetching and creating `name (1).ext`.
**Why it failed.** It fixed Safari but made Chrome start a download, cancel it, and re-fetch in parallel 206 ranges — a small file finished the first plain attempt before the cancel and saved twice. Net: it moved the duplicate from Safari to Chrome. Resolved v0.2.14 by keeping the 206 handler but NOT advertising `Accept-Ranges`.
**Evidence.** Field logs v0.2.10–v0.2.14; docs/commits/0012 and 0016; tests/test_download_range.py.

### L2 A JS debounce to stop the Android re-fire
**What was tried.** v0.2.11 debounced the download anchor, assuming the repeated `[id]` (~3×, matching the 2.5 s poll) was our client double-firing.
**Why it failed.** Two layers hid behind it. First the phone ran a CACHED old page (fixed by `no-store`, v0.2.12). Then, with the fresh client confirmed, small files STILL completed 2–3× — proving the repeats came from the browser's own download manager (probe + real request), which a JS debounce cannot stop. The real fix was server-side (L1). The debounce was kept only as a cheap double-tap guard.
**Evidence.** v0.2.11/0.2.12 field logs; CHANGELOG [0.2.11]–[0.2.13]; SESSION pre-migration "later 9/10".

### L3 Blob / in-page download for small files
**What was tried.** v0.2.13 fetched files at/under `BLOB_DL_MAX` in JS and saved via a blob URL — one fetch = one request = one file, which did dedup.
**Why it failed.** UX was unacceptable: it buffered the whole file with no feedback (downloads felt dead) and stacked multiple save dialogs on re-tap. REVERTED in v0.2.14. Do not resurrect.
**Evidence.** v0.2.13 log (one fetch per file); docs/commits/0015 (history) and 0016 (revert); docs/notes/audit-guide-downloads.md "REMOVED — do not resurrect" (archived).

## Investigations that found no code defect
### L4 Speculative CSS fixes for theme + long-list scroll
**What was tried.** A v0.2.10 attempt patched the light/dark theme (BACKLOG 12) and the long-list scroll (BACKLOG 5) via CSS.
**Why it failed.** Neither bug reproduced. The scroll tested clean at 1100 files; the theme "regression" was a browser setting forcing night mode on the device, not a DropZone defect. Gabe asked to revert; build returned to v0.2.09. Both items dropped `[-]`.
**Evidence.** Headless-Chromium measurements (dark bg luminance 22 / text 207; light bg 243 / text 37; toggle flips both ways); SESSION pre-migration "later 4/5"; BACKLOG items 5 and 12 (archived).

### L5 The fake upload progress timer
**What was tried.** The original bar was a `setInterval` creeping to ~82% then jumping to 100% on response.
**Why it failed.** It was not tied to real bytes, so it hid where an upload actually stalled. Replaced v0.2.05 by an `XMLHttpRequest` driving the bar from `upload.onprogress` (true bytes + ETA), which also visibly halts at a stall point.
**Evidence.** CHANGELOG [0.2.05]; BACKLOG item 9 (archived).
