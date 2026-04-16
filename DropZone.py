#!/usr/bin/env python3
"""
DropZone - LAN File Sharing Server
Run: python3 DropZone.py
Then open http://localhost:7070 in your browser
"""

import os, sys, json, uuid, socket, re, shutil, tempfile, mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.parse

# ─── State ────────────────────────────────────────────────────────────────────
users        = {}
shared_files = {}
UPLOAD_DIR   = Path(tempfile.mkdtemp(prefix="dropzone_"))
PORT         = 7070

ADJECTIVES = ["Swift","Crimson","Golden","Silver","Azure","Jade","Amber","Coral","Indigo","Teal"]
ANIMALS    = ["Fox","Wolf","Hawk","Bear","Lynx","Deer","Crow","Orca","Ibis","Puma"]
import random

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP = get_local_ip()

def gen_name(): return random.choice(ADJECTIVES)+random.choice(ANIMALS)+str(random.randint(10,99))

def fmt_size(b):
    for u in ['B','KB','MB','GB']:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def get_or_create_user(sid):
    if sid not in users:
        users[sid] = {"name": gen_name(), "files": []}
    return users[sid]

# ─── Multipart parser ─────────────────────────────────────────────────────────
def parse_multipart(data, boundary):
    if isinstance(boundary, str): boundary = boundary.encode()
    parts = []
    for seg in data.split(b"--" + boundary)[1:]:
        if seg.startswith(b"--"): break
        seg = seg.lstrip(b"\r\n")
        if b"\r\n\r\n" not in seg: continue
        hdr_raw, body = seg.split(b"\r\n\r\n", 1)
        body = body.rstrip(b"\r\n")
        hdrs = {}
        for line in hdr_raw.decode(errors="replace").split("\r\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                hdrs[k.strip().lower()] = v.strip()
        parts.append((hdrs, body))
    return parts

def get_filename(cd):
    for pat in [r'filename\*=UTF-8\'\'(.+)', r'filename="([^"]+)"', r'filename=([^\s;]+)']:
        m = re.search(pat, cd)
        if m: return urllib.parse.unquote(m.group(1))
    return "upload"

# ─── HTTP Handler ─────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def get_session(self):
        for part in self.headers.get("Cookie","").split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                if k.strip() == "session": return v.strip()
        return ""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        if path in ("/", "/host"):  self.send_html(HOST_PAGE);   return
        if path == "/remote":       self.send_html(REMOTE_PAGE); return

        if path == "/api/state":
            sid  = self.get_session()
            user = get_or_create_user(sid) if sid else {"name":"?","files":[]}
            all_users = [
                {"name": u["name"], "files": u["files"], "is_me": sid2 == sid}
                for sid2, u in users.items() if u["files"]
            ]
            self.send_json({"session":sid,"user":user,"all_users":all_users,
                            "local_ip":LOCAL_IP,"port":PORT})
            return

        if path == "/api/download":
            fid = qs.get("id",[""])[0]
            if fid not in shared_files: self.send_json({"error":"Not found"},404); return
            f  = shared_files[fid]
            fp = Path(f["tmp_path"])
            if not fp.exists(): self.send_json({"error":"File missing"},404); return
            data = fp.read_bytes()
            fsafe = urllib.parse.quote(f["name"])
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(f["name"])[0] or "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{f["name"]}"; filename*=UTF-8\'\'{fsafe}')
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
            return

    def do_POST(self):
        path   = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        sid    = self.get_session()

        if path == "/api/session":
            if not sid: sid = str(uuid.uuid4())[:8]
            user = get_or_create_user(sid)
            resp = json.dumps({"session":sid,"user":user}).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",len(resp))
            self.send_header("Set-Cookie",f"session={sid}; Path=/; Max-Age=86400")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(resp)
            return

        if path == "/api/upload":
            ct = self.headers.get("Content-Type","")
            if "multipart/form-data" not in ct:
                self.send_json({"error":"Expected multipart"},400); return
            m = re.search(r'boundary=(.+)', ct)
            if not m: self.send_json({"error":"No boundary"},400); return
            boundary = m.group(1).strip()
            body  = self.rfile.read(length)
            parts = parse_multipart(body, boundary)
            if not sid: self.send_json({"error":"No session"},400); return
            user = get_or_create_user(sid)
            uploaded = []
            for hdrs, data in parts:
                cd = hdrs.get("content-disposition","")
                if "filename" not in cd: continue
                fname = get_filename(cd)
                fid   = str(uuid.uuid4())[:8]
                tmp   = UPLOAD_DIR / fid
                tmp.write_bytes(data)
                entry = {"id":fid,"name":fname,"tmp_path":str(tmp),
                         "size":len(data),"size_str":fmt_size(len(data))}
                user["files"].append(entry)
                shared_files[fid] = {**entry,"owner_id":sid,"owner_name":user["name"]}
                uploaded.append({"id":fid,"name":fname,"size_str":fmt_size(len(data))})
            self.send_json({"ok":True,"files":uploaded})
            return

        if path == "/api/rename":
            data = json.loads(self.rfile.read(length))
            if sid in users:
                users[sid]["name"] = data.get("name", users[sid]["name"])[:30]
                for f in shared_files.values():
                    if f["owner_id"] == sid: f["owner_name"] = users[sid]["name"]
            self.send_json({"ok":True,"name":users.get(sid,{}).get("name","")})
            return

        if path == "/api/remove_file":
            data = json.loads(self.rfile.read(length))
            fid  = data.get("id","")
            if sid in users:
                users[sid]["files"] = [f for f in users[sid]["files"] if f["id"] != fid]
            if fid in shared_files and shared_files[fid]["owner_id"] == sid:
                try: Path(shared_files[fid]["tmp_path"]).unlink(missing_ok=True)
                except: pass
                del shared_files[fid]
            self.send_json({"ok":True})
            return

        self.send_json({"error":"Not found"},404)


