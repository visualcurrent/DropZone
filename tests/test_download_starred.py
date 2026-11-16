"""BACKLOG (Starred section) — GET /api/download_starred?ids=a,b,c: one flat zip.

Two sessions each upload files; two files share the name "same.txt" so the
de-duplication is exercised. The test then checks that the route:

  * returns 200 with a Content-Length equal to the bytes actually received,
  * returns a valid zip (testzip clean) holding exactly the chosen files and
    no others, each member byte-exact, same-named files told apart,
  * skips an unknown id mixed in with valid ones (still 200, right members),
  * writes a repeated id once, not twice,
  * answers 404 for only-unknown ids and for an empty ids value.

The zip is read into memory (io.BytesIO), never written to disk, so no file
stays open that could not be deleted on Windows.

Run:  python3 tests/test_download_starred.py     (exit 0 = pass)
"""
import os, sys, socket, re, io, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _dz_harness as H
import test_download_range as R      # reuse its upload / state helpers

PORT = 8077
R.PORT = PORT                        # the helpers read the port from their own module

def fetch(sess, ids_value):
    """GET /api/download_starred?ids=<ids_value>. Returns (status, clen or None, body bytes)."""
    s = socket.create_connection(("127.0.0.1", PORT))
    s.sendall((f"GET /api/download_starred?ids={ids_value} HTTP/1.1\r\nHost:x\r\n"
               f"Cookie: session={sess}\r\nConnection:close\r\n\r\n").encode())
    head, rest = H.recv_headers(s)
    status = int(head.split(None, 2)[1])
    m = re.search(r"Content-Length:\s*(\d+)", head, re.I)
    clen = int(m.group(1)) if m else None
    body = bytearray(rest)
    while True:                      # Connection: close, so read until the server hangs up
        d = s.recv(1048576)
        if not d: break
        body += d
    s.close()
    return status, clen, bytes(body)

def members(body):
    """Open a zip held in memory. Returns (testzip_clean, {member name: bytes})."""
    z = zipfile.ZipFile(io.BytesIO(body))
    return z.testzip() is None, {n: z.read(n) for n in z.namelist()}

def main():
    path = H.make_patched(PORT)
    srv = H.launch(path); checks = []
    def check(name, cond):
        checks.append((name, bool(cond)))
        print(f"  [{'ok' if cond else 'XX'}] {name}")
    try:
        if not H.wait_port(PORT): print("server did not start"); return 1
        sa, sb = H.get_session(PORT), H.get_session(PORT)

        # Distinct content per file so a wrong member cannot match by accident.
        data = {
            ("A", "same.txt"):    b"alpha same " * 500,
            ("A", "a_only.bin"):  bytes(range(256)) * 40,
            ("A", "skipped.dat"): b"never starred " * 300,
            ("B", "same.txt"):    b"bravo same " * 700,
            ("B", "b_only.bin"):  bytes(range(255, -1, -1)) * 33,
        }
        for (who, name), body in data.items():
            R.upload_bytes(sa if who == "A" else sb, name, body)

        # Read the ids back from /api/state: own files from "user", others from "all_users".
        ids = {}
        for f in R.get_state(sa)["user"]["files"]: ids[("A", f["name"])] = f["id"]
        for f in R.get_state(sb)["user"]["files"]: ids[("B", f["name"])] = f["id"]
        check("all five uploads got an id", len(ids) == len(data))

        chosen = [("A", "same.txt"), ("A", "a_only.bin"), ("B", "same.txt"), ("B", "b_only.bin")]
        chosen_ids = [ids[k] for k in chosen]

        # --- 1. the chosen subset ---------------------------------------------
        status, clen, body = fetch(sa, ",".join(chosen_ids))
        check("subset: 200 and Content-Length equals bytes received",
              status == 200 and clen == len(body))
        clean, got = members(body)
        check("subset: testzip is clean", clean)
        # Two "same.txt" must both survive under different archive names.
        expected_bytes = sorted(data[k] for k in chosen)
        check("subset: exactly 4 members, no skipped.dat",
              len(got) == 4 and not any("skipped" in n for n in got))
        check("subset: every member's bytes equal what was uploaded (both same.txt kept)",
              sorted(got.values()) == expected_bytes)
        check("subset: member names are flat and distinct",
              all("/" not in n for n in got) and len(set(got)) == 4)

        # --- 2. an unknown id among valid ones is skipped ------------------------
        status, clen, body = fetch(sa, f"{chosen_ids[0]},nosuchid,{chosen_ids[1]}")
        clean, got = members(body) if status == 200 else (False, {})
        check("unknown id mixed in: 200, clean zip, only the two valid members",
              status == 200 and clen == len(body) and clean
              and sorted(got.values()) == sorted([data[chosen[0]], data[chosen[1]]]))

        # --- 3. a repeated id gives one member ------------------------------------
        status, clen, body = fetch(sa, f"{chosen_ids[1]},{chosen_ids[1]},{chosen_ids[1]}")
        clean, got = members(body) if status == 200 else (False, {})
        check("repeated id: one member, bytes exact",
              status == 200 and clean and list(got.values()) == [data[chosen[1]]])

        # --- 4. nothing usable -> 404 ---------------------------------------------
        check("only unknown ids: 404", fetch(sa, "nosuch1,nosuch2")[0] == 404)
        check("empty ids: 404", fetch(sa, "")[0] == 404)
        check("only commas: 404", fetch(sa, ",,,")[0] == 404)

        ok = all(v for _, v in checks)
        print("\nDOWNLOAD STARRED:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        H.stop(srv)

if __name__ == "__main__":
    sys.exit(main())
