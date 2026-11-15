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

### L8 Several separate downloads from one tap (U4)
**What was tried.** v0.2.17 and v0.2.19 test page: one tap starts every file as its own download, four ways (link click 1 s apart, a hidden frame per file 1 s apart, hidden frames all at once, link click 8 s apart), 5 files, run on six browsers.
**Why it failed.** No way works everywhere. Android Firefox keeps 2 to 4 of 5 however the downloads are started, unless each dialog is answered before the next download begins, which the page cannot detect. iPhone Safari keeps 1 of 5 with link clicks and 5 of 5 with frames. PC Chrome, once its multiple-download permission is blocked, saves nothing more and shows nothing. In every failing run the host still sent all 5 files. Dropped by Gabe 2026-11-16: an issue in any common browser rules the feature out; the per-file download buttons stay.
**Evidence.** LOG 2026-11-13, 2026-11-15, 2026-11-16 (`multi-test` log lines and Gabe's counts).

## Investigations that found no code defect
### L4 Speculative CSS fixes for theme + long-list scroll
**What was tried.** A v0.2.10 attempt patched the light/dark theme (BACKLOG 12) and the long-list scroll (BACKLOG 5) via CSS.
**Why it failed.** Neither bug reproduced. The scroll tested clean at 1100 files; the theme "regression" was a browser setting forcing night mode on the device, not a DropZone defect. Gabe asked to revert; build returned to v0.2.09. Both items dropped `[-]`.
**Evidence.** Headless-Chromium measurements (dark bg luminance 22 / text 207; light bg 243 / text 37; toggle flips both ways); SESSION pre-migration "later 4/5"; BACKLOG items 5 and 12 (archived).

### L5 The fake upload progress timer
**What was tried.** The original bar was a `setInterval` creeping to ~82% then jumping to 100% on response.
**Why it failed.** It was not tied to real bytes, so it hid where an upload actually stalled. Replaced v0.2.05 by an `XMLHttpRequest` driving the bar from `upload.onprogress` (true bytes + ETA), which also visibly halts at a stall point.
**Evidence.** CHANGELOG [0.2.05]; BACKLOG item 9 (archived).

### L12 Reading a video's embedded cover picture instead of grabbing a frame
**What was considered.** Gabe, 2026-11-16: most video files may carry an embedded thumbnail; read that instead of drawing a frame, which Android Firefox cannot do.
**Why it was not pursued.** None of the four films on hand had one: three `.mp4` files with a tag block but no `covr` cover box, one `.mkv` with no attached picture. Phone recordings are not expected to carry one either [assumed]. Parsing the box tree in the page would be real work for files that mostly have nothing to find. Gabe chose to keep the frame grab.
**Evidence.** LOG 2026-11-16 (v0.2.23 passes on PC Chrome entry): index-only reads over adb of the four stored films.

### L11 Video thumbnails: "fade-in from black" fix (v0.2.18)
**What was tried.** Some video thumbnails were black on v0.2.16; v0.2.18 moved the frame from 0.1 s in to 10% in, on the assumption that clips fade in from black.
**Why it failed.** The assumption was never tested. On v0.2.22 two feature films were black on four browsers; a bright test video was black too. The real cause was jumping before the first frame was decoded (fixed v0.2.23). Reproducing the fault on a known-bright video would have shown this before the first fix.
**Evidence.** LOG 2026-11-16 (v0.2.23 entry): scratch runs in headless Edge, brightness 0 before the fix and 127 after.

### L9 Pages look bigger on the Samsung than on the Xiaomi
**What was seen.** Gabe, 2026-11-16: every element and all text on the host and guest pages looked big and clunky on the Samsung (SM-S921B) and fine on the Xiaomi (23116PN5BC).
**Cause.** The phones and the browser, not the page. The Samsung gives a page 360 layout px across (1080 px at density 480), the Xiaomi 411 (1080 px at density 420), so every element is about 14% larger on the Samsung. Firefox's "Automatic font sizing" then scales text by the system font scale, which on the Samsung reads above 1.0 even one notch below its slider's middle; turning it off made the page look normal. The page fixes its text at 16 px and turns off the browser's text resizing. Nothing changed in `DropZone.py`; do not chase this there, and do not override Firefox's setting, which is an accessibility feature.
**Evidence.** `wm size`, `wm density`, `settings get system font_scale` on both phones (Samsung 1.15 then 1.08, Xiaomi 1.0); Gabe's Firefox toggle; LOG 2026-11-16.
### L10 Slow transfers from a phone to this PC
**What was seen.** 2026-11-13: downloads from a host phone to this PC ran at about 5 MB/s in any browser and in curl.
**Cause.** Outside the app and the core: the same phone sends to another phone at about 47 MB/s, and the PC receives from the internet at about 52 MB/s. Not the app or the core's send loop; do not chase it in `DropZone.py`.
**Evidence.** Host logs and Gabe's speed tests, LOG 2026-11-13. The working note that held the measurements was deleted by Gabe on 2026-11-16 once he had what he needed; the LOG entries remain.

## Diagnosis and communication (DropCast session, 2026-11-13)
### L6 Naming a cause from one comparison #cross-project
**What was tried.** After the host's phone sent a file to the guest's phone at about 47 MB/s and to the PC at about 5 MB/s, the agent reported "the slow leg is the PC's WiFi reception".
**Why it failed.** Only one side of the slow pair had been compared. The PC had never been measured receiving from anything else; Gabe's speed tests then showed it receiving about 52 MB/s from the internet. The evidence supported "this phone to this PC is slow", nothing wider.
**Evidence.** LOG 2026-11-13, the RETRACTION line; `LESSONS_LEARNED.md` > L10.
**Guardrail.** Before naming a device as the cause, measure that device against a second partner. Until then, state the finding as the pair that is slow.

### L7 Questions that could be read two ways #cross-project
**What was tried.** Questions and option labels put to Gabe used "Keep it", "the phone", "as before", and two adjacent questions that read as contradicting each other.
**Why it failed.** Each needed a second round to untangle, four times in one session, on decisions that needed his full attention.
**Evidence.** LOG 2026-11-13: the photo-location decision, the Stop warning questions, the known-limit note, the QR check.
**Guardrail.** In anything put to the user, name every device and person by role each time, say what an option changes and what it leaves, and replace bare time words ("before", "still", "again") with the event meant.
