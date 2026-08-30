"""Shared helpers for DropZone's tests.

The tests spin up the REAL server (a copy of ../DropZone.py with only PORT — and
optionally MAX_CONCURRENT_TRANSFERS — patched) on a high port, drive it over raw
sockets, and check observable behaviour. No third-party deps (matches the project
rule); standard library only. Linux/Termux only for the RSS checks (they read
/proc/<pid>/status).
"""
import os, re, sys, socket, subprocess, time, tempfile, signal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC  = os.path.join(REPO, "DropZone.py")

def make_patched(port, max_concurrent=None):
    """Write a copy of DropZone.py with PORT (and optionally the transfer
    concurrency cap) changed, into a fresh temp dir. Returns its path."""
    s = open(SRC, encoding="utf-8").read()
    s = re.sub(r'^PORT\s*=\s*\d+', f'PORT = {port}', s, count=1, flags=re.M)
    if max_concurrent is not None:
        s = re.sub(r'^MAX_CONCURRENT_TRANSFERS\s*=\s*\d+',
                   f'MAX_CONCURRENT_TRANSFERS = {max_concurrent}', s, count=1, flags=re.M)
    d = tempfile.mkdtemp(prefix="dztest_")
    p = os.path.join(d, "DropZone_under_test.py")
    open(p, "w", encoding="utf-8").write(s)
    return p

def launch(path):
    return subprocess.Popen([sys.executable, path], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, preexec_fn=os.setsid)

def wait_port(port, timeout=15):
    for _ in range(int(timeout * 4)):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close(); return True
        except OSError:
            time.sleep(0.25)
    return False

def stop(proc):
    try: os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    except Exception: pass
    time.sleep(1)
    try: proc.kill()
    except Exception: pass

def read_vmrss(pid):
    "Resident memory of the server process, MB (Linux/Termux /proc)."
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        return 0.0
    return 0.0

def recv_headers(sock):
    buf = b""
    while b"\r\n\r\n" not in buf:
        d = sock.recv(65536)
        if not d: break
        buf += d
    head, _, rest = buf.partition(b"\r\n\r\n")
    return head.decode("latin-1"), rest

def get_session(port):
    s = socket.create_connection(("127.0.0.1", port)); b = b"{}"
    s.sendall((f"POST /api/session HTTP/1.1\r\nHost:x\r\nContent-Type:application/json\r\n"
               f"Content-Length:{len(b)}\r\nConnection:close\r\n\r\n").encode() + b)
    d = b""
    while True:
        x = s.recv(65536)
        if not x: break
        d += x
    s.close()
    return re.search(r"session=([^;]+)", d.decode("latin-1")).group(1)

def upload_file(port, sess, filename, size_bytes, block=None):
    """Upload one file of the given size (streamed). Returns sha256 hex of the body."""
    import hashlib
    block = block or (b"\xa5" * 1048576)
    bnd = "----dztest%d" % int(time.time() * 1000)
    head = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
    closing = f"--{bnd}--\r\n".encode()
    full, tail = divmod(size_bytes, len(block))
    total = len(head) + size_bytes + 2 + len(closing)
    s = socket.create_connection(("127.0.0.1", port))
    s.sendall((f"POST /api/upload HTTP/1.1\r\nHost:x\r\n"
               f"Content-Type: multipart/form-data; boundary={bnd}\r\n"
               f"Cookie: session={sess}\r\nContent-Length:{total}\r\nConnection:close\r\n\r\n").encode())
    s.sendall(head); h = hashlib.sha256()
    for _ in range(full): s.sendall(block); h.update(block)
    if tail: s.sendall(block[:tail]); h.update(block[:tail])
    s.sendall(b"\r\n"); s.sendall(closing)
    d = b""
    while True:
        x = s.recv(65536)
        if not x: break
        d += x
    s.close()
    return h.hexdigest()
