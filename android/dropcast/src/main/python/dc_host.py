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

import hashlib
import html
import threading
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

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
.dc-prep.err{background:var(--err-bg);color:var(--err)}
.dc-got{border-color:var(--pri);padding:1.1rem 1rem;gap:.8rem}
.dc-gotrow{display:flex;align-items:center;gap:.8rem;width:100%}
.dc-gotpic{width:4rem;height:4rem;object-fit:cover;flex:none}
.dc-gotrow .dc-name{text-align:left;font-size:.98rem}
.dc-gotrow .dc-size{margin-top:.1rem}
.dc-bar{height:4px;border-radius:2px;margin-top:.6rem;background:var(--div);overflow:hidden}
.dc-bar i{display:block;height:100%;width:35%;border-radius:2px;background:var(--pri);
  animation:dc-slide 1.1s ease-in-out infinite alternate}
.dc-bar i.exact{animation:none;margin-left:0;transition:width .2s}
@keyframes dc-slide{from{margin-left:0}to{margin-left:65%}}
.dc-list{width:100%;display:flex;flex-direction:column;gap:.4rem}
.dc-list h2{font-size:.8rem;font-weight:600;color:var(--hint);text-transform:uppercase;letter-spacing:.04em}
.dc-row{display:flex;justify-content:space-between;gap:.75rem;width:100%;text-align:left;
  background:var(--surf2);border:1px solid var(--border);border-radius:var(--r);padding:.6rem .8rem;font-size:.9rem}
.dc-row span:first-child{overflow-wrap:anywhere}
.dc-row span:last-child{color:var(--hint);white-space:nowrap}
[hidden]{display:none!important}
.dc-lost .dc-live{display:none!important}
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
  <section id="fileCard" class="dc-frame dc-live">
    {picture}
    <div class="dc-name">{name}</div>
    <div class="dc-size">{f["size_str"]}</div>
    <a class="dc-btn" href="/api/download?id={fid}" download>Download</a>
  </section>
  <p class="dc-foot dc-live">Stay on this WiFi until the download finishes.</p>
  <script>var PAGE_FID = '{fid}';</script>
""" + _SHARE_HTML)


# The "Share a file" part of the guest page (PLAN M2 step 5): the guest picks
# one file, it uploads to the host's phone with a progress bar, and the guest
# then gets a QR for it. A plain string (not an f-string), with NO backslashes
# in the script, so Python passes it to the browser exactly as typed.
_SHARE_HTML = """
  <div id="goneNote" class="dc-prep err" hidden>This file is no longer being shared.</div>
  <div id="lost" class="dc-prep err" hidden><b>Can't reach the host's phone.</b><br>
    They may have stopped sharing, or you may have left their WiFi.</div>
  <section id="mine" class="dc-frame dc-live" hidden>
    <p class="dc-note"><b>Your file is ready to share.</b><br>Anyone on this WiFi can scan this code to download it.</p>
    <div id="myName" class="dc-name"></div>
    <div id="mySize" class="dc-size"></div>
    <div id="qr" class="dc-qr"></div>
    <div id="myUrl" class="dc-url"></div>
  </section>
  <div id="up" class="dc-prep" hidden><span id="upText"></span><div class="dc-bar"><i id="upBar"></i></div></div>
  <button id="share" class="dc-btn2 dc-live">Share a file</button>
  <input id="pick" type="file" hidden>
  <p class="dc-foot dc-live">Your file is sent to the phone that is hosting, and stays there until that person stops sharing.</p>
  <script src="/dc/qrcode.js"></script>
  <script>
var $ = function(id){ return document.getElementById(id); };
var busy = false;
var myId = '';       // id of this guest's own shared file whose QR is on show, '' when none
var misses = 0;      // checks in a row that got no answer from the host's phone

