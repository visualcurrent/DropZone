No-store the app shell so clients stop running a cached old UI (v0.2.12)

The v0.2.11 field log (DropZone.log) showed the Android download re-fire was NOT
fixed — the zip re-fire storm (same URL requested ~3x, two cancels) was unchanged.
But the same log showed `206 Partial Content` range replies, which only the
v0.2.11 *server* can send. Conclusion: the server was updated, the CLIENT was not
— the browser was executing a cached copy of the pre-0.2.11 page, so the new
`downloadOne`/debounce/render-skip JS never ran.

Cause: `send_html()` sent the HTML app shell with no cache headers. Because the
page embeds all CSS/JS inline, a cached page silently pins an old client across
deploys.

Fix: `send_html()` now sends `Cache-Control: no-store, no-cache, must-revalidate`,
`Pragma: no-cache`, `Expires: 0`. The shell is tiny and LAN-served, so refetching
it every load is free, and client-side changes now take effect immediately. No
change to any download/upload/zip path.

Note for readers of the log going forward: now that the server advertises
`Accept-Ranges` (v0.2.10), a browser's download manager may split ONE single-file
download into several parallel `206` range requests (e.g. three even thirds).
That is normal segmented downloading and assembles into a single saved file —
multiple `download [id]` *range* lines for one file are expected and are not a
duplicate. A duplicate would be multiple FULL (200) completions of the same file.

Verified: boot smoke confirms `GET /` now carries `Cache-Control: no-store` and
still serves the v0.2.12 client (`downloadOne`, `DL_DEBOUNCE_MS`); full server
suite green.

Field step (Android): load the page once on a fresh cache — clear the site's data
or append a throwaway query like `?v=12` to the URL — to get past the currently
cached old page (after that, no-store keeps it current automatically). Then a
single tap should log one logical download and the zip button one request.
