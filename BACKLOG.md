# DropZone — Backlog

Work top to bottom. One item per session. Finish and verify an item before
starting the next. See `docs/DEVELOPMENT.md` for the workflow.

Status keys: `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` dropped

Priority tiers:
- **P0** — broken or data-losing; blocks normal use.
- **P1** — high-value fix or foundation the rest builds on.
- **P2** — worthwhile improvement.
- **P3** — nice to have / larger effort, do once the core is stable.

---

## P0 — Fix first

### 1. [x] Upload freezes near completion on large files  (BUG)  — closed, field-confirmed v0.2.09
The freeze that makes big uploads unusable. Symptoms from the field:
- Uploads run fast, then freeze at ~80–90% and never finish.
- Even a single large file freezes at ~80%.
- Rough ceiling observed near 1.8 GB; not exhaustively tested.
- After freeze, F5 shows the file in the list but with a cut-off (partial) size.
- Host is a phone in Termux; ~1 GB per user, 2 users, ~70 GB free on the phone.

Prime suspect (to confirm, not assume): the server reads the **entire** upload
body into RAM in one call — `body = self.rfile.read(length)` in `do_POST`, then
`parse_multipart` splits that blob, making more full-size copies. On a phone,
a ~1.8 GB upload can exhaust memory and the process stalls or the socket dies
mid-read, which matches the "size cut" on refresh. The `BrokenPipeError` in the
saved log is on the *download* path, so it is a separate concern (see item 6).

First session's job is investigation + splitting, not a forced fix:
- Instrument first (low risk): log request Content-Length, bytes read, and
  peak memory around the upload; and silence the benign download-side
  `BrokenPipeError` (item 6) so the terminal shows only signal. Confirm
  behaviour, then fix.
- Reproduce and confirm the memory theory (watch RSS while uploading a big file).
- Decide the fix direction: stream the request body to disk in bounded chunks
  and parse multipart incrementally, so peak memory stays flat regardless of
  file size. Consider a real per-file streaming upload from the client.
- Split into concrete sub-tasks once the direction is set.

**Definition of done:** a single ~2 GB file and a multi-file ~1 GB-per-user
upload both complete on the phone host without freezing; server memory stays
bounded during the transfer; the uploaded size on the list matches the real
file size. Preserve the raw log at `docs/notes/upload-freeze-log.md`.

**Progress (v0.2.02):** instrumentation shipped — the upload path now logs
Content-Length, bytes read, part count, and RSS at each stage; benign
download-side broken pipes are silenced so the terminal shows only signal.
**Progress (v0.2.05):** cause CONFIRMED from the v0.2.04 field log — RSS tracked
upload size, and the 700 MB and 3.5 GB uploads were OOM-killed (see
docs/notes/upload-freeze-log.md). Streaming fix shipped: `stream_multipart()`
parses the body from the socket in `UPLOAD_CHUNK` (4 MB) blocks and writes
each file straight to disk; `do_POST` no longer reads the whole body. Verified in the container — a
1.2 GB upload peaked at ~23 MB server RSS and all files saved byte-exact
(size + sha256).
**Closed (2026-08-30, field, v0.2.09):** DoD met on the phone. Single files of
2.4 GB, 2.6 GB and 1.8 GB, plus a 4.4 GB two-file batch, all uploaded byte-exact
with server RSS flat at 12-16 MB (memory did not track file size). No freeze, no
OOM, no traceback. Separately, a battery-saver client (device .94) reset mid-
upload 3x — logged cleanly as ConnectionResetError, 0 files, RSS low, no
traceback (robustness holds); it completed once the browser was excluded from
Android battery optimisation. Raw evidence in `DropZone.log`.

---

## P1 — High value / foundations

### 2. [ ] Test: does remote-user file deletion actually remove the file?  (TEST)
Confirm whether a guest deleting an uploaded file removes it from the server, or
whether the file persists on disk. Code path to check: `POST /api/remove_file`
unlinks the temp file only when `owner_id == sid`. Verify a remote guest's
delete both drops the list entry and unlinks the temp file; check for orphans
left in the temp folder.

**Definition of done:** a written finding in `docs/notes/` stating observed
behavior; if broken, a new backlog item with the fix.

### 3. [x] Versioning: single version constant + show it on the host page  (IMPROVEMENT)  — shipped v0.2.01
Add one `__version__` constant to DropZone.py and display it on the host page,
including the release channel (nightly / beta / stable) per the scheme in
`docs/DEVELOPMENT.md`. Doing this early means every later change bumps the
version and updates CHANGELOG.md as it ships.