# ══════════════════════════════════════════════════════════════════════════════
#  FRONT-END
# ══════════════════════════════════════════════════════════════════════════════

CSS = """
:root,[data-theme="light"]{
  --bg:#f4f3ef; --surf:#f9f8f5; --surf2:#fdfcfa; --off:#edeae5;
  --border:#d4d1ca; --div:#dcd9d5;
  --txt:#28251d; --muted:#6b6a66; --hint:#7a7975;
  --pri:#01696f; --pri-h:#0c4e54; --pri-hl:rgba(1,105,111,.12);
  --err:#a12c7b; --err-bg:#fce8f4;
  --sh:0 2px 10px rgba(30,28,20,.09);
  --r:.5rem; --rx:.85rem; --rfull:9999px;
}
[data-theme="dark"]{
  --bg:#171614; --surf:#1c1b19; --surf2:#201f1d; --off:#27261f;
  --border:#383632; --div:#262422;
  --txt:#d0cfc9; --muted:#8a8880; --hint:#9e9c96;
  --pri:#4f98a3; --pri-h:#227f8b; --pri-hl:rgba(79,152,163,.14);
  --err:#d163a7; --err-bg:#2d1a28;
  --sh:0 2px 10px rgba(0,0,0,.35);
}
@media(prefers-color-scheme:dark){:root:not([data-theme]){
  --bg:#171614; --surf:#1c1b19; --surf2:#201f1d; --off:#27261f;
  --border:#383632; --div:#262422;
  --txt:#d0cfc9; --muted:#8a8880; --hint:#9e9c96;
  --pri:#4f98a3; --pri-h:#227f8b; --pri-hl:rgba(79,152,163,.14);
  --err:#d163a7; --err-bg:#2d1a28;
  --sh:0 2px 10px rgba(0,0,0,.35);
}}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:none;text-size-adjust:none}
body{min-height:100dvh;font-family:'Satoshi','Inter',system-ui,sans-serif;
  font-size:16px;color:var(--txt);background:var(--bg);line-height:1.5}
img,svg{display:block}
button,input,a{font:inherit;color:inherit}
button{cursor:pointer;background:none;border:none}

/* ── Header ── */
.hdr{
  background:var(--surf);border-bottom:1px solid var(--border);
  padding:10px 16px;
  display:flex;flex-direction:column;gap:3px;
  position:sticky;top:0;z-index:100;box-shadow:var(--sh);
}
.hdr-top{display:flex;align-items:center;gap:10px;width:100%}
.logo{display:flex;align-items:center;gap:8px;font-weight:700;
  font-size:1.05rem;color:var(--pri);text-decoration:none;flex-shrink:0}
.hdr-right{margin-left:auto;display:flex;align-items:center;gap:10px}

/* Tagline sits on its own line under the logo row */
.hdr-tagline{
  font-size:.75rem;color:var(--hint);line-height:1.3;
  padding-left:2px;
}

.badge{
  font-size:.68rem;padding:2px 8px;border-radius:var(--rfull);
  background:var(--pri-hl);color:var(--pri);font-weight:600;
  letter-spacing:.04em;flex-shrink:0;
}
.tt-btn{
  width:36px;height:36px;display:flex;align-items:center;justify-content:center;
  border-radius:var(--r);color:var(--muted);transition:background .15s,color .15s;
  flex-shrink:0;
}
.tt-btn:hover{background:var(--off);color:var(--txt)}

/* ── Layout ── */
.main{max-width:800px;margin:0 auto;padding:18px 14px;
  display:flex;flex-direction:column;gap:14px}

/* ── Card ── */
.card{background:var(--surf);border:1px solid var(--border);
  border-radius:var(--rx);overflow:hidden;box-shadow:var(--sh)}
.card-hdr{padding:9px 16px;border-bottom:1px solid var(--div);
  display:flex;align-items:center;gap:8px}
.card-title{font-size:.68rem;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em}
.card-body{padding:15px 16px}

/* ── Consistent hint/description text ── */
/* Used for ALL small descriptive text under inputs, under QR, etc. */
.hint{
  font-size:.78rem;
  color:var(--hint);   /* --hint is lighter than --muted, same in both themes */
  line-height:1.45;
  margin-top:6px;
}
.hint-top{   /* same style but margin above instead of below */
  font-size:.78rem;color:var(--hint);line-height:1.45;margin-bottom:8px;
}

/* ── Name row ── */
.name-row{display:flex;align-items:stretch;gap:8px;width:100%}
.name-inp{
  flex:1 1 0;min-width:0;
  padding:9px 12px;border:1px solid var(--border);border-radius:var(--r);
  background:var(--surf2);font-size:.9rem;
  transition:border-color .15s,box-shadow .15s;
}
.name-inp:focus{outline:none;border-color:var(--pri);
  box-shadow:0 0 0 3px var(--pri-hl)}
.btn-save{
  flex:0 0 auto;padding:9px 18px;border-radius:var(--r);
  font-size:.9rem;font-weight:600;background:var(--pri);color:#fff;
  transition:background .15s;white-space:nowrap;
}
.btn-save:hover{background:var(--pri-h)}

/* ── Drop zone ── */
.drop-zone{
  border:2px dashed var(--border);border-radius:var(--rx);
  padding:26px 16px;text-align:center;cursor:pointer;position:relative;
  transition:border-color .15s,background .15s;
}
.drop-zone:hover,.drop-zone.drag-over{border-color:var(--pri);background:var(--pri-hl)}
.drop-zone input[type=file]{
  position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
.drop-ico{font-size:2rem;margin-bottom:7px}
.drop-lbl{font-size:.9rem;font-weight:600;margin-bottom:3px}
.drop-sub{font-size:.78rem;color:var(--hint)}

/* ── Progress ── */
.prog-wrap{margin-top:11px;display:none;flex-direction:column;gap:5px}
.prog-wrap.on{display:flex}
.prog-track{background:var(--off);border-radius:var(--rfull);height:5px;overflow:hidden}
.prog-bar{height:100%;background:var(--pri);border-radius:var(--rfull);
  width:0%;transition:width .2s ease}
.prog-lbl{font-size:.75rem;color:var(--muted)}

/* ── Error ── */
.err-msg{display:none;font-size:.75rem;color:var(--err);
  background:var(--err-bg);padding:7px 12px;border-radius:var(--r);margin-top:7px}
.err-msg.on{display:block}

/* ── File list ── */
.file-list{display:flex;flex-direction:column;margin-top:12px}
.file-row{
  display:grid;
  grid-template-columns:28px 1fr 32px;
  grid-template-rows:auto auto;
  column-gap:8px;
  padding:8px 6px;
  border-radius:var(--r);
  transition:background .15s;
  align-items:start;
}
.file-row:hover{background:var(--off)}
.file-row+.file-row{border-top:1px solid var(--div)}
.f-ico{grid-column:1;grid-row:1/3;font-size:1.2rem;align-self:center;line-height:1;padding-top:1px}
.f-name{grid-column:2;grid-row:1;font-size:.88rem;font-weight:500;
  overflow-wrap:break-word;word-break:break-word;line-height:1.35}
.f-meta{grid-column:2;grid-row:2;font-size:.72rem;color:var(--hint);
  font-variant-numeric:tabular-nums;margin-top:2px}
.f-action{grid-column:3;grid-row:1/3;align-self:center;
  display:flex;align-items:center;justify-content:center}
.rm-btn{width:28px;height:28px;display:flex;align-items:center;justify-content:center;
  border-radius:var(--r);font-size:.75rem;color:var(--hint);
  transition:background .15s,color .15s}
.rm-btn:hover{background:#fde8e8;color:#c0392b}
[data-theme="dark"] .rm-btn:hover{background:#3d1f1f;color:#e07070}
.dl-btn{width:32px;height:32px;display:flex;align-items:center;justify-content:center;
  border-radius:var(--r);background:var(--pri-hl);color:var(--pri);
  font-size:1rem;font-weight:700;text-decoration:none;transition:background .15s,color .15s}
.dl-btn:hover{background:var(--pri);color:#fff}

/* ── User groups ── */
.user-group{border:1px solid var(--div);border-radius:var(--rx);
  overflow:hidden;margin-bottom:11px}
.user-group:last-child{margin-bottom:0}
.user-group.is-me{border-color:var(--pri)}
.u-hdr{display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--off)}
.u-av{width:28px;height:28px;border-radius:50%;background:var(--pri);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:.72rem;font-weight:700;flex-shrink:0}
.u-nm{font-size:.88rem;font-weight:600;flex:1;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.u-ct{font-size:.72rem;color:var(--hint);white-space:nowrap}
.u-files{padding:4px 8px}
.u-files .file-list{margin-top:0}

/* ── QR section ── */
.qr-wrap{display:flex;flex-direction:column;align-items:center;gap:10px}
.qr-box{background:#fff;padding:13px;border-radius:var(--rx);
  border:1px solid var(--border);display:inline-block}
.qr-url{font-size:.8rem;color:var(--pri);font-weight:500;
  text-align:center;word-break:break-all}
/* QR instruction line — bold action first */
.qr-action{font-size:.88rem;font-weight:600;color:var(--txt);text-align:center}
/* QR description line — lighter, consistent hint style */
.qr-desc{font-size:.78rem;color:var(--hint);text-align:center;line-height:1.45;
  max-width:28ch;margin:0 auto}

/* ── Empty ── */
.empty{color:var(--hint);font-size:.85rem;text-align:center;padding:22px 0}

@media(max-width:480px){
  .main{padding:12px 10px;gap:11px}
  .card-body{padding:12px}
}
"""

