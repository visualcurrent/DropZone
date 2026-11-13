package com.visualcurrent.dropcast;

import android.content.Context;
import android.graphics.Bitmap;
import android.media.ThumbnailUtils;
import android.net.Uri;
import android.os.Build;
import android.util.Size;
import android.webkit.MimeTypeMap;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The "copy-in" (PLAN.md > M2 step 2b): copies a file the host shared into
 * the app's own storage and hands it to the server.
 *
 * Why a copy: another app lends DropCast the file as a content:// reference,
 * and the DropZone core can only send a file that has a real path. Serving the
 * original in place is UNEXPLORED_IDEAS U5.
 *
 * Steps for one file (all on one background thread, one file at a time):
 *   1. wait for the server to be up (it owns the folder the copy goes into)
 *   2. check there is room for the copy
 *   3. ask Python (dc_host.new_slot) for an id and a path
 *   4. copy the bytes, feeding each block to an MD5 hash on the way past
 *   5. hand over to Python (dc_host.register), which either lists the file or,
 *      when an identical file is already held, deletes this copy and returns
 *      the existing id
 *
 * FILE EFFECTS: writes files/uploads/<id> in the app's private storage; a
 * failed or duplicate copy is deleted again.
 */
public final class CopyIn {   // public (with makeThumb) so dc_host.py can call it for guests' files

    /** Progress line for the screen, "" when no copy is running. */
    static volatile String status = "";

    // One worker thread: a second share waits for the first to finish.
    private static final ExecutorService worker = Executors.newSingleThreadExecutor();

    private static final int BLOCK = 1024 * 1024;   // copy 1 MB at a time; memory use stays flat
    private static final int THUMB_PX = 320;        // thumbnail's longer side, same as DropZone's browser-made ones

    private CopyIn() {}

    /**
     * Queue one shared file for copy-in.
     *
     * Call from the screen's thread while the screen still holds Android's
     * permission to read the file: the file is OPENED here, straight away, and
     * an open file stays readable even if the screen is closed mid-copy.
     *
     * size: bytes as stated by the sending app, or -1 when it did not say.
     */
    static void start(Context appCtx, Uri uri, String name, long size) {
        final InputStream in;
        try {
            in = appCtx.getContentResolver().openInputStream(uri);
            if (in == null) throw new java.io.IOException("the sending app returned no data");
        } catch (Exception e) {
            Report.add(appCtx, "copy-in FAILED at open: '" + name + "': " + e);
            Report.problem = "Could not share '" + name + "': the file could not be opened.";
            return;
        }
        worker.execute(() -> run(appCtx, in, name, size));
    }

    private static void run(Context ctx, InputStream in, String name, long size) {
        String fid = null;          // set once Python has given us a slot
        PyObject dc = null;
        try (InputStream src = in) {   // try-with-resources: closes the file however we leave
            // --- 1. wait for the server (up to 20 s) --------------------------
            status = "Preparing '" + name + "': waiting for the server";
            for (int i = 0; i < 100 && !CastService.running; i++) Thread.sleep(200);
            if (!CastService.running) throw new IllegalStateException("the server is not running");

            // --- 2. room for the copy? ----------------------------------------
            // Only possible when the sending app stated a size.
            long free = ctx.getFilesDir().getUsableSpace();
            if (size > 0 && size > free) {
                throw new IllegalStateException("not enough space: the file is " + mb(size)
                        + ", the phone has " + mb(free) + " free");
            }

            // --- 3. an id and a path from Python ------------------------------
            dc = Python.getInstance().getModule("dc_host");
            List<PyObject> slot = dc.callAttr("new_slot").asList();
            fid = slot.get(0).toString();
            File dest = new File(slot.get(1).toString());

            // --- 4. copy and hash ---------------------------------------------
            MessageDigest md5 = MessageDigest.getInstance("MD5");
            byte[] block = new byte[BLOCK];
            long done = 0;
            long t0 = System.nanoTime();
            long lastShown = 0;
            try (OutputStream out = new FileOutputStream(dest)) {
                int n;
                while ((n = src.read(block)) > 0) {
                    out.write(block, 0, n);
                    md5.update(block, 0, n);
                    done += n;
                    // Refresh the progress line about four times a second.
                    long now = System.nanoTime();
                    if (now - lastShown > 250_000_000L) {
                        lastShown = now;
                        status = "Preparing '" + name + "': " + mb(done)
                                + (size > 0 ? " of " + mb(size) + " (" + (100 * done / size) + "%)" : "");
                    }
                }
            }
            double secs = (System.nanoTime() - t0) / 1e9;

            // --- 4b. thumbnail for the guest page -----------------------------
            // A failure here never fails the share: the page shows an icon.
            status = "Preparing '" + name + "': making the thumbnail";
            String thumbNote = makeThumb(dest, name);

            // --- 5. hand over -------------------------------------------------
            String hex = hex(md5.digest());
            List<PyObject> res = dc.callAttr("register", fid, name, hex).asList();
            String useFid = res.get(0).toString();
            boolean reused = res.get(1).toBoolean();

            String rate = secs > 0 ? String.format(Locale.US, "%.0f MB/s", done / 1048576.0 / secs) : "-";
            Report.add(ctx, (reused ? "copy-in REUSED existing file" : "copy-in done") + ": '" + name + "' id=" + useFid
                    + " bytes=" + done + " md5=" + hex
                    + String.format(Locale.US, " copy=%.1f s (%s)", secs, rate)
                    + " thumb=" + thumbNote
                    + "\nguest page: " + CastService.baseUrl + "/f/" + useFid);
        } catch (Throwable t) {
            Report.add(ctx, "copy-in FAILED: '" + name + "': " + t);
            // Our own checks (no space, server not running) throw
            // IllegalStateException with a message written for the host.
            Report.problem = "Could not share '" + name + "': "
                    + (t instanceof IllegalStateException ? t.getMessage() : "the file could not be read") + ".";
            // Remove whatever part of the copy was written.
            if (fid != null && dc != null) {
                try { dc.callAttr("discard", fid); } catch (Throwable ignored) { /* server already stopped and wiped */ }
            }
        } finally {
            status = "";
        }
    }