**Definition of done:** host page shows the version and channel; CHANGELOG.md
and the constant agree. (Deploy note: the phone copies the latest build onto `DropZone.py`; the
version constant, not the filename, identifies the running build.)

### 4. [ ] Host view: panel of all connected users + status  (IMPROVEMENT)
Today a user only appears once they upload a file — `/api/state` filters with
`if u["files"]`. The host wants to see everyone connected and useful
troubleshooting info: who is present, whether they are active, current activity
(e.g. uploading / downloading), and other diagnostics. This also helps debug
items 1 and 6.

**Definition of done:** host page lists connected sessions even with no files,
showing name and a live activity/status indicator; guests are unaffected.

---

## P2 — Improvements & fixes

### 5. [-] Bug: long combined file list cannot scroll to the bottom  (BUG)  — dropped, not reproducible
With many files uploaded by several people, the page stops short and the bottom
of the list is cut off; you cannot reach the end. Likely a CSS height/overflow
constraint on a container (investigate the `.card`, `.main`, and list wrappers
in the CSS block). Small, high-annoyance win.

**Definition of done:** with a long multi-user list, the whole list scrolls into
view on both phone and desktop widths.

**Dropped (2026-08-30):** re-tested with 1100 uploaded files — all are listed and
the list scrolls to the bottom. No defect. Reopen only with a concrete repro
(file count, browser/width, screenshot of the cut-off).

### 6. [~] Bug: no feedback (and possibly no service) when a download is queued  (BUG)
A second user clicking download while someone else pulls a ZIP sees nothing —
no start, no error, no position. Two things to address:
- Feedback: if the transfer is waiting on a slot (`MAX_CONCURRENT_TRANSFERS`,
  the `transfer_sem`), show the user they are queued and roughly where.
- Robustness: a big ZIP is spooled entirely to a temp file *before* the first
  byte is sent, so the client looks frozen while it builds; and a client that
  cancels mid-download raises an unhandled `BrokenPipeError` (see saved log),
  which spams the console. Handle the broken pipe cleanly and consider sending
  ZIP headers/bytes sooner.

**Definition of done:** a queued download shows clear waiting feedback; a
cancelled download does not print a traceback; two users can request downloads
without one silently getting nothing.

**Progress (v0.2.02–0.2.03):** cancelled downloads no longer print a traceback;
the terminal now logs the full download/zip lifecycle. Remaining: user-facing
(in-browser) "you are queued / position N" feedback.
**Field evidence (v0.2.06 — 3 devices, 3 simultaneous 1 GB+ zips):** all three
archives completed and every cancel was logged cleanly (no unhandled traceback —
the broken-pipe handling holds up under load). The "no feedback" delay is the
silent spool-to-disk phase, NOT the semaphore: `MAX_CONCURRENT_TRANSFERS=4`, so
the three zips ran concurrently, but each is built entirely to a temp file before
the first byte is sent (~15 s of silence for a 1 GB archive; three at once means
~4 GB of temp zips and disk contention). During that window the browser has an
open request with no response, so it shows nothing.
**Plan (simple, low risk):** track active transfers — phase (queued/building/
sending), owner sid, name, size — in shared state and include them in `/api/state`,
which every page already polls each second. Waiting devices then get an ambient
"host is building N archives / sending M" line, the requester sees its own
archive's phase, and if the semaphore ever queues (5+ heavy transfers) it shows a
position. Feedback rides the independent poll, so it works even while a device's
own download request is blocked.
**Shipped (v0.2.07):** the activity banner and /api/state "transfers" list are
live — queued/preparing/sending with a queue position. The "deeper" streaming
plan is split out as item 13. Remaining here: nothing further unless the
banner needs polish from field use.
**Plan (deeper, optional):** stream the STORE zip as it is built (headers +
bytes) instead of spooling the whole thing first, so the browser starts receiving
immediately and shows native download progress — removes the spool wait itself.

---

## P3 — Larger features & cleanup

### 7. [ ] Thumbnails toggle + thumbnail selection view  (IMPROVEMENT)
Opt-in thumbnails so users can pick files visually, defaulting OFF so people who
want speed keep fast icons. Open questions to resolve during design:
- Toggle in the UI; off by default.
- A thumbnail view screen that allows custom multi-select of files.
- Whether thumbnails come from file metadata vs. being generated, and how much
  generation latency is acceptable. Measure before committing to generation.

**Definition of done:** a working toggle; with it on, an image grid allows
multi-select; performance impact measured and documented; off by default.

### 8. [ ] Code audit for simplicity and maintainability  (IMPROVEMENT)
A deliberate pass to keep the code simple, straightforward, and easy to develop.
Do this **after** the bug fixes above land, so we audit stable code rather than
code about to be rewritten. Keep the single-file, zero-dependency shape.

