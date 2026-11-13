"""
dc_host.py - DropCast's additions on top of the UNEDITED DropZone core.

dz_host.py (shared with DropZone's app) starts and stops the server. This file
holds what only DropCast needs. Through PLAN.md > M2 step 3 that is two jobs:

  1. putting a file the HOST shares into the core's file list, so the core's
     own /api/download route can send it (new_slot / register / discard);
  2. DropCast's pages (CastHandler): the guest page at /f/<id>, one file each.

How a host file gets in (the "copy-in")
---------------------------------------
The Java side (CopyIn) does the heavy part, because only Java can read a file
handed over by another Android app:

  1. Java calls new_slot()            -> [fid, path]   an id and an empty path
  2. Java copies the shared file to that path, hashing it (MD5) as it goes,
     and may leave a thumbnail beside it as "<fid>.t"
  3. Java calls register(fid, name, md5)

register() runs the same-file check: if a file with the same MD5 is already
held, the fresh copy is deleted and the existing file's id is returned, so one
file never gets two ids (and later, two QR codes).

Core names used here (ARCHITECTURE.md > Contracts, the Android list):
UPLOAD_DIR, shared_files, state_lock, get_or_create_user, fmt_size, log,
Handler, CSS, LOGO_SVG.
"""

import html
import uuid
from pathlib import Path
from urllib.parse import urlparse

import DropZone as dz   # already imported and configured by dz_host.start()

# The core files every shared file under a "user" keyed by a session id.
# Guests get theirs from the browser; the host's files, which never pass
# through a browser, are filed under this fixed one.
HOST_SID = "dropcast-host"


# ─── Copy-in ──────────────────────────────────────────────────────────────────

def new_slot():
    """Reserve an id and a path for one incoming host file.

    Returns [fid, path]. Nothing is created on disk; Java creates the file
    when it starts copying. Same id shape the core's upload route uses.
    """
    fid = str(uuid.uuid4())[:8]
    return [fid, str(Path(dz.UPLOAD_DIR) / fid)]


def register(fid, name, md5):
    """Add a finished copy to the core's file list, or reuse an identical file.

    fid:  the id from new_slot(); the copy must already be complete at its path.
    name: the file's display name, e.g. "holiday.mp4".
    md5:  hex MD5 of the copied bytes, computed by Java during the copy.

    Returns [fid_to_use, reused]. reused is True when an identical file was
    already held; in that case the fresh copy has been DELETED from disk.

    If Java left a thumbnail beside the copy ("<fid>.t", the core's own
    thumbnail slot), the file is marked as having one.
    """
    path = Path(dz.UPLOAD_DIR) / fid
    thumb = Path(str(path) + ".t")
    size = path.stat().st_size
    user = dz.get_or_create_user(HOST_SID)   # takes state_lock itself, so call it first

    with dz.state_lock:
        # Same-file check: a few files at most, so a plain scan is enough.
        for other in dz.shared_files.values():
            if other.get("md5") == md5 and other["size"] == size:
                existing = other["id"]
                break
        else:   # for/else: runs only when the loop found no match
            existing = None
            # Same fields the core's upload route writes, plus md5.
            entry = {"id": fid, "name": name, "tmp_path": str(path),
                     "size": size, "size_str": dz.fmt_size(size), "md5": md5}
            if thumb.exists():
                entry["thumb"] = True     # same flag the core sets after POST /api/thumb
            user["files"].append(entry)
            dz.shared_files[fid] = {**entry, "owner_id": HOST_SID, "owner_name": user["name"]}

    if existing is not None:
        path.unlink(missing_ok=True)          # FILE EFFECT: deletes the duplicate copy
        thumb.unlink(missing_ok=True)         # ... and its thumbnail
        dz.log(f"copy-in: '{name}' {dz.fmt_size(size)} md5={md5} is already held as [{existing}]; duplicate deleted")
        return [existing, True]

    dz.log(f"copy-in saved: '{name}' [{fid}] {dz.fmt_size(size)} md5={md5} thumb={thumb.exists()}")
    return [fid, False]


def discard(fid):
    """Delete a copy that did not finish (copy failed or ran out of space)."""
    (Path(dz.UPLOAD_DIR) / fid).unlink(missing_ok=True)            # FILE EFFECT: deletes the partial copy
    (Path(dz.UPLOAD_DIR) / (fid + ".t")).unlink(missing_ok=True)   # ... and its thumbnail
    dz.log(f"copy-in abandoned: [{fid}] partial file deleted")


# ─── Pages ────────────────────────────────────────────────────────────────────
# DropCast's pages are plain HTML built here on the server: no script, no web
# font and no outside address, so they work on a WiFi with no internet.

# Icon shown when a file has no thumbnail, chosen by the name's ending.
_ICONS = [
    ("\U0001F5BC", "jpg jpeg png gif webp svg heic heif bmp"),   # framed picture
    ("\U0001F3AC", "mp4 mov avi mkv webm m4v 3gp"),              # clapper board
    ("\U0001F3B5", "mp3 flac wav aac m4a ogg opus"),             # musical note
    ("\U0001F4C4", "pdf"),                                       # page
    ("\U0001F4DD", "doc docx odt rtf txt md"),                   # memo
    ("\U0001F4CA", "xls xlsx ods csv"),                          # bar chart
    ("\U0001F4CB", "ppt pptx odp"),                              # clipboard
    ("\U0001F5DC", "zip rar 7z tar gz bz2 xz"),                  # clamp
    ("\U0001F4F1", "apk ipa"),                                   # phone
]
_ICON_OTHER = "\U0001F4C1"    # folder
_ICON_GONE = "\U0001F50D"     # magnifying glass


