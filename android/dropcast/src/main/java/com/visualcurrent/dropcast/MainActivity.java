package com.visualcurrent.dropcast;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.Log;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * DropCast's one screen.
 *
 * STEP 1 SKELETON (PLAN.md > M2 step 1): proves the share-menu entry works.
 * When a file is shared to DropCast, this screen shows the file's name and
 * size and appends the same line to files/DropCast.log. Nothing is copied or
 * served yet; that is step 2.
 *
 * FILE EFFECTS: appends to DropCast.log in the app's private files folder.
 * Read it from the PC with:
 *   adb shell run-as com.visualcurrent.dropcast cat files/DropCast.log
 */
public class MainActivity extends Activity {

    private static final String TAG = "DropCast";
    private TextView out;   // the on-screen copy of the log

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);

        // Plain scrolling text is enough for the skeleton; the real screen
        // (step 4) replaces it.
        out = new TextView(this);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);  // 16dp in pixels
        out.setPadding(pad, pad, pad, pad);
        out.setTextSize(16);
        out.setTextIsSelectable(true);
        ScrollView scroll = new ScrollView(this);
        scroll.setFitsSystemWindows(true);   // keep text out from under the status bar
        scroll.addView(out);
        setContentView(scroll);

        report("DropCast " + versionName() + " opened");
        handleIntent(getIntent());
    }

    /** Called instead of onCreate when a file is shared while the app is already open. */
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    /** Decide which way in was used and report what arrived. */
    private void handleIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) {
            report("Opened from the icon. Share a file to DropCast from a file manager to test.");
            return;
        }

        // A shared file arrives as a content:// reference in EXTRA_STREAM.
        // (The typed getParcelableExtra exists only on Android 13+, and
        // minSdk is 26, so the older form is used on purpose.)
        @SuppressWarnings("deprecation")
        Uri uri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        if (uri == null) {
            // e.g. a web link shared from a browser: text, not a file.
            report("share received with NO file (type=" + intent.getType() + "); DropCast shares files only");
            return;
        }

        String name = "(unknown name)";
        long size = -1;   // -1 = the sending app did not state a size

        // Ask the app that owns the file for its display name and size.
        // Each named operation is wrapped on its own so a failure says which
        // step failed.
        try (Cursor c = getContentResolver().query(uri, null, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int nameCol = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                int sizeCol = c.getColumnIndex(OpenableColumns.SIZE);
                if (nameCol >= 0 && !c.isNull(nameCol)) name = c.getString(nameCol);
                if (sizeCol >= 0 && !c.isNull(sizeCol)) size = c.getLong(sizeCol);
            }
        } catch (Exception e) {
            report("could not ask for name/size: " + e);
        }

        report("share received: name='" + name + "' size=" + size + " bytes"
                + " type=" + intent.getType() + " from=" + uri.getAuthority());
    }

    /** Show a line on screen, send it to logcat, and append it to DropCast.log. */
    private void report(String line) {
        String stamped = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date()) + "  " + line;
        Log.i(TAG, line);
        out.append(stamped + "\n\n");
        try (FileWriter w = new FileWriter(new File(getFilesDir(), "DropCast.log"), true)) {  // true = append
            w.write(stamped + "\n");
        } catch (IOException e) {
            Log.w(TAG, "could not write DropCast.log: " + e);
        }
    }

    /** The versionName set in build.gradle, read back from the installed app. */
    private String versionName() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "?";
        }
    }
}
