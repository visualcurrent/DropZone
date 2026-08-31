# Audit / cleanup guide — download & upload paths

Written 2026-08-30, right after the BACKLOG 10 work, while the context is fresh.
Purpose: when we do the code audit (BACKLOG 8), this says what is **load-bearing
and must stay**, what is **safe to scrutinize / likely removable**, and which
**non-obvious choices must NOT be "simplified" away** (each one is a scar from a
real field bug). Read this before touching `/api/download`, `send_html`, or the
client download/upload JS.

The download path churned through v0.2.10 -> v0.2.14 (five builds, one full
reversion) chasing BACKLOG 10 (duplicate downloads). The **net keeper is
v0.2.14**. Commit notes `docs/commits/0012`-`0016` are the blow-by-blow;
`0016` is the authoritative explanation of the final behavior.

---

## Invariants — DO NOT break these during cleanup

These three are counter-intuitive and each fixes a specific field bug. A well-
meaning "cleanup" that reverts any of them **re-opens a closed bug**:

1. **`/api/download` must NOT advertise `Accept-Ranges` on its 200/206 responses.**
   It looks like a missing header — it is deliberate. Advertising it makes Chrome
   start/cancel/re-segment a download, which duplicated small files (`name (1).ext`).
   Removed in v0.2.14. (The 416 branch keeps its own `Accept-Ranges`; that path is
   range-specific and rarely hit — harmless.)

2. **`send_html` must stay `Cache-Control: no-store`.** The page inlines all
   CSS/JS, so without this browsers pin an OLD client across deploys. This is why
   v0.2.11's client fix "didn't work" until v0.2.12 — the phone ran a cached page.
   Removing no-store means client-side changes silently stop reaching users.

3. **If we keep Range support, keep the whole apparatus but never advertise it.**
   The 206 handler (`parse_range`, `Content-Range`, `If-Range`, `416`) exists for
   iOS Safari's probe and for resume. It is only reached when a client sends an
   explicit `Range:` header. Keep it *or* remove it wholesale (see decision below)
   — do not half-remove it.

---

## Download path — keep vs. scrutinize

### KEEP (load-bearing)
- **Server, no `Accept-Ranges` advertisement** — invariant #1.
- **Server, `no-store` on `send_html`** — invariant #2.
- **Client, native `triggerDownload`** (detached, self-removing `<a>` on `<body>`,
  not the polled list) — gives the instant browser download UI and survives the
  list re-render.
- **Client, 1.5 s per-URL debounce (`_dlLast` / `DL_DEBOUNCE_MS`)** — guards an
  accidental rapid double-tap. Cheap; keep.
- **Client, render-skip in `renderMyFiles` / `renderAllUsers`** (JSON-signature
  compare) — stops the 2.5 s poll churning download buttons under a click.
- **`test_download_range.py`** — locks the v0.2.14 decision (200 omits
  `Accept-Ranges`; an explicit `Range` still returns 206). Keep it honest.

### SCRUTINIZE (decide during the audit)
- **The entire Range apparatus** (`parse_range`, the 206/416 branch, `ETag`,
  `Last-Modified`, `If-Range`) exists ONLY for iOS Safari + resume.
  **Decision point:** do we still need to support Safari download quirks / resume?
  - If YES -> keep it all, keep NOT advertising (status quo). Leave as is.
  - If NO -> remove `parse_range`, the 206/416 branches, `ETag`/`Last-Modified`/
    `If-Range`, and serve a plain 200 always. That deletes a lot of surface.
  This is the single biggest simplification available in the download path. It was
  kept in v0.2.14 because we have not been able to test iPhone; revisit once we can.
- **`ETag` / `Last-Modified` on `/api/download`** — only meaningful with the Range/
  If-Range story. If Range is dropped, drop these too.
- **`STREAM_THRESHOLD` buffered-vs-streamed split in `/api/download`** — still
  valid (small = one buffered write, large = streamed slice under the transfer
  registry). Not suspect, just verify it still earns its keep after any Range
  decision.

### REMOVED — do not resurrect
- **Blob / in-page download** (`blobSave`, `cdFilename`, `startDownload`,
  `BLOB_DL_MAX`). Shipped in v0.2.13, reverted in v0.2.14. It DID dedup (one fetch
  = one file) but buffered the whole file with no feedback and stacked save
  dialogs — unacceptable UX. If someone proposes "just fetch it in JS," this is why
  we don't.

---

## Upload path — NOT part of the download saga

`uploadFiles` (client) and `stream_multipart` / `do_POST` (server) were untouched
by v0.2.10-v0.2.14. The streaming-upload memory fix (BACKLOG 1) is solid and
field-confirmed — leave it alone.

**Known gap (logged as BACKLOG 15, found 2026-08-30):** uploads have no guard
against a duplicate/concurrent submit, a single shared progress bar that bounces
when two run at once, and no "upload started" feedback before the first
`upload.onprogress` event (bad on slow/public wifi — user thinks it's dead and
re-submits, creating a same-named duplicate with a different id). This is a UX gap,
NOT a regression from the download work. Fix belongs to its own item.

---

## Housekeeping to clear during the audit
- `docs/notes/DropZone.py.bak4` ... `bak8` — pre-change backups from this saga.
  Delete once the audit is done and committed.
- `tests/__pycache__/` — should be gitignored, not committed.
- CHANGELOG `[0.2.10]`-`[0.2.14]` all target BACKLOG 10; the audit may add a short
  "net effect" note, but keep the per-version entries — they explain the scars.
- Commit notes `0012`-`0015` describe superseded/reverted approaches; keep for
  history but treat `0016` as the current-behavior source of truth.

## One-line summary for the impatient
Downloads are plain native `200`s on purpose (no `Accept-Ranges`), the page is
`no-store` on purpose, and the Range/blob machinery is either kept-but-silent
(Range) or deliberately gone (blob). The biggest available simplification is
deleting Range support IF we decide Safari/resume don't matter.