// ── Is the host still there? ─────────────────────────────────────────────────
// A page cannot be told that the host stopped: the host's phone only ever
// answers questions. So this page asks, every 5 seconds, whether the file it
// shows (PAGE_FID) and this guest's own shared file (myId) are still held.
//   answer "no"          -> that file is gone for good: remove its card and QR
//   no answer, 3 in a row -> hide everything that needs the host and say so;
//                            if the host answers again, it all comes back
// Everything that needs the host carries the class dc-live; putting the class
// dc-lost on the page hides all of it at once.
function check(){
  if (busy) return;                      // an upload is running; it reports its own failures
  var stop = new AbortController();      // lets us give up on a question after 4 s
  var timer = setTimeout(function(){ stop.abort(); }, 4000);
  fetch('/dc/alive?id=' + PAGE_FID + '&mine=' + myId, {cache: 'no-store', signal: stop.signal})
    .then(function(r){ return r.json(); })
    .then(function(s){
      clearTimeout(timer);
      misses = 0;
      document.body.classList.remove('dc-lost');
      $('lost').hidden = true;
      if (PAGE_FID && !s.file){          // the file this page offers is no longer held
        var card = $('fileCard');
        if (card){ card.parentNode.removeChild(card); $('goneNote').hidden = false; }
      }
      if (myId && !s.mine){              // this guest's own file is no longer held
        myId = '';
        $('mine').hidden = true;
        $('qr').innerHTML = '';
        $('share').textContent = 'Share a file';
      }
    })
    .catch(function(){
      clearTimeout(timer);
      misses++;
      if (misses >= 3){
        document.body.classList.add('dc-lost');
        $('lost').hidden = false;
      }
    });
}
setInterval(check, 5000);
// Phone browsers pause timers in a tab that is not on screen, so ask again the
// moment the page is brought back into view.
document.addEventListener('visibilitychange', function(){ if (!document.hidden) check(); });

// Show the QR card for one of this guest's own files.
function showMine(f){
  myId = f.id;
  var url = location.origin + '/f/' + f.id;
  $('myName').textContent = f.name;      // textContent: a file name is never treated as HTML
  $('mySize').textContent = f.size_str;
  $('myUrl').textContent = url;
  $('qr').innerHTML = '';
  new QRCode($('qr'), {text: url, width: 220, height: 220,
                       colorDark: '#000000', colorLight: '#ffffff',
                       correctLevel: QRCode.CorrectLevel.M});
  $('mine').hidden = false;
  $('share').textContent = 'Share another file';
}

// The progress box. pct = 0..100 for a real percentage, null for "working".
function progress(text, pct){
  $('up').hidden = false;
  $('up').className = 'dc-prep';
  $('upText').textContent = text;
  var bar = $('upBar');
  if (pct === null){ bar.className = ''; bar.style.width = ''; }
  else { bar.className = 'exact'; bar.style.width = pct + '%'; }
}
function failed(why){
  busy = false;
  $('up').hidden = false;
  $('up').className = 'dc-prep err';
  $('upText').textContent = 'That did not work: ' + why + '. Please try again.';
  $('upBar').className = 'exact'; $('upBar').style.width = '0%';
}

function upload(file){
  busy = true;
  progress('Sending ' + file.name + ' ... 0%', 0);
  // 1. the host's server gives this browser an id (a cookie) so the file is filed under it
  fetch('/api/session', {method: 'POST'}).then(function(){
    // 2. send the file. XMLHttpRequest is used because it reports upload progress.
    var fd = new FormData();
    fd.append('file', file, file.name);
    var x = new XMLHttpRequest();
    x.open('POST', '/api/upload');
    x.upload.onprogress = function(e){
      if (!e.lengthComputable) return;
      var pct = Math.floor(100 * e.loaded / e.total);
      progress('Sending ' + file.name + ' ... ' + pct + '%', pct);
    };
    x.onerror = function(){ failed('the connection to the host was lost'); };
    x.onload = function(){
      var r = null;
      try { r = JSON.parse(x.responseText); } catch (e) {}
      if (x.status !== 200 || !r || !r.files || !r.files.length){ failed('the host did not accept the file'); return; }
      // 3. the host checks the file (and whether it already holds the same one)
      progress('Preparing ' + file.name + ' ...', null);
      fetch('/dc/claim?id=' + r.files[0].id, {method: 'POST'})
        .then(function(c){ if (!c.ok) throw 0; return c.json(); })
        .then(function(f){ busy = false; $('up').hidden = true; showMine(f); window.scrollTo(0, document.body.scrollHeight); })
        .catch(function(){ failed('the host could not prepare the file'); });
    };
    x.send(fd);
  }).catch(function(){ failed('the host could not be reached'); });
}

