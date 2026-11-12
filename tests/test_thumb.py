"""BACKLOG 18 — thumbnails: the server side of POST/GET /api/thumb.

The thumbnail itself is drawn by the uploader's BROWSER (the server has no image
decoder); this test plays the browser's part over raw sockets and checks only
what the server must do with the bytes it is handed:

  * the file's owner can post a JPEG -> 200, the file gains "thumb": true in
    /api/state, and GET /api/thumb returns the same bytes typed image/jpeg,
  * a different session posting for that file is refused (403) and changes nothing,
  * a post larger than THUMB_MAX_BYTES is refused (413),
  * a post that is not a JPEG is refused (400),
  * a failure report (?fail=reason, empty body) is accepted and written to the log,
  * removing the file removes the thumbnail: GET is 404 and "<id>.t" is gone from disk,
  * nothing leaves a traceback in the server log.

Run:  python3 tests/test_thumb.py     (exit 0 = pass)
"""
import os, sys, socket, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _dz_harness as H
import test_download_range as R      # reuse its upload / state helpers

PORT = 8076
R.PORT = PORT                        # the helpers read the port from their own module

# Not a real picture: the server only checks the 3-byte JPEG signature, so a
# signature followed by filler is enough to stand in for a thumbnail.
JPEG = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 60          # ~15 KB, like a real one

def request(method, target, sess, body=b""):
    """One HTTP request over a raw socket. Returns (status, headers dict, body)."""
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall((f"{method} {target} HTTP/1.1\r\nHost:x\r\nCookie: session={sess}\r\n"
               f"User-Agent: dz-test-agent\r\n"
               f"Content-Length:{len(body)}\r\nConnection:close\r\n\r\n").encode() + body)
    head, rest = H.recv_headers(s)
    data = bytearray(rest)
    while True:
        d = s.recv(65536)
        if not d: break
        data += d
    s.close()
    hdrs = {}
    for line in head.split("\r\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            hdrs[k.strip().lower()] = v.strip()
    return int(head.split(None, 2)[1]), hdrs, bytes(data)

def main():
    path = H.make_patched(PORT)
    logf = os.path.join(os.path.dirname(path), "DropZone.log")
    srv = H.launch(path); checks = []
    def check(name, cond):
        checks.append((name, bool(cond)))
        print(f"  [{'ok' if cond else 'XX'}] {name}")
    try:
        if not H.wait_port(PORT): print("server did not start"); return 1
        owner, other = H.get_session(PORT), H.get_session(PORT)

        R.upload_bytes(owner, "photo.jpg", b"pretend photo " * 1000)
        f = R.get_state(owner)["user"]["files"][0]
        fid, thumb_path = f["id"], f["tmp_path"] + ".t"
        check("a new upload has no thumbnail yet",
              not f.get("thumb") and request("GET", f"/api/thumb?id={fid}", other)[0] == 404)

        # --- refusals: none of these may create a thumbnail -------------------
        check("another session's post is refused (403)",
              request("POST", f"/api/thumb?id={fid}", other, JPEG)[0] == 403)
        check("an oversize post is refused (413)",
              request("POST", f"/api/thumb?id={fid}", owner, JPEG[:4] + bytes(300 * 1024))[0] == 413)
        check("a post that is not a JPEG is refused (400)",
              request("POST", f"/api/thumb?id={fid}", owner, b"<html>not a picture</html>")[0] == 400)
        check("a post for an unknown file is 404",
              request("POST", "/api/thumb?id=nosuchid", owner, JPEG)[0] == 404)
        check("after the refusals there is still no thumbnail",
              not os.path.exists(thumb_path)
              and not R.get_state(owner)["user"]["files"][0].get("thumb"))

        # --- a failure report from the browser lands in the log ---------------
        check("a failure report is accepted (200)",
              request("POST", f"/api/thumb?id={fid}&fail=decode+error&ms=41&src=4032x3024", owner)[0] == 200)

        # --- the owner's post ---------------------------------------------------
        check("the owner's post is accepted (200)",
              request("POST", f"/api/thumb?id={fid}&ms=120&src=4032x3024", owner, JPEG)[0] == 200)
        seen_by_other = [x for u in R.get_state(other)["all_users"] for x in u["files"] if x["id"] == fid]
        check("the file is flagged thumb:true for the owner and for another user",
              R.get_state(owner)["user"]["files"][0].get("thumb") is True
              and len(seen_by_other) == 1 and seen_by_other[0].get("thumb") is True)
        s, h, b = request("GET", f"/api/thumb?id={fid}", other)
        check("GET returns the same bytes, typed image/jpeg, sniffing off",
              s == 200 and b == JPEG and h.get("content-type") == "image/jpeg"
              and h.get("x-content-type-options") == "nosniff")

        # --- removal takes the thumbnail with it --------------------------------
        request("POST", "/api/remove_file", owner, ('{"id":"%s"}' % fid).encode())
        check("after remove_file: GET is 404 and the .t file is gone from disk",
              request("GET", f"/api/thumb?id={fid}", other)[0] == 404
              and not os.path.exists(thumb_path) and not os.path.exists(f["tmp_path"]))

        # --- the log holds what a field run needs --------------------------------
        time.sleep(0.3)
        log = open(logf, encoding="utf-8", errors="replace").read() if os.path.exists(logf) else ""
        check("log: saved line carries timing, source size and the browser's User-Agent",
              any("thumb saved" in l and "ms=120" in l and "src=4032x3024" in l
                  and "UA=dz-test-agent" in l for l in log.splitlines()))
        check("log: the browser's failure report is recorded with its reason",
              any("thumb FAILED" in l and "decode error" in l for l in log.splitlines()))
        check("no traceback in server log", "Traceback" not in log)

        ok = all(v for _, v in checks)
        print("\nTHUMBNAILS (server):", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        H.stop(srv)

if __name__ == "__main__":
    sys.exit(main())
