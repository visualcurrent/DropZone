"""
dc_host.py - DropCast's additions on top of the UNEDITED DropZone core.

dz_host.py (shared with DropZone's app) starts and stops the server. This file
holds what only DropCast needs. Through PLAN.md > M2 step 2b that is one job:
putting a file the HOST shares into the core's file list, so the core's own
/api/download route can send it.

How a host file gets in (the "copy-in")
---------------------------------------
The Java side (CastService) does the heavy part, because only Java can read a
file handed over by another Android app:

  1. Java calls new_slot()            -> [fid, path]   an id and an empty path
  2. Java copies the shared file to that path, hashing it (MD5) as it goes
  3. Java calls register(fid, name, md5)

register() runs the same-file check: if a file with the same MD5 is already
held, the fresh copy is deleted and the existing file's id is returned, so one
file never gets two ids (and later, two QR codes).

Core names used here (ARCHITECTURE.md > Contracts, the Android list):
UPLOAD_DIR, shared_files, state_lock, get_or_create_user, fmt_size, log.
"""

import uuid
from pathlib import Path

import DropZone as dz   # already imported and configured by dz_host.start()

# The core files every shared file under a "user" keyed by a session id.
# Guests get theirs from the browser; the host's files, which never pass
# through a browser, are filed under this fixed one.
HOST_SID = "dropcast-host"


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
    """
    path = Path(dz.UPLOAD_DIR) / fid
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
            user["files"].append(entry)
            dz.shared_files[fid] = {**entry, "owner_id": HOST_SID, "owner_name": user["name"]}

    if existing is not None:
        path.unlink(missing_ok=True)          # FILE EFFECT: deletes the duplicate copy
        dz.log(f"copy-in: '{name}' {dz.fmt_size(size)} md5={md5} is already held as [{existing}]; duplicate deleted")
        return [existing, True]

    dz.log(f"copy-in saved: '{name}' [{fid}] {dz.fmt_size(size)} md5={md5}")
    return [fid, False]


def discard(fid):
    """Delete a copy that did not finish (copy failed or ran out of space)."""
    (Path(dz.UPLOAD_DIR) / fid).unlink(missing_ok=True)   # FILE EFFECT: deletes the partial copy
    dz.log(f"copy-in abandoned: [{fid}] partial file deleted")
