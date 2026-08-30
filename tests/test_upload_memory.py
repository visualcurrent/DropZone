"""BACKLOG 1 — uploads stream to disk with flat memory, byte-exact.

Verifies that uploading small, multi-file, and large bodies:
  * saves each file byte-exact (size + sha256), and
  * keeps the server's peak resident memory bounded (does NOT scale with the
    upload size — the bug that used to OOM-kill the phone on big files).

Run:  python3 tests/test_upload_memory.py     (exit 0 = pass)
"""
import os, sys, socket, time, threading, hashlib, glob, json, re, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _dz_harness as H

PORT = 8071
BLOCK = os.urandom(1048576)
MEM_LIMIT_MB = 150          # generous; real peak is ~30 MB even for 1+ GB uploads

def upload(sess, name, size):
    bnd = "----m%d" % int(time.time()*1000)
    head = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
    closing = f"--{bnd}--\r\n".encode()
    full, tail = divmod(size, len(BLOCK))
    total = len(head)+size+2+len(closing)
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall((f"POST /api/upload HTTP/1.1\r\nHost:x\r\nContent-Type: multipart/form-data; "
               f"boundary={bnd}\r\nCookie: session={sess}\r\nContent-Length:{total}\r\n"
               f"Connection:close\r\n\r\n").encode())
    s.sendall(head); h = hashlib.sha256()
    for _ in range(full): s.sendall(BLOCK); h.update(BLOCK)
    if tail: s.sendall(BLOCK[:tail]); h.update(BLOCK[:tail])
    s.sendall(b"\r\n"); s.sendall(closing)
    d = b""
    while True:
        x = s.recv(65536)
        if not x: break
        d += x
    s.close()
    body = d.partition(b"\r\n\r\n")[2]
    return h.hexdigest(), json.loads(body.decode("utf-8"))

def main():
    path = H.make_patched(PORT)
    srv = H.launch(path)
    ok = True
    try:
        if not H.wait_port(PORT): print("server did not start"); return 1
        pid = srv.pid; base = H.read_vmrss(pid); sess = H.get_session(PORT)
        cases = [("small.bin", 3*1048576 + 111),
                 ("a.bin", 40*1048576), ("big.bin", 800*1048576)]
        updir = None
        for name, size in cases:
            peak = [0.0]; stop = threading.Event()
            def samp():
                while not stop.is_set(): peak[0]=max(peak[0],H.read_vmrss(pid)); time.sleep(0.03)
            t = threading.Thread(target=samp, daemon=True); t.start()
            digest, resp = upload(sess, name, size)
            stop.set(); t.join()
            if updir is None:
                updir = max(glob.glob(os.path.join(tempfile.gettempdir(), "dropzone_*")), key=os.path.getmtime)
            fid = resp["files"][0]["id"]
            p = os.path.join(updir, fid)
            good = os.path.getsize(p) == size
            fh = hashlib.sha256(); 
            with open(p, "rb") as f:
                for ch in iter(lambda: f.read(1<<20), b""): fh.update(ch)
            good = good and fh.hexdigest() == digest
            mem_ok = (peak[0]-base) < MEM_LIMIT_MB
            print(f"  {name:9} {size//1048576:4} MB  saved-exact={good}  peakRSS={peak[0]:.0f}MB (Δ{peak[0]-base:.0f})  mem_ok={mem_ok}")
            ok = ok and good and mem_ok
            os.remove(p)
        print("\nUPLOAD MEMORY:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        H.stop(srv)

if __name__ == "__main__":
    sys.exit(main())
