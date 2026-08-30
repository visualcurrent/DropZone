Add live transfer activity feedback (v0.2.07)

Give every page ambient visibility of what the host is doing during downloads,
so waiting devices are no longer left with a silent, unresponsive-looking delay
(BACKLOG 6, feedback half).

Key idea: feedback rides the existing /api/state poll (every 2.5 s), which is a
separate request from the blocked download — so a device sees progress even
while its own download request is waiting for a transfer slot.

Server:
- A small in-memory transfer registry (transfers / transfers_lock). Each heavy
  download or zip calls transfer_start() before acquiring transfer_sem (phase
  "queued"), transfer_set() to "building" after acquiring it and "sending" once
  bytes start, and transfer_end() in a finally.
- Wired into stream_zip (download_all / download_everything) and the streamed
  single-file /api/download path.
- /api/state now returns a "transfers" list: name, size, phase, owner name,
  whether it is the viewer's own, and a queue position for queued transfers.

Client:
- New renderActivity(): an ambient "Host activity" banner listing each in-flight
  transfer with an icon, size, phase, and (when queued) "#N of M". The viewer's
  own transfers are emphasised. Fed from the poll; hidden when nothing is
  running. Added an #activity slot to the shared page shell (both pages).
- startPolling() now paints immediately, then every 2.5 s.

Not included (recorded as BACKLOG 13): streaming the zip as it is built to remove
the spool delay itself. Investigation and decision in
docs/notes/streaming-zip-findings.md.

Verified in the container: with the semaphore forced to 1 and three concurrent
downloads, /api/state correctly reported one "sending" and two "queued" with
positions #1/#2, the owner/"mine" flag was right, and the registry drained to
zero on completion. Upload path re-tested unchanged (1.2 GB, ~30 MB RSS, exact).