JS = """
const API = window.location.origin;
let session = '';

async function initSession(){
  const r = await fetch(`${API}/api/session`,{method:'POST',body:'{}'});
  const d = await r.json();
  session = d.session;
  const el = document.getElementById('username');
  if(el) el.value = d.user.name;
  startPolling();
}

async function fetchState(){
  const r = await fetch(`${API}/api/state`);
  return r.json();
}

function startPolling(){
  setInterval(async()=>{
    const s = await fetchState();
    renderMyFiles(s.user?.files||[]);
    renderAllUsers(s.all_users||[]);
  }, 2500);
}

function fileIcon(name){
  const ext=(name.split('.').pop()||'').toLowerCase();
  const m={
    pdf:'📄',
    jpg:'🖼',jpeg:'🖼',png:'🖼',gif:'🖼',webp:'🖼',svg:'🖼',heic:'🖼',heif:'🖼',raw:'🖼',
    mp4:'🎬',mov:'🎬',avi:'🎬',mkv:'🎬',webm:'🎬',m4v:'🎬',
    mp3:'🎵',flac:'🎵',wav:'🎵',aac:'🎵',m4a:'🎵',ogg:'🎵',opus:'🎵',
    zip:'🗜',rar:'🗜','7z':'🗜',tar:'🗜',gz:'🗜',bz2:'🗜',xz:'🗜',
    doc:'📝',docx:'📝',odt:'📝',rtf:'📝',
    xls:'📊',xlsx:'📊',ods:'📊',csv:'📊',
    ppt:'📋',pptx:'📋',odp:'📋',
    txt:'📃',md:'📃',log:'📃',
    json:'⚙',xml:'⚙',yaml:'⚙',yml:'⚙',toml:'⚙',ini:'⚙',cfg:'⚙',
    js:'💻',ts:'💻',py:'💻',html:'💻',css:'💻',sh:'💻',bat:'💻',
    apk:'📱',ipa:'📱',
    dmg:'💿',iso:'💿',exe:'⚙',msi:'⚙',deb:'⚙',rpm:'⚙',
  };
  return m[ext]||'📁';
}

function renderMyFiles(files){
  const el = document.getElementById('my-files');
  if(!el) return;
  if(!files.length){el.innerHTML='<p class="empty">No files shared yet.</p>';return;}
  el.innerHTML='<div class="file-list">'+files.map(f=>`
    <div class="file-row">
      <span class="f-ico">${fileIcon(f.name)}</span>
      <span class="f-name">${escHtml(f.name)}</span>
      <span class="f-meta">${f.size_str}</span>
      <span class="f-action">
        <button class="rm-btn" onclick="removeFile('${f.id}')" title="Remove">✕</button>
      </span>
    </div>`).join('')+'</div>';
}

function renderAllUsers(all_users){
  const el = document.getElementById('net-files');
  if(!el) return;
  if(!all_users.length){el.innerHTML='<p class="empty">No files on the network yet.</p>';return;}
  el.innerHTML=all_users.map(u=>`
    <div class="user-group${u.is_me?' is-me':''}">
      <div class="u-hdr">
        <div class="u-av">${escHtml(u.name[0].toUpperCase())}</div>
        <span class="u-nm">${escHtml(u.name)}${u.is_me?' <span style="color:var(--hint);font-weight:400">(you)</span>':''}</span>
        <span class="u-ct">${u.files.length} file${u.files.length!==1?'s':''}</span>
      </div>
      <div class="u-files"><div class="file-list">
        ${u.files.map(f=>`
          <div class="file-row">
            <span class="f-ico">${fileIcon(f.name)}</span>
            <span class="f-name">${escHtml(f.name)}</span>
            <span class="f-meta">${f.size_str}</span>
            <span class="f-action">
              <a class="dl-btn" href="${API}/api/download?id=${f.id}"
                 download="${escAttr(f.name)}" title="Download">↓</a>
            </span>
          </div>`).join('')}
      </div></div>
    </div>`).join('');
}

async function removeFile(id){
  await fetch(`${API}/api/remove_file`,{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  const s=await fetchState();
  renderMyFiles(s.user?.files||[]);
  renderAllUsers(s.all_users||[]);
}

async function renameUser(){
  const inp=document.getElementById('username');
  const name=inp.value.trim();
  if(!name) return;
  await fetch(`${API}/api/rename`,{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
  inp.blur();
}

async function uploadFiles(fileList){
  if(!fileList||!fileList.length) return;
  const prog=document.getElementById('upload-prog');
  const bar=document.getElementById('prog-bar');
  const lbl=document.getElementById('prog-lbl');
  const err=document.getElementById('upload-err');
  err.classList.remove('on');
  prog.classList.add('on');
  const fd=new FormData();
  Array.from(fileList).forEach(f=>fd.append('file',f,f.name));
  lbl.textContent=`Uploading ${fileList.length} file${fileList.length>1?'s':''}…`;
  let fake=0;
  const t=setInterval(()=>{if(fake<82){fake+=Math.random()*10;bar.style.width=fake+'%';}},180);
  try{
    const r=await fetch(`${API}/api/upload`,{method:'POST',body:fd});
    clearInterval(t);
    const d=await r.json();
    if(d.error){err.textContent=d.error;err.classList.add('on');}
    else{
      bar.style.width='100%';
      lbl.textContent=`✓ ${d.files.length} file${d.files.length>1?'s':''} shared!`;
      setTimeout(()=>{prog.classList.remove('on');bar.style.width='0%';},2200);
    }
    const s=await fetchState();
    renderMyFiles(s.user?.files||[]);
    renderAllUsers(s.all_users||[]);
  }catch(e){
    clearInterval(t);
    err.textContent='Upload failed: '+e.message;
    err.classList.add('on');
  }
  const fi=document.getElementById('file-input');
  if(fi) fi.value='';
}

function escHtml(s){
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s){return s.replace(/"/g,'&quot;');}

function initDragDrop(){
  const dz=document.getElementById('drop-zone');
  if(!dz) return;
  dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag-over')});
  dz.addEventListener('dragleave',()=>dz.classList.remove('drag-over'));
  dz.addEventListener('drop',e=>{
    e.preventDefault();dz.classList.remove('drag-over');uploadFiles(e.dataTransfer.files);
  });
}

function initTheme(){
  const btn=document.querySelector('[data-tt]');
  const root=document.documentElement;
  const SUN=`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>`;
  const MOON=`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
  let d=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
  root.setAttribute('data-theme',d);
  if(btn) btn.innerHTML=d==='dark'?SUN:MOON;
  btn&&btn.addEventListener('click',()=>{
    d=d==='dark'?'light':'dark';
    root.setAttribute('data-theme',d);
    btn.innerHTML=d==='dark'?SUN:MOON;
  });
}
"""

