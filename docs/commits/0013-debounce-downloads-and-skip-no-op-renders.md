Debounce downloads + skip no-op re-renders — fix the Android re-fire (v0.2.11)

Follow-up to the v0.2.10 Range fix. That closed the iOS-Safari duplicate; this
closes the *other* re-fire seen in the field log — same `[id]` fired ~3× within a
second, two cancelled, on Android Chrome and localhost.

Cause (client): the single-file download button was a bare navigating anchor
`<a class="dl-btn" href=".../api/download?id=.." download>`. Its DOM node lives in
the network file list, which the `/api/state` poll rebuilds wholesale every 2.5 s
via `innerHTML`. When a download was still in its initial (pre-download-manager)
phase and the poll destroyed the anchor, the browser aborted the request and a
retry fired — the ~2.5 s cancel cadence in the log matches the poll interval.

Fix (client-only; server download path untouched):
- `triggerDownload(url)` now (a) debounces by URL — a repeat of the same download
  within DL_DEBOUNCE_MS (1500 ms) is dropped, so a re-tap or a churn-retry can't
  double-fire; and (b) is documented as the single path that appends a detached,
  self-removing `<a>` to `<body>` — never to the polled list — so a re-render
  cannot abort an in-flight download.
- New `downloadOne(ev, id)`: the single-file button now calls it, `preventDefault`s
  the anchor's own navigation, and routes through `triggerDownload`. The `href`
  stays as a no-JS fallback; the server's `Content-Disposition` still supplies the
  filename. Bulk downloads already went through `triggerDownload`, so they inherit
  the debounce too.
- `renderMyFiles` / `renderAllUsers` skip the `innerHTML` rebuild when their input
  is byte-identical to the last render (JSON signature), so buttons stop churning
  under an in-flight click. The activity banner (`renderActivity`) still updates
  every poll.

Not automatable here: the test harness drives raw sockets, not a browser, so this
client-JS behaviour has no unit test. Verified instead by: `node --check` on the
embedded JS (JS / HOST_INIT / REMOTE_INIT all parse), the full server suite still
green (server path unchanged), and a boot smoke confirming the served page carries
`downloadOne`, `DL_DEBOUNCE_MS`, the button `onclick`, and the render-skip guards.
Field confirm on Android: one tap should log a single `download [id]` with no
cancel/re-request storm.
