Fix host-page navigation on bulk download; float the activity panel (v0.2.08)

Two field-reported issues from the v0.2.07 run.

1. Host page went blank and duplicated downloads. Clicking a bulk ZIP
   ("All N files" / "Download everything") navigated the whole page to the
   download URL: for large archives confirmBulk() did `window.location.href=url`,
   and the smaller-archive path let the plain anchor (no `download` attribute)
   navigate. Because the ZIP spools to disk before the first byte, the page sat
   blank at /api/download_all for ~15-25 s; a confused refresh re-fired the whole
   request. The log shows one host archive requested+spooled+cancelled eight
   times before completing.
   Fix: downloads never navigate the page now. New triggerDownload() creates a
   hidden `download` anchor and clicks it (same mechanism the single-file links
   already used), so the archive downloads in the background and the page is
   untouched; a refresh no longer re-fires it. confirmBulk() always
   preventDefault()s and routes through it; the size confirm still gates large
   ones. Added `download` to both ZIP anchors as a no-JS fallback.

2. Activity panel placement/jitter. The host-activity list sat at the top of the
   page (scroll up to see it) and, being in normal flow, pushed content up/down
   as transfer rows came and went. It's now a floating panel pinned to the bottom
   centre, out of normal flow: always visible without scrolling, and its
   show/hide/updates never shift page content. Capped height with internal scroll
   for many transfers; empty => invisible.

Not changed: the server. Verified JS syntax (node --check), that confirmBulk no
longer navigates, and re-ran the queue-feedback server test (one sending, two
queued #1/#2, drains clean). On-device behaviour (no blank page, no duplicate on
refresh) to be confirmed in the field.