# ─── Reusable HTML blocks ─────────────────────────────────────────────────────

LOGO_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>
  <polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/>
</svg>"""

MOON_ICO = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2">
  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>"""

NAME_CARD = """
<div class="card">
  <div class="card-hdr"><span>👤</span><span class="card-title">Your Name</span></div>
  <div class="card-body">
    <div class="name-row">
      <input class="name-inp" id="username" type="text"
             placeholder="Display name" maxlength="30"
             onkeydown="if(event.key==='Enter')renameUser()">
      <button class="btn-save" onclick="renameUser()">Save</button>
    </div>
    <p class="hint">Others on the network see this name next to your files.</p>
  </div>
</div>
"""

UPLOAD_CARD = """
<div class="card">
  <div class="card-hdr"><span>📂</span><span class="card-title">Share Files</span></div>
  <div class="card-body">
    <div class="drop-zone" id="drop-zone">
      <input type="file" id="file-input" multiple accept="*/*"
             onchange="uploadFiles(this.files)">
      <div class="drop-ico">📁</div>
      <p class="drop-lbl">Tap to choose files</p>
      <p class="drop-sub">Desktop: drag &amp; drop &nbsp;·&nbsp; Any file type &nbsp;·&nbsp; Multiple OK</p>
    </div>
    <div class="prog-wrap" id="upload-prog">
      <div class="prog-track"><div class="prog-bar" id="prog-bar"></div></div>
      <span class="prog-lbl" id="prog-lbl">Uploading…</span>
    </div>
    <p class="err-msg" id="upload-err"></p>
    <div id="my-files"><p class="empty">No files shared yet.</p></div>
  </div>
</div>
"""

