package com.visualcurrent.dropcast;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.util.Log;
import android.widget.Button;
import android.widget.LinearLayout;
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
 * SKELETON, through PLAN.md > M2 step 2a:
 *  - opening the app (from its icon or from the share menu) starts the server
 *    (CastService) and reports its address; one button stops and starts it;
 *  - a file shared to DropCast is reported by name and size. It is not copied
 *    or served yet; that is step 2b.
 * Every reported line is also appended to files/DropCast.log.
 *
 * FILE EFFECTS: appends to DropCast.log in the app's private files folder.
 * Read it from the PC with:
 *   adb shell run-as com.visualcurrent.dropcast cat files/DropCast.log
 */
public class MainActivity extends Activity {

    private static final String TAG = "DropCast";
    private TextView out;   // the on-screen copy of the log
    private Button serverBtn;

    // Watches CastService's published state twice a second while the screen
    // is visible, and reports each change once.
    private final Handler handler = new Handler(Looper.getMainLooper());
    private String shownState = "";
    private final Runnable watch = new Runnable() {
        @Override public void run() {
            String state = CastService.running + "|" + CastService.baseUrl + "|" + CastService.lastError;
            if (!state.equals(shownState)) {
                shownState = state;
                if (CastService.running) {
                    report("server running at " + CastService.baseUrl + " (core " + CastService.coreVersion + ")");
                } else if (!CastService.lastError.isEmpty()) {
                    report("server did NOT start: " + CastService.lastError);
                } else {
                    report("server stopped");
                }
                serverBtn.setText(CastService.running ? "Stop" : "Start");
            }
            handler.postDelayed(this, 500);
        }
    };

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
        scroll.addView(out);

        // One button: Stop while the server runs, Start while it does not.
        serverBtn = new Button(this);
        serverBtn.setText("Start");
        serverBtn.setOnClickListener(v -> {
            if (CastService.running) stopService(new Intent(this, CastService.class));
            else startServer();
        });

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setFitsSystemWindows(true);     // keep content out from under the status bar
        root.addView(serverBtn);
        root.addView(scroll);
        setContentView(root);

        // Android 13+ shows a foreground service's notification only if the
        // user allows notifications. The server runs either way.
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                   != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }

        report("DropCast " + versionName() + " opened");
        startServer();               // PLAN M2: opening the app starts the server
        handleIntent(getIntent());
    }

    /** Ask Android to start CastService (does nothing if it is already running). */
    private void startServer() {
        CastService.lastError = "";
        startForegroundService(new Intent(this, CastService.class));
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.post(watch);
    }

    @Override
    protected void onPause() {
        handler.removeCallbacks(watch);
        super.onPause();
    }

    /** Called instead of onCreate when a file is shared while the app is already open. */
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (!CastService.running) startServer();   // a new share restarts a stopped server
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
