"""BACKLOG 10 — HTTP Range support on /api/download (single-file downloads).

Motivation: iOS Safari probes a download with a Range request and, if the server
answers a plain 200 instead of 206, re-fetches — producing an OS-suffixed
duplicate ("name (1).ext"). This verifies the server now speaks Range correctly:

  * a full GET is 200 with ETag/Last-Modified and the exact body, and does NOT
    advertise Accept-Ranges (so browsers don't segment/duplicate — BACKLOG 10),
  * byte ranges (closed, open-ended, suffix) return 206 with the right
    Content-Range and the correct slice (offset-sensitive, patterned body),
  * a range past EOF returns 416 with Content-Range: bytes */size,
  * If-Range with a stale validator is ignored -> 200 full body,
  * a multi-range header is ignored -> 200 full body,
  * a large slice (> STREAM_THRESHOLD) streams from disk via seek, byte-exact,
  * nothing above leaves a traceback in the server log.

Run:  python3 tests/test_download_range.py     (exit 0 = pass)
"""
import os, sys, socket, time, re, json, hashlib, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _dz_harness as H

PORT = 8074
PERIOD = bytes(range(256))                      # non-uniform, repeating -> offset-sensitive

def patfile(size):
    return (PERIOD * (size // 256 + 1))[:size]

def upload_bytes(sess, filename, body):
    bnd = "----dzrange%d" % int(time.time() * 1000)
    head = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
    closing = f"--{bnd}--\r\n".encode()
    total = len(head) + len(body) + 2 + len(closing)
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall((f"POST /api/upload HTTP/1.1\r\nHost:x\r\n"
               f"Content-Type: multipart/form-data; boundary={bnd}\r\n"
               f"Cookie: session={sess}\r\nContent-Length:{total}\r\nConnection:close\r\n\r\n").encode())
    s.sendall(head); s.sendall(body); s.sendall(b"\r\n"); s.sendall(closing)
    d = b""
    while True:
        x = s.recv(65536)
        if not x: break
        d += x
    s.close()

def get_state(sess):
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall((f"GET /api/state HTTP/1.1\r\nHost:x\r\nCookie: session={sess}\r\n"
               f"Connection:close\r\n\r\n").encode())
    head, rest = H.recv_headers(s)
    clen = int(re.search(r"Content-Length:\s*(\d+)", head, re.I).group(1))
    body = bytearray(rest)
    while len(body) < clen:
        d = s.recv(65536)
        if not d: break
        body += d
    s.close()
    return json.loads(body.decode("utf-8"))

def dl(fid, sess, rng=None, ifrange=None):
    s = socket.create_connection(("127.0.0.1", PORT))
    req = (f"GET /api/download?id={fid} HTTP/1.1\r\nHost:x\r\n"
           f"Cookie: session={sess}\r\nConnection:close\r\n")
    if rng:     req += f"Range: {rng}\r\n"
    if ifrange: req += f"If-Range: {ifrange}\r\n"
    req += "\r\n"
    s.sendall(req.encode())
    head, rest = H.recv_headers(s)
    status = int(head.split(None, 2)[1])
    hdrs = {}
    for line in head.split("\r\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            hdrs[k.strip().lower()] = v.strip()
    body = bytearray(rest)
    clen = int(hdrs.get("content-length", "0"))
    while len(body) < clen:
        d = s.recv(1048576)
        if not d: break
        body += d
    s.close()
    return status, hdrs, bytes(body)

def main():
    path = H.make_patched(PORT)
    logf = os.path.join(os.path.dirname(path), "DropZone.log")
    srv = H.launch(path); checks = []
    def check(name, cond):
        checks.append((name, bool(cond)))
        print(f"  [{'ok' if cond else 'XX'}] {name}")
    try:
        if not H.wait_port(PORT): print("server did not start"); return 1
        sess = H.get_session(PORT)

        SMALL = 8 * 1024 * 1024                      # < STREAM_THRESHOLD (64 MB) -> buffered
        LARGE = 70 * 1024 * 1024                     # > STREAM_THRESHOLD -> streamed slice
        small_body, large_body = patfile(SMALL), patfile(LARGE)
        upload_bytes(sess, "small.bin", small_body)
        upload_bytes(sess, "large.bin", large_body)

        st = get_state(sess)
        by_name = {f["name"]: f["id"] for f in st["user"]["files"]}
        sfid, lfid = by_name["small.bin"], by_name["large.bin"]

        # 1) full GET: 200, advertises range support, exact body
        s, h, b = dl(sfid, sess)
        check("full GET is 200", s == 200)
        check("full 200 does NOT advertise Accept-Ranges (anti-segmentation)", h.get("accept-ranges") is None)
        check("ETag present", bool(h.get("etag")))
        check("Last-Modified present", bool(h.get("last-modified")))
        check("full Content-Length == size", int(h.get("content-length","0")) == SMALL)
        check("full body byte-exact", b == small_body)
        etag = h.get("etag")

        # 2) closed range
        s, h, b = dl(sfid, sess, "bytes=0-99")
        check("closed range is 206", s == 206)
        check("closed Content-Range", h.get("content-range") == f"bytes 0-99/{SMALL}")
        check("closed Content-Length 100", int(h.get("content-length","0")) == 100)
        check("closed slice exact", b == small_body[0:100])

        # 3) mid range (offset-sensitive)
        s, h, b = dl(sfid, sess, "bytes=1000-1999")
        check("mid range 206 + slice", s == 206 and b == small_body[1000:2000]
              and h.get("content-range") == f"bytes 1000-1999/{SMALL}")

        # 4) suffix range: final 100 bytes
        s, h, b = dl(sfid, sess, "bytes=-100")
        check("suffix range 206", s == 206)
        check("suffix Content-Range", h.get("content-range") == f"bytes {SMALL-100}-{SMALL-1}/{SMALL}")
        check("suffix slice exact", b == small_body[-100:])

        # 5) open-ended range to EOF
        s, h, b = dl(sfid, sess, "bytes=500-")
        check("open-ended 206 to EOF", s == 206 and b == small_body[500:]
              and int(h.get("content-length","0")) == SMALL - 500)

        # 6) unsatisfiable (start at EOF)
        s, h, b = dl(sfid, sess, f"bytes={SMALL}-")
        check("past-EOF is 416", s == 416)
        check("416 Content-Range */size", h.get("content-range") == f"bytes */{SMALL}")

        # 7) If-Range with a stale validator -> ignored -> full 200
        s, h, b = dl(sfid, sess, "bytes=0-99", ifrange='"stale-nomatch"')
        check("If-Range mismatch -> 200 full", s == 200 and len(b) == SMALL)

        # 7b) If-Range that matches -> honored -> 206
        s, h, b = dl(sfid, sess, "bytes=0-99", ifrange=etag)
        check("If-Range match -> 206", s == 206 and len(b) == 100)

        # 8) multi-range header -> ignored -> full 200
        s, h, b = dl(sfid, sess, "bytes=0-9,20-29")
        check("multi-range -> 200 full", s == 200 and len(b) == SMALL)

        # 9) large slice via the streaming/seek path (> STREAM_THRESHOLD)
        s, h, b = dl(lfid, sess, "bytes=5-")               # span = LARGE-5 > 64 MB
        check("large streamed slice 206", s == 206)
        check("large slice length", int(h.get("content-length","0")) == LARGE - 5)
        check("large slice byte-exact (seek ok)",
              hashlib.sha256(b).hexdigest() == hashlib.sha256(large_body[5:]).hexdigest())

        # 10) small probe on the large file (Safari-style)
        s, h, b = dl(lfid, sess, "bytes=0-1")
        check("probe of large file 206", s == 206 and b == large_body[0:2])

        time.sleep(0.3)
        tb_free = ("Traceback" not in open(logf, encoding="utf-8", errors="replace").read()) \
                  if os.path.exists(logf) else True
        check("no traceback in server log", tb_free)

        ok = all(v for _, v in checks)
        print("\nDOWNLOAD RANGE:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        H.stop(srv)

if __name__ == "__main__":
    sys.exit(main())