$('share').onclick = function(){ if (!busy) $('pick').click(); };
$('pick').onchange = function(){
  var f = this.files && this.files[0];
  this.value = '';                 // so picking the same file again still fires
  if (f) upload(f);
};

// On opening (or reloading) the page: if this browser already shared
// something in this session, show its newest file's QR again.
fetch('/dc/mine').then(function(r){ return r.json(); }).then(function(s){
  if (s.files.length) showMine(s.files[s.files.length - 1]);
}).catch(function(){});
  </script>"""


def landing_page():
    """The page behind the host's "receive a file" QR: no file to download,
    only the "Share a file" part, so a guest can send one to the host."""
    return _page("DropCast", """
  <p class="dc-note"><b>Send a file to the person who showed you this code.</b><br>
    It goes straight to their phone over this WiFi. Nothing goes through the internet.</p>
  <script>var PAGE_FID = '';</script>
""" + _SHARE_HTML)


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
# What only the app can do is reached through "Android", an object the app
# adds to the page (MainActivity.Bridge):
#   Android.status()            -> progress line of a copy-in or a save, "" when idle
#   Android.problem()           -> last failure to tell the host about, "" when none
#   Android.clearProblem()      -> the host tapped OK on it
#   Android.batteryRestricted() -> true while the phone may pause the app
#   Android.openAppSettings()   -> open this app's page in the phone's Settings
#   Android.chooseFile()        -> open Android's file picker
#   Android.save(id)            -> save a received file through Android's save dialog
#   Android.stop()              -> stop DropCast (asks first if files are unsaved)

# The page's script. A plain (non-f) Python string, and written with NO
# backslashes, so Python passes it to the browser exactly as typed.
_HOST_JS = """
var files = [];        // the host's shared files, oldest first (from /dc/host_state)
var base = '';         // http://<phone's WiFi address>:<port>
var shownId = null;    // id of the file whose QR is on screen
var picked = null;     // id the host tapped in "Earlier files"; null = newest
var recvBase = '';     // address the "receive a file" QR was drawn for
var $ = function(id){ return document.getElementById(id); };

