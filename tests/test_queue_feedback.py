"""BACKLOG 6 — live transfer activity/queue feedback via /api/state.

Forces the transfer semaphore to 1, fires three concurrent downloads, and polls
/api/state (a separate request from the blocked downloads). Verifies it reports
one 'sending' and the others 'queued' with positions, and that the registry
drains to empty when the transfers finish.

Run:  python3 tests/test_queue_feedback.py     (exit 0 = pass)
"""
import os, sys, socket, time, threading, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _dz_harness as H

PORT = 8072

def slow_download(sess, uid):
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall((f"GET /api/download_all?user={uid} HTTP/1.1\r\nHost:x\r\n"
               f"Cookie: session={sess}\r\nConnection:close\r\n\r\n").encode())
    H.recv_headers(s)
    while True:
        try: d = s.recv(4*1048576)
        except OSError: break
        if not d: break
        time.sleep(0.25)          # throttle so the transfer lingers
    s.close()

def poll(sess):
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall((f"GET /api/state HTTP/1.1\r\nHost:x\r\nCookie: session={sess}\r\nConnection:close\r\n\r\n").encode())
    head, rest = H.recv_headers(s)
    clen = int(re.search(r"Content-Length:\s*(\d+)", head, re.I).group(1))
    while len(rest) < clen:
        d = s.recv(65536)
        if not d: break
        rest += d
    s.close()
    return json.loads(rest[:clen].decode("utf-8")).get("transfers", [])

def main():
    path = H.make_patched(PORT, max_concurrent=1)
    srv = H.launch(path)
    try:
        if not H.wait_port(PORT): print("server did not start"); return 1
        sess = H.get_session(PORT)
        H.upload_file(PORT, sess, "clip.bin", 90*1048576)
        ths = [threading.Thread(target=slow_download, args=(sess, sess), daemon=True) for _ in range(3)]
        for t in ths: t.start(); time.sleep(0.15)
        saw_sending = saw_queued = False; positions = set()
        for _ in range(14):
            for tr in poll(sess):
                if tr["phase"] == "sending": saw_sending = True
                if tr["phase"] == "queued":
                    saw_queued = True
                    if tr["pos"]: positions.add(tr["pos"])
            time.sleep(0.4)
        for t in ths: t.join(timeout=15)
        time.sleep(0.5)
        drained = len(poll(sess)) == 0
        ok = saw_sending and saw_queued and (2 in positions) and drained
        print(f"  sending={saw_sending} queued={saw_queued} positions={sorted(positions)} drained={drained}")
        print("\nQUEUE FEEDBACK:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        H.stop(srv)

if __name__ == "__main__":
    sys.exit(main())