NET_CARD = """
<div class="card">
  <div class="card-hdr"><span>🌐</span><span class="card-title">Available on Network</span></div>
  <div class="card-body">
    <div id="net-files"><p class="empty">No files on the network yet.</p></div>
  </div>
</div>
"""

# QR card — used on host (top) and remote (bottom).
# show_invite=True uses warmer invite copy for the remote page's bottom placement.
def qr_card(show_invite=False):
    if show_invite:
        action = "Someone nearby? Show them this QR code."
        desc   = "They scan it with their phone camera and join instantly — no app needed."
    else:
        action = "Scan this QR code to join on your phone."
        desc   = "Opens right in your browser — share and download files with anyone in the room."
    return f"""
<div class="card">
  <div class="card-hdr"><span>📱</span>
    <span class="card-title">{"Invite Others" if show_invite else "Connect via QR Code"}</span>
  </div>
  <div class="card-body">
    <div class="qr-wrap">
      <div class="qr-box" id="qrcode{'_invite' if show_invite else ''}"></div>
      <p class="qr-url" id="remote-url{'_invite' if show_invite else ''}">Loading…</p>
      <p class="qr-action">{action}</p>
      <p class="qr-desc">{desc}</p>
    </div>
  </div>
</div>
"""

def make_page(badge, tagline, body, init_script):
    tagline_html = f'<span class="hdr-tagline">{tagline}</span>' if tagline else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>DropZone — {badge}</title>
