package com.visualcurrent.dropcast;

import android.content.Context;
import android.util.Log;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * One place for DropCast's own log lines, usable from any thread and whether
 * or not the screen is showing.
 *
 * Each line goes to logcat and to the file files/DropCast.log. (The server's
 * own lines are separate, in files/DropZone.log.)
 *
 * FILE EFFECTS: appends to DropCast.log in the app's private files folder.
 * Read it from the PC with:
 *   adb shell run-as com.visualcurrent.dropcast cat files/DropCast.log
 */
final class Report {

    private static final String TAG = "DropCast";

    /**
     * The last failure the HOST should be told about, in plain words; "" when
     * there is none. The host's screen shows it in a box until OK is tapped.
     * (Log lines are for the developer; this is for the person holding the phone.)
     */
    static volatile String problem = "";

    private Report() {}

    /** Record one line. synchronized: the copy thread and the screen both call this. */
    static synchronized void add(Context ctx, String line) {
        String stamped = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date()) + "  " + line;
        Log.i(TAG, line);
        try (FileWriter w = new FileWriter(new File(ctx.getFilesDir(), "DropCast.log"), true)) {  // true = append
            w.write(stamped + "\n");
        } catch (IOException e) {
            Log.w(TAG, "could not write DropCast.log: " + e);
        }
    }
}