def _icon(name):
    """The emoji for a file name, by its extension; a folder for anything else."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    for emoji, exts in _ICONS:
        if ext in exts.split():
            return emoji
    return _ICON_OTHER


# Page-only styles. Colours and the light/dark switch come from the core's own
# stylesheet (dz.CSS), so DropCast matches DropZone and follows the phone's theme.
_PAGE_CSS = """
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
.dc-wrap{max-width:26rem;margin:0 auto;padding:1.25rem 1rem 2.5rem;
  display:flex;flex-direction:column;align-items:center;gap:1.1rem}
.dc-logo{display:flex;align-items:center;gap:.45rem;font-weight:700;font-size:1.15rem;color:var(--pri)}
.dc-note{text-align:center;color:var(--muted);font-size:.95rem;line-height:1.5}
.dc-note b{color:var(--txt);font-weight:600}
.dc-frame{width:100%;background:var(--surf2);border:1px solid var(--border);border-radius:var(--rx);
  box-shadow:var(--sh);padding:1.5rem 1.25rem;display:flex;flex-direction:column;align-items:center;gap:1rem}
.dc-thumb{max-width:100%;max-height:15rem;border-radius:var(--r);border:1px solid var(--div);background:var(--off)}
.dc-icon{font-size:4.5rem;line-height:1.1}
.dc-name{font-weight:600;font-size:1.05rem;text-align:center;overflow-wrap:anywhere}
.dc-size{color:var(--hint);font-size:.85rem;margin-top:-.6rem}
.dc-btn{display:block;width:100%;text-align:center;text-decoration:none;background:var(--pri);color:#fff;
  font-weight:600;font-size:1.05rem;padding:.9rem 1rem;border-radius:var(--rfull)}
.dc-btn:active{background:var(--pri-h)}
.dc-foot{color:var(--hint);font-size:.78rem;text-align:center}
"""


def _page(title, inner):
    """Wrap a page's content in DropCast's shell (header, styles)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>{dz.CSS}{_PAGE_CSS}</style>
</head>
<body>
<main class="dc-wrap">
  <div class="dc-logo">{dz.LOGO_SVG} DropCast</div>
{inner}
</main>
</body>
</html>"""


def file_page(f):
    """The guest page for one shared file (f is its shared_files entry)."""
    name = html.escape(f["name"])          # a file name is outside text: never trust it as HTML
    fid = f["id"]                          # made by us (hex), safe in an address
    if f.get("thumb"):
        picture = f'<img class="dc-thumb" src="/api/thumb?id={fid}" alt="">'
    else:
        picture = f'<div class="dc-icon">{_icon(f["name"])}</div>'
    return _page(f["name"], f"""
  <p class="dc-note"><b>Someone nearby is sharing a file with you.</b><br>
    It comes straight from their phone over this WiFi. Nothing goes through the internet.</p>
  <section class="dc-frame">
    {picture}
    <div class="dc-name">{name}</div>
    <div class="dc-size">{f["size_str"]}</div>
    <a class="dc-btn" href="/api/download?id={fid}" download>Download</a>
  </section>
  <p class="dc-foot">Stay on this WiFi until the download finishes.</p>""")


def gone_page():
    """Shown for an address whose file is not (or no longer) shared."""
    return _page("DropCast", f"""
  <section class="dc-frame">
    <div class="dc-icon">{_ICON_GONE}</div>
    <div class="dc-name">This file is not being shared right now</div>
  </section>
  <p class="dc-note">Ask the person sharing it to show you their QR code again.</p>""")


class CastHandler(dz.Handler):
    """The core's request handler plus DropCast's pages.

    A subclass: everything not handled here (the /api/... routes, uploads)
    falls through to the core's own code unchanged.
    """

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/f/"):
            f = dz.shared_files.get(path[3:])
            if f:
                self._send_page(file_page(f), 200)
                dz.log(f"guest page [{f['id']}] to {self.client_address[0]}; "
                       f"UA={self.headers.get('User-Agent', '?')[:200]}")
            else:
                self._send_page(gone_page(), 404)
            return
        # DropZone's own host and guest pages are not part of DropCast.
        if path in ("/", "/host", "/remote"):
            self._send_page(gone_page(), 404)
            return
        super().do_GET()

    def _send_page(self, page, status):
        """Send an HTML page, never cached (same reason as the core's send_html)."""
        body = page.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(body)


def install():
    """Called by dz_host.start() just before the server is made.

    make_server() looks up the name "Handler" in the core at call time, so
    replacing it here makes the server use CastHandler. Same technique as
    dz_host's LOG_FILE / UPLOAD_DIR / LOCAL_IP / PORT replacements.
    """
    dz.Handler = CastHandler
