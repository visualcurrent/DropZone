"""BACKLOG 16 — single-file download of a file whose NAME is not plain ASCII.

Motivation (field, 2026-11-11): downloading 'Pickled Daikon Crunch (40’s).mp3'
(curly apostrophe) or a name with an emoji failed, while the zip of the same
files worked. /api/download put the raw name into the Content-Disposition
header; http.server can only send latin-1 header text, so send_header raised
UnicodeEncodeError and the connection closed with no response.

This verifies, for several awkward names:

  * the download is 200 and the body is byte-exact,
  * the header's quoted filename="" part is plain printable ASCII,
  * the header's filename*=UTF-8'' part decodes back to the exact original name,
  * nothing leaves a traceback in the server log.

Run:  python3 tests/test_download_filename.py     (exit 0 = pass)
"""
import os, sys, re, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _dz_harness as H
import test_download_range as R      # reuse its upload / state / download helpers

PORT = 8075
R.PORT = PORT                        # the helpers read the port from their own module

NAMES = [
    "plain.txt",                                     # control: must keep working
    "Pickled Daikon Crunch (40’s).mp3",         # curly apostrophe (the field case)
    "CHOOSE YOURSELF ☀️ Take Your Power Back.opus",   # emoji (the field case)
    "café résumé.txt",                # latin-1 accents
    "日本語のファイル.txt",     # Japanese
]

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

        # Each file's body is its own name, so a mixed-up download is caught too.
        bodies = {n: ("body of " + n).encode("utf-8") * 50 for n in NAMES}
        for n in NAMES:
            R.upload_bytes(sess, n, bodies[n])

        by_name = {f["name"]: f["id"] for f in R.get_state(sess)["user"]["files"]}
        check("all names stored exactly as uploaded", sorted(by_name) == sorted(NAMES))

        for i, n in enumerate(NAMES, 1):
            if n not in by_name: continue
            s, h, b = R.dl(by_name[n], sess)
            cd = h.get("content-disposition", "")
            # Header layout: attachment; filename="<ascii>"; filename*=UTF-8''<percent-encoded>
            m = re.match(r'attachment; filename="([^"]*)"; filename\*=UTF-8\'\'(\S+)$', cd)
            check(f"name {i}: 200 + body byte-exact", s == 200 and b == bodies[n])
            check(f"name {i}: quoted filename is printable ASCII",
                  bool(m) and all(0x20 <= ord(c) <= 0x7e for c in m.group(1)))
            check(f"name {i}: filename* decodes to the original name",
                  bool(m) and urllib.parse.unquote(m.group(2)) == n)

        time.sleep(0.3)
        tb_free = ("Traceback" not in open(logf, encoding="utf-8", errors="replace").read()) \
                  if os.path.exists(logf) else True
        check("no traceback in server log", tb_free)

        ok = all(v for _, v in checks)
        print("\nDOWNLOAD FILENAME:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        H.stop(srv)

if __name__ == "__main__":
    sys.exit(main())