<link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,600,700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<header class="hdr">
  <div class="hdr-top">
    <a href="/" class="logo">{LOGO_SVG} DropZone</a>
    <span class="badge">{badge}</span>
    <div class="hdr-right">
      <button class="tt-btn" data-tt aria-label="Toggle theme">{MOON_ICO}</button>
    </div>
  </div>
  {tagline_html}
</header>
<main class="main">
{body}
</main>
<script>
{JS}
{init_script}
</script>
</body>
</html>"""

# ─── Host page ────────────────────────────────────────────────────────────────
HOST_BODY = f"""
{qr_card(show_invite=False)}
{NAME_CARD}
{UPLOAD_CARD}
{NET_CARD}
"""

HOST_INIT = """
initTheme(); initDragDrop();
(async()=>{
  await initSession();
  const s = await fetchState();
  const url = `http://${s.local_ip}:${s.port}/remote`;
  document.getElementById('remote-url').textContent = url;
  new QRCode(document.getElementById('qrcode'),{
    text:url, width:200, height:200,
    colorDark:'#01696f', colorLight:'#ffffff',
    correctLevel:QRCode.CorrectLevel.M
  });
  renderMyFiles(s.user?.files||[]);
  renderAllUsers(s.all_users||[]);
})();
"""

# ─── Remote page ─────────────────────────────────────────────────────────────
REMOTE_TAGLINE = "Share &amp; download files with anyone on this WiFi"

REMOTE_BODY = f"""
{NAME_CARD}
{UPLOAD_CARD}
{NET_CARD}
{qr_card(show_invite=True)}
"""

REMOTE_INIT = """
initTheme(); initDragDrop();
(async()=>{
  await initSession();
  const s = await fetchState();
  const url = `http://${s.local_ip}:${s.port}/remote`;
  // populate both QR url labels (invite card at bottom)
  const urlEl = document.getElementById('remote-url_invite');
  if(urlEl) urlEl.textContent = url;
  new QRCode(document.getElementById('qrcode_invite'),{
    text:url, width:180, height:180,
    colorDark:'#01696f', colorLight:'#ffffff',
    correctLevel:QRCode.CorrectLevel.M
  });
  renderMyFiles(s.user?.files||[]);
  renderAllUsers(s.all_users||[]);
})();
"""

HOST_PAGE   = make_page("Host",   "",              HOST_BODY,   HOST_INIT)
REMOTE_PAGE = make_page("Remote", REMOTE_TAGLINE,  REMOTE_BODY, REMOTE_INIT)

# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n  ╔══════════════════════════════════════════╗")
    print(f"  ║         DropZone is running!             ║")
    print(f"  ╠══════════════════════════════════════════╣")
    print(f"  ║  Host page  →  http://localhost:{PORT}    ║")
    print(f"  ║  Remote URL →  http://{LOCAL_IP}:{PORT}/remote")
    print(f"  ╠══════════════════════════════════════════╣")
    print(f"  ║  Ctrl+C to stop (cleans up temp files)  ║")
    print(f"  ╚══════════════════════════════════════════╝\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopping — cleaning up uploads…")
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
        print("  Done. Goodbye.")
