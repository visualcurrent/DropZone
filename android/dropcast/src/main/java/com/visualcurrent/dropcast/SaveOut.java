package com.visualcurrent.dropcast;

import android.content.Context;
import android.net.Uri;
import android.provider.DocumentsContract;

import com.chaquo.python.Python;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Saves a file a guest shared out of the app, to the place the host picked in
 * Android's save dialog (PLAN.md > M2 step 6).
 *
 * The file is already on this phone, inside DropCast's own storage, where it
 * is deleted at Stop. "Download" on the host's screen therefore is a local
 * copy, not a network download. It is a COPY, not a move: the app's copy
 * stays so the file's QR keeps working until Stop (moving instead is
 * UNEXPLORED_IDEAS U6).
 *
 * FILE EFFECTS: writes the document the host chose. If the copy fails partway
 * (for example the phone fills up) that half-written document is deleted.
 */
final class SaveOut {

    /** Progress line for the screen, "" when no save is running. */
    static volatile String status = "";

    // One worker thread: a second save waits for the first to finish.
    private static final ExecutorService worker = Executors.newSingleThreadExecutor();

    private static final int BLOCK = 1024 * 1024;   // copy 1 MB at a time; memory use stays flat

    private SaveOut() {}

    /**
     * Queue one save.
     *
     * dest: the document Android's save dialog created (still empty).
     * fid:  the file's id, to mark it saved afterwards.
     * src:  the app's copy of the file.
     */
    static void start(Context appCtx, Uri dest, String fid, String name, File src) {
        worker.execute(() -> run(appCtx, dest, fid, name, src));
    }

    private static void run(Context ctx, Uri dest, String fid, String name, File src) {
        long total = src.length();
        long done = 0;
        long lastShown = 0;
        status = "Saving '" + name + "'";
        try {
            // --- copy -----------------------------------------------------------
            try (InputStream in = new FileInputStream(src);
                 OutputStream out = ctx.getContentResolver().openOutputStream(dest)) {
                if (out == null) throw new java.io.IOException("the chosen place could not be opened");
                byte[] block = new byte[BLOCK];
                int n;
                while ((n = in.read(block)) > 0) {
                    out.write(block, 0, n);
                    done += n;
                    // Refresh the progress line about four times a second.
                    long now = System.nanoTime();
                    if (now - lastShown > 250_000_000L) {
                        lastShown = now;
                        status = "Saving '" + name + "': " + (done / 1048576) + " MB of "
                                + (total / 1048576) + " MB (" + (total > 0 ? 100 * done / total : 100) + "%)";
                    }
                }
            }
            if (done != total) throw new java.io.IOException("only " + done + " of " + total + " bytes were written");

            // --- record ---------------------------------------------------------
            Python.getInstance().getModule("dc_host").callAttr("mark_saved", fid);
            Report.add(ctx, "saved: '" + name + "' id=" + fid + " bytes=" + done + " to " + dest.getAuthority());
        } catch (Throwable t) {
            Report.add(ctx, "save FAILED: '" + name + "' id=" + fid + " after " + done + " bytes: " + t);
            // Do not leave half a file behind under the real file's name.
            try {
                DocumentsContract.deleteDocument(ctx.getContentResolver(), dest);
            } catch (Throwable ignored) { /* some storage apps do not allow deleting; nothing more to do */ }
            Report.problem = "Could not save '" + name + "'. The place you chose may be full or not writable. "
                    + "The file is still held in DropCast; try saving it somewhere else.";
        } finally {
            status = "";
        }
    }
}