**Definition of done:** a short findings note listing concrete simplifications;
low-risk ones applied; anything larger split into its own backlog item.

---

## P1/P2 — from field notes (2026-08-27)

### 9. [x] Real upload progress bar — replace the fake timer  (BUG/UX)  — shipped v0.2.05
The current bar is a `setInterval` that creeps to ~82% then jumps to 100% on
response; it is not tied to real bytes sent, so it is deceiving. Use an
XMLHttpRequest with `upload.onprogress` (fetch cannot report upload progress) to
show true bytes-sent. Pairs with BACKLOG item 1: a real bar also shows exactly
where a large upload stalls.
**Definition of done:** the bar tracks actual bytes sent; on a stalled upload it
visibly stops at the real point rather than sitting near 100%.
**Done (v0.2.05):** client uploads via XMLHttpRequest and drives the bar from
`upload.onprogress` (true bytes sent, with bytes + ETA). Field note: confirm on
the phone that it visibly halts at the stall point during a large upload.

### 10. [~] Investigate duplicate / double downloads  (BUG)  — fix shipped v0.2.10, awaiting iPhone field confirm
Field report: selecting each file once still produced many OS-suffixed
duplicates ("name (1).ext") in the download folder. Two candidate causes: (a) a
real double-fire — the same request sent twice; or (b) not a bug — distinct
same-named files from different users colliding in the Downloads folder, so the
OS adds a suffix. The new per-download `[id]` logging (v0.2.03) distinguishes
them: repeat the test and read the terminal — the same id twice means (a);
different ids with the same name means (b), which argues for namespacing
single-file downloads by user or offering a per-user zip.
**Update (v0.2.09):** the spool delay that made people re-click bulk downloads
is gone (zips now stream instantly), which should remove the biggest source of
accidental duplicate downloads. Re-test to see what, if anything, remains.
**Field evidence (2026-08-30, v0.2.09):** the re-fire is REAL and client-side —
individual downloads logged the same `[id]` three times (request, cancel, cancel,
done). On gigabyte files the two superseded requests are cancelled before they
commit a file, so NO `(1)` duplicate appeared (confirmed: no dupes on the big-
file downloads). The duplicate symptom is a race that only shows on SMALL files:
there each fire completes before the next cancel, so 2-3 completions write
`name.ext`, `name (1).ext`, `name (2).ext`. One download (The Insult) fired only
once, so the re-fire is browser/timing-dependent, not universal. Prime suspect:
the hidden download anchor is clicked more than once (possibly re-triggered by
the activity-panel re-render or the 1 s `/api/state` poll).
**Still to reproduce:** download several SMALL individual files (a few MB each),
one click each, and confirm from the log (same `[id]` with multiple `download
done`) + the Downloads folder (`(1)` files). The fix — debounce/guard the anchor
so one click = one request — is the same regardless and can proceed on the
evidence already logged.
**Field evidence (2026-08-30, v0.2.09):** the re-fire is REAL and client-side —
individual downloads logged the same `[id]` three times (request, cancel, cancel,
done). On gigabyte files the two superseded requests are cancelled before they
commit a file, so NO `(1)` duplicate appeared (confirmed: no dupes on the big-
file downloads). The duplicate symptom is a race that only shows on SMALL files:
there each fire completes before the next cancel, so 2-3 completions write
`name.ext`, `name (1).ext`, `name (2).ext`. One download fired only once, so the
re-fire is browser/timing-dependent, not universal. Prime suspect: the hidden
download anchor is clicked more than once (possibly re-triggered by the activity-
panel re-render or the 1 s `/api/state` poll).
**Still to reproduce:** download several SMALL individual files (a few MB each),
one click each, and confirm from the log (same `[id]` with multiple `download
done`) + the Downloads folder (`(1)` files). The fix — debounce/guard the anchor
so one click = one request — is the same regardless and can proceed on the
evidence already logged.
**Cause + fix (v0.2.10):** identified as iOS Safari probing the download with a
Range request and re-fetching because `/api/download` only ever replied `200`
(no `Accept-Ranges`/`206`), so the probe and the save became two files (`name
(1).ext`). Android takes the single `200` cleanly — hence Android-to-Android
never reproduced it. Fix: single-file downloads now speak HTTP Range (206 +
`Content-Range`, `Accept-Ranges`/`ETag`/`Last-Modified`, `If-Range`, `416` past
EOF); see docs/commits/0012 and tests/test_download_range.py. Zips unchanged.
**Field confirm still owed:** on an iPhone, download several small files
individually (one tap each) and check they land once each — no `(1)` copies.
Separately, the Android triple-fire (same `[id]` 3x ~ the 1 s poll) is a distinct
lower-priority client issue (list re-render churns the anchor); not fixed here.
**Definition of done:** cause identified from logs; fix or a clear "working as
intended, here is the better UX" decision recorded.

