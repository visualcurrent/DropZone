Store (not compress) zips and log the download lifecycle (v0.2.03)

From field notes on 2026-08-27. Addresses "the zip should only wrap, not
compress" and "the terminal says nothing after I press download".

- stream_zip now uses ZIP_STORED instead of ZIP_DEFLATED for both the in-RAM and
  spooled-to-disk paths. Files are usually already compressed; storing is much
  faster on a phone host and makes the archive size predictable (which also sets
  up size-capped splitting, BACKLOG 11).
- Add lifecycle logging: single-file downloads log name, file id, size, and
  destination, plus a done/cancelled line; zip downloads log
  requested/building/sending/done/cancelled. The per-file id makes a real
  double-fire distinguishable from same-named files colliding on save
  (BACKLOG 10).
- Bump __version__ to 0.2.03 (nightly).
