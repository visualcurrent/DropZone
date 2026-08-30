Add a dependency-free test suite in tests/

Preserve the regression checks written during the v0.2.05–0.2.09 work as a real
safety net (they had been living in throwaway scratch). No framework, standard
library only, matching the project's zero-dependency rule.

- tests/_dz_harness.py — copies DropZone.py with only PORT (and optionally
  MAX_CONCURRENT_TRANSFERS) patched, launches it on a high port, and drives it
  over raw sockets. Tests never touch a running instance and always exercise the
  current DropZone.py.
- tests/test_upload_memory.py (item 1) — uploads save byte-exact and peak memory
  stays flat regardless of size.
- tests/test_queue_feedback.py (item 6) — /api/state reports sending/queued with
  positions and drains to empty.
- tests/test_zip_streaming.py (item 13) — streamed ZIP: Content-Length == bytes
  == zip_stream_size(), instant first byte, valid archive (python + unzip),
  byte-exact extraction, clean mid-stream cancel.
- tests/run_all.py runs all three; tests/README.md explains usage and how a
  future agent extends them.
- DEVELOPMENT.md's Verify step and living-docs list now point at tests/.

No application code changed; no version bump.