function draw(){
  var f = null;
  for (var i = 0; i < files.length; i++) if (files[i].id === picked) f = files[i];
  if (!f && files.length) f = files[files.length - 1];      // default: the newest share

  $('empty').hidden = !!f;
  $('card').hidden = !f;

  // Nothing shared yet: show a QR that lets someone SEND a file to this phone
  // (it opens the landing page, which has only the "Share a file" button).
  $('recv').hidden = !!f || !base;
  if (!f && base && recvBase !== base){
    recvBase = base;
    $('recvUrl').textContent = base + '/';
    $('recvQr').innerHTML = '';
    new QRCode($('recvQr'), {text: base + '/', width: 220, height: 220,
                             colorDark: '#000000', colorLight: '#ffffff',
                             correctLevel: QRCode.CorrectLevel.M});
  }
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

// Files guests have shared with the host: one small card each, newest first,
// with a Download button that opens Android's "save to" dialog.
var gotKey = '';       // what is drawn now, so the cards are rebuilt only on a change
function drawReceived(list){
  var key = JSON.stringify(list);
  if (key === gotKey) return;
  gotKey = key;
  var box = $('got'); box.innerHTML = '';
  for (var i = list.length - 1; i >= 0; i--){
    var f = list[i];
    var card = document.createElement('section'); card.className = 'dc-frame dc-got';
    var note = document.createElement('p'); note.className = 'dc-note';
    var b = document.createElement('b');
    b.textContent = f.saved ? 'Saved to this phone.' : 'This file has been shared with you.';
    note.appendChild(b);
    var row = document.createElement('div'); row.className = 'dc-gotrow';
    var ic;                // the picture: the file's thumbnail, or an icon for its kind
    if (f.thumb){
      ic = document.createElement('img'); ic.className = 'dc-thumb dc-gotpic'; ic.alt = '';
      ic.src = '/api/thumb?id=' + f.id;
    } else {
      ic = document.createElement('div'); ic.className = 'dc-icon small'; ic.textContent = f.icon;
    }
    var tx = document.createElement('div');
    var nm = document.createElement('div'); nm.className = 'dc-name'; nm.textContent = f.name;
    var sz = document.createElement('div'); sz.className = 'dc-size'; sz.textContent = f.size_str;
    tx.appendChild(nm); tx.appendChild(sz); row.appendChild(ic); row.appendChild(tx);
    var btn = document.createElement('button');
    btn.className = f.saved ? 'dc-btn2' : 'dc-btn';
    btn.textContent = f.saved ? 'Save again' : 'Download';
    btn.onclick = (function(id){ return function(){ if (window.Android) Android.save(id); }; })(f.id);
    card.appendChild(note); card.appendChild(row); card.appendChild(btn);
    box.appendChild(card);
  }
  $('gotBox').hidden = (list.length === 0);
}

// Files on their way in from guests: one progress box per upload, and one box
// while arrived files are being checked. Redrawn every tick (once a second).
function drawIncoming(list, checking){
  var box = $('inBox'); box.innerHTML = '';
  var mb = function(n){ return Math.floor(n / 1048576) + ' MB'; };
  var add = function(text, pct){
    var d = document.createElement('div'); d.className = 'dc-prep';
    var t = document.createElement('span'); t.textContent = text;
    var bar = document.createElement('div'); bar.className = 'dc-bar';
    var fill = document.createElement('i');
    if (pct !== null){ fill.className = 'exact'; fill.style.width = pct + '%'; }
    bar.appendChild(fill); d.appendChild(t); d.appendChild(bar); box.appendChild(d);
  };
  for (var i = 0; i < list.length; i++){
    var r = list[i];
    var pct = r.total > 0 ? Math.min(100, Math.floor(100 * r.done / r.total)) : 0;
    add('Receiving a file from a guest: ' + mb(r.done) + ' of ' + mb(r.total) + ' (' + pct + '%)', pct);
  }
  if (checking > 0) add(checking === 1 ? 'Checking a received file ...' : 'Checking ' + checking + ' received files ...', null);
  box.hidden = (list.length === 0 && checking === 0);
}

function tick(){
  // 1. straight from the app: the progress line (copy-in or save), the last
  //    problem to tell the host about, and whether the phone restricts the app
  var st = (window.Android && Android.status()) || '';
  $('prep').hidden = !st;
  $('prepText').textContent = st;
  var pr = (window.Android && Android.problem()) || '';
  $('prob').hidden = !pr;
  $('probText').textContent = pr;
  $('batt').hidden = !(window.Android && Android.batteryRestricted());

  // 2. the file list, from the server on this phone
  fetch('/dc/host_state').then(function(r){ return r.json(); }).then(function(s){
    var newest = function(a){ return a.length ? a[a.length - 1].id : ''; };
    if (newest(s.files) !== newest(files)) picked = null;   // a new share takes over the screen
    files = s.files; base = s.base;
    draw();
    drawIncoming(s.incoming, s.checking);
    drawReceived(s.received);
  }).catch(function(){ /* server stopping or starting: try again next tick */ });
}

$('battBtn').onclick = function(){ if (window.Android) Android.openAppSettings(); };
$('probBtn').onclick = function(){ if (window.Android) Android.clearProblem(); $('prob').hidden = true; };
$('choose').onclick = function(){ if (window.Android) Android.chooseFile(); };
$('stop').onclick = function(){ if (window.Android) Android.stop(); };
tick();
setInterval(tick, 1000);
"""


def host_page():
    """The host's screen: the shared file with its QR, Choose a file, Stop."""
    inner = """
  <div id="batt" class="dc-prep err" hidden><b>This phone may pause DropCast.</b><br>
    Downloads stall when it does. In App info, set the battery or power option to No restrictions.
    <button id="battBtn" class="dc-btn2 dc-stop" style="margin-top:.7rem">Open settings</button></div>
  <div id="prob" class="dc-prep err" hidden><span id="probText"></span>
    <button id="probBtn" class="dc-btn2 dc-stop" style="margin-top:.7rem">OK</button></div>
  <div id="prep" class="dc-prep" hidden><span id="prepText"></span><div class="dc-bar"><i></i></div></div>
  <div id="inBox" class="dc-list" hidden></div>
  <div id="gotBox" class="dc-list" hidden><h2>Shared with you</h2><div id="got" class="dc-list"></div></div>
  <p id="empty" class="dc-note"><b>Share a file with people nearby.</b><br>
    Choose a file here, or use Share in any app and pick DropCast.</p>
  <section id="recv" class="dc-frame" hidden>
    <p class="dc-note"><b>Want a file from someone?</b><br>They scan this code and send it to you. No app needed.</p>
    <div id="recvQr" class="dc-qr"></div>
    <div id="recvUrl" class="dc-url"></div>
  </section>
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
    return _page("DropCast", inner)


def host_state():
    """What the host's screen needs.

    files:    the host's own shares, oldest first (each gets a QR).
    received: files guests have shared, oldest first (no QR; the host saves
              them). A guest's file appears only once it has been claimed
              (hashed), so an upload that turns out to be a duplicate never
              flashes up and vanishes.
    """
    with dz.state_lock:
        mine = list(dz.users.get(HOST_SID, {}).get("files", []))
        got = [f for f in dz.shared_files.values()       # dicts keep insertion order: oldest first
               if f.get("owner_id") != HOST_SID and f.get("md5")]
        checking = _checking_count()
    with _incoming_lock:
        incoming = [dict(r) for r in _incoming.values()]   # copies, so the reply is a fixed snapshot
    return {
        # incoming: uploads arriving right now; checking: arrived, being hashed.
        "incoming": incoming,
        "checking": checking,
        "base": f"http://{dz.LOCAL_IP}:{dz.PORT}",
        "files": [{"id": f["id"], "name": f["name"], "size_str": f["size_str"],
                   "thumb": bool(f.get("thumb")), "icon": _icon(f["name"])} for f in mine],
        "received": [{"id": f["id"], "name": f["name"], "size_str": f["size_str"],
                      "icon": _icon(f["name"]), "thumb": bool(f.get("thumb")),
                      "saved": bool(f.get("saved"))} for f in got],
    }


# ─── Saving a received file (called from Java: MainActivity / SaveOut) ────────

def file_info(fid):
    """[name, path, size] of a held file, for Java to copy it out; None if not held."""
    with dz.state_lock:
        f = dz.shared_files.get(fid)
        return [f["name"], f["tmp_path"], f["size"]] if f else None


def mark_saved(fid):
    """Record that the host has saved a received file (the Stop warning counts the rest)."""
    with dz.state_lock:
        if fid in dz.shared_files:
            dz.shared_files[fid]["saved"] = True
    dz.log(f"host saved [{fid}] out of the app")


def stop_check():
    """What the host would lose by stopping now: [unsaved, arriving].

    unsaved:  received files, complete, that the host has not saved.
    arriving: files still uploading, plus files that have arrived but are
              still being checked.
    """
    with dz.state_lock:
        unsaved = sum(1 for f in dz.shared_files.values()
                      if f.get("owner_id") != HOST_SID and f.get("md5") and not f.get("saved"))
        checking = _checking_count()
    with _incoming_lock:
        arriving = len(_incoming) + checking
    return [unsaved, arriving]


# ─── Uploads on their way in ──────────────────────────────────────────────────
# The core's /api/upload does the receiving, and tells nobody until it is done.
# To let the host SEE a file arriving (and be warned about it at Stop),
# CastHandler.do_POST hands the core a reader that counts the bytes as the core
# reads them. One record per upload in progress.
_incoming = {}                       # key -> {"total": bytes expected, "done": bytes read so far}
_incoming_lock = threading.Lock()


class _CountingReader:
    """Stands in for a request's input stream and counts what is read from it.

    The core's upload code reads the body only through read(n) (ARCHITECTURE
    contract 7), so that is the one method counted; anything else is passed
    straight through to the real stream by __getattr__.
    """

    def __init__(self, raw, rec):
        self._raw = raw
        self._rec = rec

    def read(self, n=-1):
        data = self._raw.read(n)
        self._rec["done"] += len(data)
        return data

    def __getattr__(self, name):     # called only for names not defined above
        return getattr(self._raw, name)


def _checking_count():
    """Guests' files that have arrived but are not yet claimed (hashed). Call with state_lock held."""
    return sum(1 for f in dz.shared_files.values()
               if f.get("owner_id") != HOST_SID and not f.get("md5"))


