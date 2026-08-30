"""BACKLOG 13 — ZIP downloads stream as built: exact length, instant, valid.

Uploads a few files (incl. a unicode name), downloads the per-user ZIP, and
verifies:
  * advertised Content-Length == bytes actually streamed == DropZone.zip_stream_size(),
  * time-to-first-byte is tiny (streamed, not spooled first),
  * the archive is valid (Python zipfile; and Info-ZIP `unzip -t` if present) and
    extracts byte-exact,
  * a mid-stream cancel leaves no traceback in the server log.

Run:  python3 tests/test_zip_streaming.py     (exit 0 = pass)
"""
import os, sys, socket, time, re, hashlib, tempfile, subprocess, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _dz_harness as H
sys.path.insert(0, H.REPO)
import DropZone   # for the real zip_stream_size()

PORT = 8073

def download(sess, uid, out, cancel_after=None):
    s = socket.create_connection(("127.0.0.1", PORT)); t0 = time.time()
    s.sendall((f"GET /api/download_all?user={uid} HTTP/1.1\r\nHost:x\r\n"
               f"Cookie: session={sess}\r\nConnection:close\r\n\r\n").encode())
    head, rest = H.recv_headers(s); ttfb = time.time() - t0
    clen = int(re.search(r"Content-Length:\s*(\d+)", head, re.I).group(1))
    got = bytearray(rest); fh = open(out, "wb"); fh.write(rest)
    while len(got) < clen:
        if cancel_after and len(got) >= cancel_after:
            s.close(); fh.close(); return "cancelled", clen, len(got), ttfb
        d = s.recv(1048576)
        if not d: break
        got += d; fh.write(d)
    s.close(); fh.close()
    return "done", clen, len(got), ttfb

def main():
    path = H.make_patched(PORT)
    logf = os.path.join(os.path.dirname(path), "DropZone.log")
    srv = H.launch(path); ok = True
    try:
        if not H.wait_port(PORT): print("server did not start"); return 1
        sess = H.get_session(PORT)
        files = [("Alpha.mkv", 120*1048576), ("Bravo file.bin", 80*1048576), ("charlié_名.dat", 20*1048576)]
        hashes = {n: H.upload_file(PORT, sess, n, sz) for n, sz in files}
        expected = DropZone.zip_stream_size([(n, None, sz) for n, sz in files])

        out = os.path.join(tempfile.gettempdir(), "dz_dl.zip")
        status, clen, got, ttfb = download(sess, sess, out)
        len_ok = clen == got == expected
        ttfb_ok = ttfb < 2.0
        print(f"  status={status} TTFB={ttfb*1000:.0f}ms  Content-Length={clen}  streamed={got}  formula={expected}  len_ok={len_ok}")

        z = zipfile.ZipFile(out)
        zip_ok = z.testzip() is None
        content_ok = all(hashlib.sha256(z.read(n)).hexdigest() == hashes[n] for n, _ in files)
        # Info-ZIP cross-check, if available
        unzip_ok = True
        try:
            r = subprocess.run(["unzip", "-t", out], capture_output=True, text=True)
            unzip_ok = r.returncode == 0 and "No errors" in r.stdout
        except FileNotFoundError:
            print("  (unzip not installed — skipped Info-ZIP cross-check)")
        print(f"  python-valid={zip_ok}  content-exact={content_ok}  unzip-t={unzip_ok}")
        os.remove(out)

        # cancel mid-stream -> must not produce a traceback
        download(sess, sess, os.path.join(tempfile.gettempdir(), "dz_dl2.zip"), cancel_after=8*1048576)
        time.sleep(0.5)
        traceback_free = ("Traceback" not in open(logf, encoding="utf-8", errors="replace").read()) if os.path.exists(logf) else True
        print(f"  cancel leaves no traceback: {traceback_free}")

        ok = len_ok and ttfb_ok and zip_ok and content_ok and unzip_ok and traceback_free
        print("\nZIP STREAMING:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        H.stop(srv)

if __name__ == "__main__":
    sys.exit(main())
