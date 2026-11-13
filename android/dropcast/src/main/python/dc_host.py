"""
dc_host.py - DropCast's additions on top of the UNEDITED DropZone core.

dz_host.py (shared with DropZone's app) starts and stops the server. This file
holds what only DropCast needs. Through PLAN.md > M2 step 4 that is two jobs:

  1. putting a file the HOST shares into the core's file list, so the core's
     own /api/download route can send it (new_slot / register / discard);
  2. DropCast's pages (CastHandler): the guest page at /f/<id>, one file each,
     and the host's own screen at /host, shown inside the app.

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
UPLOAD_DIR, shared_files, users, state_lock, get_or_create_user, fmt_size,
log, Handler (and its send_json), CSS, LOGO_SVG, LOCAL_IP, PORT.
"""

import html
import uuid
from pathlib import Path
from urllib.parse import urlparse

import DropZone as dz   # already imported and configured by dz_host.start()
import dc_qr            # the QR drawing library as a string (generated file)

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


# ─── The host's own screen ────────────────────────────────────────────────────
# The app shows this page inside itself (a WebView pointed at 127.0.0.1), so it
# is only ever sent to the phone it runs on. Unlike the guest page it needs a
# script: it asks /dc/host_state once a second and redraws when that changes.
#
# Three things only the app can do are reached through "Android", an object
# the app adds to the page (MainActivity.Bridge):
#   Android.status()      -> the copy-in progress line, "" when idle
#   Android.chooseFile()  -> open Android's file picker
#   Android.stop()        -> stop DropCast and delete the files it holds

_HOST_CSS = """
.dc-qr{background:#fff;padding:14px;border-radius:var(--rx);border:1px solid var(--border)}
.dc-qr img,.dc-qr canvas{display:block}
.dc-url{color:var(--pri);font-size:.8rem;font-weight:500;text-align:center;overflow-wrap:anywhere}
.dc-thumb.small{max-height:8rem}
.dc-icon.small{font-size:3rem}
.dc-btn2{display:block;width:100%;text-align:center;background:none;color:var(--pri);
  border:1.5px solid var(--pri);font-weight:600;font-size:1rem;padding:.8rem 1rem;border-radius:var(--rfull)}
.dc-stop{color:var(--err);border-color:var(--err)}
.dc-prep{width:100%;background:var(--pri-hl);border-radius:var(--rx);padding:.9rem 1rem;
  color:var(--txt);font-size:.9rem;text-align:center;overflow-wrap:anywhere}
.dc-bar{height:4px;border-radius:2px;margin-top:.6rem;background:var(--div);overflow:hidden}
.dc-bar i{display:block;height:100%;width:35%;border-radius:2px;background:var(--pri);
  animation:dc-slide 1.1s ease-in-out infinite alternate}
@keyframes dc-slide{from{margin-left:0}to{margin-left:65%}}
.dc-list{width:100%;display:flex;flex-direction:column;gap:.4rem}
.dc-list h2{font-size:.8rem;font-weight:600;color:var(--hint);text-transform:uppercase;letter-spacing:.04em}
.dc-row{display:flex;justify-content:space-between;gap:.75rem;width:100%;text-align:left;
  background:var(--surf2);border:1px solid var(--border);border-radius:var(--r);padding:.6rem .8rem;font-size:.9rem}
.dc-row span:first-child{overflow-wrap:anywhere}
.dc-row span:last-child{color:var(--hint);white-space:nowrap}
[hidden]{display:none!important}
"""