### 11. [ ] Split "Download everything" into size-capped parts  (IMPROVEMENT)
One giant archive is unwieldy. Break it into multiple volumes up to a sane max
size (e.g. a `MAX_ARCHIVE_BYTES` constant), packing whole files into each part
without splitting a single file across parts. Now that archives STORE (no
compression, v0.2.03), the packed size is predictable, which makes sizing exact.
**Definition of done:** a large "everything" download yields several parts each
at/under the cap, each a valid zip; the UI lists the parts.

### 12. [-] Light/dark theme regression  (BUG, P2)  — dropped, external cause
Field report (v0.2.06): light/dark theme modes are misbehaving. The theme code —
the `:root` / `[data-theme]` CSS variables (~L491), the
`@media(prefers-color-scheme:dark)` fallback (~L508), and `initTheme()` (~L952,
which sets the OS default on load and wires the toggle) — was **not** touched by
the v0.2.05/06 work (that was the upload path, the `UPLOAD_CHUNK` constant, and
the version string), and it reads byte-identical in the `bak2` (pre-08-27) and
`bak3` (pre-4 MB) backups. So the cause is not the streaming change; it needs
pinning. To capture on repro: which page (host vs remote), the OS theme setting,
and whether it is the initial load or the toggle click that misbehaves.
**Definition of done:** on both the host and remote pages, the page follows the
OS light/dark setting on load and the toggle flips it; the regression's cause is
identified and fixed, with a one-line note on what it was.
**Investigation (2026-08-30, headless Chromium against v0.2.09):** the two
themes ARE distinct and the toggle works. Measured body colours: dark = bg
luminance 22 / text 207; light = bg 243 / text 37. On a dark OS one click flips
to genuinely light (bg 243) and back; the toggle button is visible and within
the viewport at desktop (900px) and mobile (380px) widths. So there is no theme
defect in the code — neither state 'falls through' to the OS default. Whatever
was seen is device/browser specific; NEEDS a concrete repro (screenshot of the
bad state, which browser/OS, and exactly what is wrong). One true behavioural
note: the OS theme is read only on load — there is no matchMedia change listener,
so flipping the OS theme while the page is open does not live-update (and, per
Gabe, cross-session persistence is intentionally not wanted).
**Dropped (2026-08-30):** root cause found — it was a browser setting forcing
night mode on the device, overriding the page. Not a DropZone bug; the code is
correct (see investigation above). Reopen only if the issue recurs with that
browser setting off.

### 13. [x] Stream the "download everything"/zip as it is built  (IMPROVEMENT)  — shipped v0.2.09
Replace spool-whole-then-send with streaming the STORE archive straight to the
socket, removing the silent spool delay and the temp-file disk cost. Investigated
2026-08-30 (docs/notes/streaming-zip-findings.md): feasible, data descriptors are
fine, and the exact archive size is computable in advance so the real progress
bar is preserved — but the length calculator MUST branch on the 4 GiB zip64
thresholds (per file and whole archive). Recommend a hand-rolled STORE streamer
so one code path owns both layout and length.
**Definition of done:** a large "everything" download starts sending immediately
(no spool wait), uses no temp file, shows a real browser progress bar, and the
archive opens correctly on Windows, macOS, and Android — including a case that
crosses the 4 GiB zip64 boundary.

### 14. [ ] Unify upload progress + host activity into one status area  (IMPROVEMENT, P3)
Field feedback: the host-activity list and the upload progress bar are separate
and in different places. Consider one persistent status area that shows both
your own upload progress and the host's live download/queue activity, so there
is a single place to watch. v0.2.08 made the activity a floating always-visible
panel (out of flow, no page jump) as an interim; this item is the fuller merge
if wanted.
**Definition of done:** one status region shows in-flight uploads (real bytes,
pairs with item 9) and host download/queue activity; no page-content jump as it
updates; reachable without scrolling on phone and desktop widths.

## Notes on ordering
Item 1 is fixed first by explicit request and because it makes the app unusable
for its core purpose. Items 2–4 are small and build foundations (a correctness
check, versioning discipline, and a host view that also aids debugging). Items
5–6 are the remaining bugs. Items 7–8 are the larger feature and the cleanup
pass, saved for when the core is stable. Re-order freely as priorities shift —
this file is the source of truth.