    /**
     * Make the thumbnail the guest page shows, for a picture or a video.
     *
     * Writes a JPEG no larger than THUMB_PX on its longer side to
     * "<file>.t" - the slot the DropZone core already serves at /api/thumb.
     * In DropZone the uploader's BROWSER makes this; a file shared from the
     * share menu never passes through a browser, so Android makes it here.
     *
     * Returns a short note for the log: the thumbnail's size, or why there is
     * none. Never throws.
     *
     * FILE EFFECTS: writes "<file>.t"; removes it again if making it failed.
     */
    public static String makeThumb(File file, String name) {
        // Android's ready-made thumbnail maker for a plain file (it also
        // turns a photo the right way up) arrived in Android 10 (API 29).
        // Android 8 and 9 show the icon instead.
        if (Build.VERSION.SDK_INT < 29) return "none (needs Android 10+)";

        // Decide picture / video from the NAME's ending, not from the type the
        // sending app stated (the Xiaomi gallery sent "image/*").
        int dot = name.lastIndexOf('.');
        String ext = dot >= 0 ? name.substring(dot + 1).toLowerCase(Locale.US) : "";
        String type = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
        if (type == null) return "none (unknown kind ." + ext + ")";

        File out = new File(file.getPath() + ".t");
        try {
            Size box = new Size(THUMB_PX, THUMB_PX);
            Bitmap bmp;
            if (type.startsWith("image/"))      bmp = ThumbnailUtils.createImageThumbnail(file, box, null);
            else if (type.startsWith("video/")) bmp = ThumbnailUtils.createVideoThumbnail(file, box, null);
            else return "none (not a picture or video)";

            // Android may hand back something larger than asked; shrink so the
            // longer side is THUMB_PX, keeping the shape (k = scale factor <= 1).
            int w = bmp.getWidth(), h = bmp.getHeight();
            float k = Math.min(1f, (float) THUMB_PX / Math.max(w, h));
            if (k < 1f) {
                w = Math.max(1, Math.round(w * k));
                h = Math.max(1, Math.round(h * k));
                bmp = Bitmap.createScaledBitmap(bmp, w, h, true);   // true = smooth scaling
            }
            try (OutputStream o = new FileOutputStream(out)) {
                bmp.compress(Bitmap.CompressFormat.JPEG, 80, o);    // 80 = JPEG quality, as small as looks clean
            }
            return w + "x" + h + " (" + out.length() + " bytes)";
        } catch (Throwable t) {
            out.delete();   // no half-written thumbnail left behind
            return "none (" + t + ")";
        }
    }

    /** Bytes as megabytes, e.g. "2035 MB". */
    private static String mb(long bytes) {
        return (bytes / 1048576) + " MB";
    }

    /** Bytes as lowercase hex, the usual way an MD5 is written. */
    private static String hex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}