def _md5_of(path):
    """Hex MD5 of a file, read 1 MB at a time so memory stays flat at any size."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _make_thumb(path, name):
    """Make the thumbnail for a file a GUEST uploaded. Returns True if one now exists.

    A host's file gets its thumbnail in Java during the copy-in. A guest's file
    arrives through the core's upload route, which Java never sees, so Python
    asks Java for the same job here: CopyIn.makeThumb writes "<path>.t", the
    core's thumbnail slot. ("from java import jclass" is Chaquopy's way to
    call the app's Java code from Python.)

    Any failure only means the page shows an icon instead.
    """
    try:
        from java import jclass
        note = jclass("com.visualcurrent.dropcast.CopyIn").makeThumb(jclass("java.io.File")(path), name)
        dz.log(f"guest thumb for '{name}': {note}")
    except Exception as e:
        dz.log(f"guest thumb for '{name}' FAILED: {e!r}")
    return Path(path + ".t").exists()


# One record per guest upload whose check has been started:
#   fid -> {"sid": owner's session id, "done": threading.Event, "result": dict or None}
# The check is started by the HOST'S phone itself the moment an upload has
# arrived (CastHandler.do_POST), so a guest who closes their browser straight
# after uploading cannot leave the file unchecked. The guest's page still asks
# (POST /dc/claim) because it needs the RESULT for its QR; that request finds
# the record here and waits on "done" instead of hashing the file a second time.
_claims = {}
_claims_lock = threading.Lock()


def claim(fid, sid):
    """Check a GUEST's upload once, and give every caller the same result.

    Called twice per upload in the normal case: by the host's phone as soon as
    the upload has arrived, and by the guest's page asking for the result.
    Whichever comes first does the work (_check_upload); the other waits for it.

    Returns the file's public details as a dict, or None when fid is not an
    upload of this guest (or the check failed, e.g. Stop was tapped meanwhile).
    """
    if not sid:
        return None
    with _claims_lock:
        c = _claims.get(fid)
        first = c is None
        if first:
            # Only the owner may start a check, so nobody else can fill this
            # record with a refusal before the owner asks.
            with dz.state_lock:
                f = dz.shared_files.get(fid)
                owned = bool(f) and f.get("owner_id") == sid
            if not owned:
                return None
            c = _claims[fid] = {"sid": sid, "done": threading.Event(), "result": None}
    if c["sid"] != sid:
        return None
    if first:
        try:
            c["result"] = _check_upload(fid, sid)
        except Exception as e:           # e.g. the file was deleted by Stop mid-hash
            dz.log(f"claim FAILED [{fid}]: {e!r}")
        finally:
            c["done"].set()              # release anyone waiting, whatever happened
    else:
        c["done"].wait()                 # Event.wait(): sleeps until set() is called
    return c["result"]


def _check_upload(fid, sid):
    """The work of a claim: hash the upload and run the same-file check.

    The core's /api/upload has already saved the file and listed it under the
    guest (session id sid). This adds the MD5 and, when an identical file is
    already held by anyone, removes the new upload and answers with the
    existing file instead, so one file never gets two addresses.

    Returns the file's public details as a dict, or None when fid is not an
    upload of this guest.

    FILE EFFECTS: on a match, deletes the just-uploaded copy and its thumbnail.
    """
    with dz.state_lock:
        f = dz.shared_files.get(fid)
        if not f or f.get("owner_id") != sid or not sid:
            return None
        path, size = f["tmp_path"], f["size"]

    md5 = _md5_of(path)        # slow for a big file (seconds per GB), so done outside the lock
    has_thumb = _make_thumb(path, f["name"])   # before the file is listed, so its card never appears without it

    with dz.state_lock:
        match = None
        for other in dz.shared_files.values():
            if other["id"] != fid and other.get("md5") == md5 and other["size"] == size:
                match = other
                break
        if match is None:
            # The core keeps two copies of an entry (one in the file list, one
            # in the owner's list); mark both.
            marks = {"md5": md5}
            if has_thumb:
                marks["thumb"] = True     # same flag the core sets after POST /api/thumb
            dz.shared_files[fid].update(marks)
            for e in dz.users.get(sid, {}).get("files", []):
                if e["id"] == fid:
                    e.update(marks)
            keep = dz.shared_files[fid]
        else:
            del dz.shared_files[fid]
            mine = dz.users.get(sid, {}).get("files", [])
            mine[:] = [e for e in mine if e["id"] != fid]    # slice assignment: edits the list in place
            keep = match

    if match is not None:
        Path(path).unlink(missing_ok=True)
        Path(path + ".t").unlink(missing_ok=True)
        dz.log(f"claim: '{f['name']}' {dz.fmt_size(size)} md5={md5} is already held as [{keep['id']}]; upload [{fid}] deleted")
    else:
        dz.log(f"claim: '{f['name']}' [{fid}] {dz.fmt_size(size)} md5={md5}")
    return {"id": keep["id"], "name": keep["name"], "size_str": keep["size_str"], "reused": match is not None}


def my_files(sid):
    """A guest's own finished shares, oldest first (for the guest page on reload)."""
    with dz.state_lock:
        mine = list(dz.users.get(sid, {}).get("files", [])) if sid else []
    return {"files": [{"id": f["id"], "name": f["name"], "size_str": f["size_str"]}
                      for f in mine if f.get("md5")]}


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
        # A guest page's 5-second question: are these two files still held?
        # Not logged: it arrives every few seconds from every open guest page.
        if path == "/dc/alive":
            q = parse_qs(urlparse(self.path).query)
            self.send_json({"file": q.get("id", [""])[0] in dz.shared_files,
                            "mine": q.get("mine", [""])[0] in dz.shared_files})
            return
        # A guest's own shares, so a reloaded guest page can show its QR again.
        if path == "/dc/mine":
            self.send_json(my_files(self.get_session()))
            return
        # The address behind the host's "receive a file" QR.
        if path == "/":
            self._send_page(landing_page(), 200)
            return
        # DropZone's own guest page is not part of DropCast.
        if path == "/remote":
            self._send_page(gone_page(), 404)
            return
        # A Download tapped on a page left open from an earlier session: the
        # file is gone. Say so as a page; the core would answer with raw JSON.
        if path == "/api/download":
            if parse_qs(urlparse(self.path).query).get("id", [""])[0] not in dz.shared_files:
                self._send_page(gone_page(), 404)
                return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/dc/claim":
            fid = parse_qs(parsed.query).get("id", [""])[0]
            result = claim(fid, self.get_session())
            if result is None:
                self.send_json({"error": "Not your upload"}, 403)
            else:
                self.send_json(result)
            return
        if parsed.path == "/api/upload":
            # The core receives the file; we only count the bytes going past
            # so the host's screen can show it arriving.
            rec = {"total": int(self.headers.get("Content-Length", 0)), "done": 0}
            with _incoming_lock:
                _incoming[id(rec)] = rec
            sid = self.get_session()
            with dz.state_lock:
                before = set(dz.shared_files)        # ids held before this upload
            raw = self.rfile
            self.rfile = _CountingReader(raw, rec)
            try:
                super().do_POST()
            finally:                 # runs whether the upload finished or failed
                self.rfile = raw
                with _incoming_lock:
                    _incoming.pop(id(rec), None)
            # Start the check of what just arrived, here on the host's phone,
            # without waiting for the guest's page to ask (it may never ask).
            # A separate thread, so this request can end while a big file is
            # still being hashed.
            with dz.state_lock:
                arrived = [fid for fid, f in dz.shared_files.items()
                           if fid not in before and f.get("owner_id") == sid]
            for fid in arrived:
                threading.Thread(target=claim, args=(fid, sid),
                                 name="dropcast-claim", daemon=True).start()
            return
        super().do_POST()      # /api/session and the rest: the core's own code

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

    Python keeps running inside the app between a Stop and the next start, so
    the records of the previous session are emptied here too.
    """
    dz.Handler = CastHandler
    with _claims_lock:
        _claims.clear()
    with _incoming_lock:
        _incoming.clear()