# The page's script. A plain (non-f) Python string, and written with NO
# backslashes, so Python passes it to the browser exactly as typed.
_HOST_JS = """
var files = [];        // the host's shared files, oldest first (from /dc/host_state)
var base = '';         // http://<phone's WiFi address>:<port>
var shownId = null;    // id of the file whose QR is on screen
var picked = null;     // id the host tapped in "Earlier files"; null = newest
var $ = function(id){ return document.getElementById(id); };

function draw(){
  var f = null;
  for (var i = 0; i < files.length; i++) if (files[i].id === picked) f = files[i];
  if (!f && files.length) f = files[files.length - 1];      // default: the newest share

  $('empty').hidden = !!f;
  $('card').hidden = !f;
  $('choose').textContent = f ? 'Share another file' : 'Choose a file';
  $('choose').className = f ? 'dc-btn2' : 'dc-btn';

  // Rebuild the card and its QR only when a different file is shown.
  if (f && f.id !== shownId){
    shownId = f.id;
    var url = base + '/f/' + f.id;
    $('pic').innerHTML = '';
    if (f.thumb){
      var img = document.createElement('img');
      img.className = 'dc-thumb small'; img.alt = ''; img.src = '/api/thumb?id=' + f.id;
      $('pic').appendChild(img);
    } else {
      var d = document.createElement('div');
      d.className = 'dc-icon small'; d.textContent = f.icon;
      $('pic').appendChild(d);
    }
    $('name').textContent = f.name;       // textContent: a file name is never treated as HTML
    $('size').textContent = f.size_str;
    $('url').textContent = url;
    $('qr').innerHTML = '';
    new QRCode($('qr'), {text: url, width: 220, height: 220,
                         colorDark: '#000000', colorLight: '#ffffff',
                         correctLevel: QRCode.CorrectLevel.M});
  }
  if (!f) shownId = null;

  // Earlier files: every file except the one on show, newest first.
  var list = $('others'); list.innerHTML = '';
  var n = 0;
  for (var j = files.length - 1; j >= 0; j--){
    if (f && files[j].id === f.id) continue;
    var b = document.createElement('button');
    b.className = 'dc-row';
    var a = document.createElement('span'); a.textContent = files[j].name;
    var s = document.createElement('span'); s.textContent = files[j].size_str;
    b.appendChild(a); b.appendChild(s);
    b.onclick = (function(id){ return function(){ picked = id; draw(); window.scrollTo(0, 0); }; })(files[j].id);
    list.appendChild(b); n++;
  }
  $('othersBox').hidden = (n === 0);
}

function tick(){
  // 1. the copy-in progress line, straight from the app
  var st = (window.Android && Android.status()) || '';
  $('prep').hidden = !st;
  $('prepText').textContent = st;

  // 2. the file list, from the server on this phone
  fetch('/dc/host_state').then(function(r){ return r.json(); }).then(function(s){
    var newest = function(a){ return a.length ? a[a.length - 1].id : ''; };
    if (newest(s.files) !== newest(files)) picked = null;   // a new share takes over the screen
    files = s.files; base = s.base;
    draw();
  }).catch(function(){ /* server stopping or starting: try again next tick */ });
}

$('choose').onclick = function(){ if (window.Android) Android.chooseFile(); };
$('stop').onclick = function(){ if (window.Android) Android.stop(); };
tick();
setInterval(tick, 1000);
"""


def host_page():
    """The host's screen: the shared file with its QR, Choose a file, Stop."""
    inner = """
  <div id="prep" class="dc-prep" hidden><span id="prepText"></span><div class="dc-bar"><i></i></div></div>
  <p id="empty" class="dc-note"><b>Share a file with people nearby.</b><br>
    Choose a file here, or use Share in any app and pick DropCast.</p>
  <section id="card" class="dc-frame" hidden>
    <div id="pic"></div>
    <div id="name" class="dc-name"></div>
    <div id="size" class="dc-size"></div>
    <div id="qr" class="dc-qr"></div>
    <div id="url" class="dc-url"></div>
    <p class="dc-note">Anyone on this WiFi can scan this code to download the file.</p>
  </section>
  <button id="choose" class="dc-btn">Choose a file</button>
  <div id="othersBox" class="dc-list" hidden><h2>Earlier files</h2><div id="others" class="dc-list"></div></div>
  <button id="stop" class="dc-btn2 dc-stop">Stop sharing</button>
  <p class="dc-foot">Stop closes DropCast and removes the files it holds.</p>
  <script src="/dc/qrcode.js"></script>
  <script>""" + _HOST_JS + "</script>"
    # _page() puts _PAGE_CSS in; the host-only styles ride along in a second tag.
    return _page("DropCast", "<style>" + _HOST_CSS + "</style>" + inner)


def host_state():
    """What the host's screen needs: the host's own files and the address guests use."""
    with dz.state_lock:
        mine = list(dz.users.get(HOST_SID, {}).get("files", []))
    return {
        "base": f"http://{dz.LOCAL_IP}:{dz.PORT}",
        "files": [{"id": f["id"], "name": f["name"], "size_str": f["size_str"],
                   "thumb": bool(f.get("thumb")), "icon": _icon(f["name"])} for f in mine],
    }


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
        # The host's screen and its data: only for the phone itself. A guest
        # asking for them gets the same "not shared" page as any unknown address.
        if path in ("/host", "/dc/host_state"):
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                self._send_page(gone_page(), 404)
            elif path == "/host":
                self._send_page(host_page(), 200)
            else:
                self.send_json(host_state())
            return
        # The QR drawing library (dc_qr.py). It never changes, so let the
        # browser keep it.
        if path == "/dc/qrcode.js":
            body = dc_qr.QRCODE_JS.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(body)
            return
        # DropZone's own host and guest pages are not part of DropCast.
        if path in ("/", "/remote"):
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
