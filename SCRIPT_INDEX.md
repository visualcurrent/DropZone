# SCRIPT_INDEX — DropZone

Per-file map so `DropZone.py` (~1450 lines, single file) need not be re-read wholesale. Extend, never restart. Line numbers are approximate (v0.2.15).

| File | Purpose | Key functions / anchors | Run |
|---|---|---|---|
| `DropZone.py` | The whole app: HTTP server, upload, download, bulk zip, embedded UI. | see the map below | `python3 DropZone.py` |
| `tests/run_all.py` | Runs all five tests; fails if any fails. | — | `python3 tests/run_all.py` |
| `tests/test_download_filename.py` | BACKLOG 16: `/api/download` of names outside plain ASCII — 200, byte-exact, quoted `filename=""` is ASCII, `filename*` decodes to the original. Reuses the helpers in `test_download_range.py`; port 8075. | — | `python3 tests/test_download_filename.py` |
| `tests/_dz_harness.py` | Copies `../DropZone.py` to a temp file with only `PORT` (and where needed `MAX_CONCURRENT_TRANSFERS`) patched, launches on ports 8071–8073, drives it over raw sockets. Never touches a running instance. | — | (imported by tests) |
| `tests/test_upload_memory.py` | BACKLOG 1: small/multi/800 MB uploads save byte-exact (size + sha256) and peak RSS stays flat. Linux/Termux only (reads `/proc/<pid>/status`). | — | `python3 tests/test_upload_memory.py` |
| `tests/test_queue_feedback.py` | BACKLOG 6: transfer cap forced to 1 → three downloads show one `sending` + others `queued` with positions in `/api/state`; registry drains. | — | `python3 tests/test_queue_feedback.py` |
| `tests/test_zip_streaming.py` | BACKLOG 13: advertised `Content-Length` == bytes streamed == `zip_stream_size()`; first byte near-instant; archive valid + byte-exact; clean mid-stream cancel. | — | `python3 tests/test_zip_streaming.py` |
| `tests/test_download_range.py` | BACKLOG 10: `/api/download` Range behaviour — 200 omits `Accept-Ranges`, an explicit `Range` returns 206 with the right `Content-Range`, past-EOF is 416, stale `If-Range`/multi-range fall back to 200. | `python3 tests/test_download_range.py` |
| `android/build.bat` | Builds the sideloadable APK with the portable toolchain in `D:\AndroidToolchain`; writes `android/DropZone-debug.apk`. Windows only. | — | `android\build.bat` |
| `android/app/build.gradle` | App build settings: copies `../../DropZone.py` into `app/src/main/python/` (generated, git-ignored), reads its `__version__` into the APK version name, sets wrapper version, SDK levels, ABIs, Python 3.13. | `coreSrc`/`coreDst`, `wrapperVersion` | (via `build.bat`) |
| `android/app/src/main/python/dz_host.py` | Starts/stops the unedited core inside the app. Depends on these core names: `LOG_FILE`, `UPLOAD_DIR`, `LOCAL_IP`, `get_local_ip`, `make_server`, `log`, `state_lock`, `shared_files`, `users`, `PORT`, `__version__`, `VERSION_STAGE`. | `start(files_dir)` -> `[remote_url, core_version]`, `stop()` | (called from `ServerService`) |
| `android/app/src/main/java/com/visualcurrent/dropzone/ServerService.java` | Foreground service (type `connectedDevice`) that runs `dz_host`; holds CPU + WiFi locks; publishes `running` / `remoteUrl` / `coreVersion` / `lastError`. | `onStartCommand`, `onDestroy` | — |
| `android/app/src/main/java/com/visualcurrent/dropzone/MainActivity.java` | The one screen: Start/Stop, remote address, "Open host page" (launches the browser at `http://localhost:7070`). | `refresh()` | — |

## DropZone.py map (by anchor, not full read)
- Config constants (~L18–42): `UPLOAD_DIR`, `PORT=7070`, `__version__="0.2.15"`, `VERSION_STAGE="nightly"`, `STREAM_THRESHOLD` (64 MB), `UPLOAD_CHUNK` (4 MB), `WARN_THRESHOLD` (512 MB), `MAX_CONCURRENT_TRANSFERS` (4), `SPEEDTEST_BYTES`, `THREADED`.
- Transfer registry (~L47–68): `transfer_start` / `transfer_set` / `transfer_end` / `transfers_public`, `transfer_sem`.
- Logging (~L83–115): `DEBUG`, `LOG_FILE` (`DropZone.log`, rolls at 5 MB), `log`, `rss_mb`, `get_local_ip`, `LOCAL_IP`.
- Helpers (~L117–190): `gen_name`, `fmt_size`, `parse_range` (L125), `get_or_create_user`, `user_display`, `dedup_name`, `parse_multipart`.
- Upload streaming (~L212–296): `stream_multipart` (socket → disk in `UPLOAD_CHUNK`; `fill`/`read_line`/`stream_body`), `get_filename`.
- Zip streamer (~L312–366): `zip_stream_size` (exact length), `_dos_dt`, `zip_stream` (uniform-zip64 STORE).
- `Handler` (~L368–707): `send_json`, `send_html` (L380, `no-store`), `get_session`, `do_OPTIONS`, `_zip_headers`, `stream_zip` (L418), `do_GET` (L452; `/api/download` L482, its `Content-Disposition` built at L494–501), `do_POST` (L615).
- Embedded UI (~L708–1437): `CSS`, `JS`, `LOGO_SVG`/`MOON_ICO`, `NAME_CARD`/`UPLOAD_CARD`/`NET_CARD`, `HOST_*`/`REMOTE_*`, `qr_card`, `make_page`, `HOST_PAGE`/`REMOTE_PAGE`.
- Server (~L1440–1463): `_LogErrors`, `ThreadingServer`, `SingleServer`, `make_server`.

## API routes (UI-coupled — highest silent-corruption risk)
`do_GET`: `/api/state` (L458, 1 s poll — file list grouped by user + `transfers`), `/api/speedtest` (L472), `/api/download` (L482, single; NO `Accept-Ranges` advertised — see ARCHITECTURE contract 1), `/api/download_all` (L570, one user), `/api/download_everything` (L584, everyone else, foldered).
`do_POST`: `/api/session` (L613), `/api/upload` (L626), `/api/rename` (L670), `/api/remove_file` (L681, unlinks only when `owner_id == sid` — BACKLOG 2 checks this).
