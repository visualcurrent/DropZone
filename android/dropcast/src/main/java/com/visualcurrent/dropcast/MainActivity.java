package com.visualcurrent.dropcast;

import android.Manifest;
import android.annotation.SuppressLint;
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
import android.view.Gravity;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * DropCast's one screen (PLAN.md > M2 step 4).
 *
 * The screen is a WEB PAGE shown inside the app: a WebView pointed at the
 * server running on this same phone (http://127.0.0.1:7071/host, built by
 * dc_host.host_page). So the host's screen and the guest's page share one
 * design and one QR library.
 *
 * This class only does what a web page cannot:
 *   - start the server when the app opens;
 *   - receive a file from the share menu, or from Android's file picker
 *     ("Choose a file"), and hand it to CopyIn;
 *   - give the page three calls through the "Android" object (see Bridge):
 *     the copy-in progress line, open the file picker, stop.
 *
 * Until the server is up (about a second) a plain "Starting..." line shows.
 */
public class MainActivity extends Activity {

    private static final String HOST_PAGE = "http://127.0.0.1:" + CastService.PORT + "/host";
    private static final int PICK_FILE = 7;   // any number; names our file-picker request

    private WebView web;
    private TextView msg;             // "Starting..." or the reason the server did not start
    private boolean pageLoaded = false;

    // Twice a second while the screen is visible: once the server is running,
    // load the host page; if it is not running, say why.
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable watch = new Runnable() {
        @Override public void run() {
            if (CastService.running) {
                if (!pageLoaded) {
                    pageLoaded = true;
                    web.loadUrl(HOST_PAGE);
                    web.setVisibility(View.VISIBLE);
                    msg.setVisibility(View.GONE);
                }
            } else {
                pageLoaded = false;
                web.setVisibility(View.GONE);
                msg.setVisibility(View.VISIBLE);
                msg.setText(CastService.lastError.isEmpty()
                        ? "Starting DropCast..."
                        : "DropCast could not start:\n" + CastService.lastError);
            }
            handler.postDelayed(this, 500);
        }
    };

    // The page needs JavaScript; it only ever loads our own page from this phone.
    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);

        web = new WebView(this);
        web.getSettings().setJavaScriptEnabled(true);
        web.addJavascriptInterface(new Bridge(), "Android");   // the page calls Android.xxx()
        web.setVisibility(View.GONE);

        msg = new TextView(this);
        msg.setTextSize(16);
        msg.setGravity(Gravity.CENTER);
        int pad = (int) (24 * getResources().getDisplayMetrics().density);  // 24dp in pixels
        msg.setPadding(pad, pad, pad, pad);

        FrameLayout root = new FrameLayout(this);   // the two views share the same space
        root.setFitsSystemWindows(true);            // keep content out from under the status bar
        root.addView(web);
        root.addView(msg);
        setContentView(root);

        // Android 13+ shows a foreground service's notification only if the
        // user allows notifications. The server runs either way.
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                   != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }

        startServer();               // PLAN M2: opening the app starts the server

        // Android rebuilds this screen when the phone is rotated or its theme
        // changes, and hands back the SAME share request each time. "saved" is
        // null only on a genuinely new opening, so a shared file is taken
        // once and not copied again on every rotation.
        if (saved == null) {
            Report.add(this, "DropCast " + versionName() + " opened");
            handleIntent(getIntent());
        }
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

    /** Way in 2, the share menu: take the shared file. Opened from the icon: nothing to do. */
    private void handleIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return;

        // A shared file arrives as a content:// reference in EXTRA_STREAM.
        // (The typed getParcelableExtra exists only on Android 13+, and
        // minSdk is 26, so the older form is used on purpose.)
        @SuppressWarnings("deprecation")
        Uri uri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        if (uri == null) {
            // e.g. a web link shared from a browser: text, not a file.
            Report.add(this, "share received with NO file (type=" + intent.getType() + "); DropCast shares files only");
            return;
        }
        shareFile(uri, "share menu");
    }

    /** "Choose a file": Android's own file picker returns here with the chosen file. */
    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == PICK_FILE && result == RESULT_OK && data != null && data.getData() != null) {
            shareFile(data.getData(), "file picker");
        }
    }

    /** Both ways in end here: look up the file's name and size, then start the copy-in. */
    private void shareFile(Uri uri, String via) {
        String name = null;
        long size = -1;   // -1 = the sending app did not state a size

        // Ask the app that owns the file for its display name and size.
        try (Cursor c = getContentResolver().query(uri, null, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int nameCol = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                int sizeCol = c.getColumnIndex(OpenableColumns.SIZE);
                if (nameCol >= 0 && !c.isNull(nameCol)) name = c.getString(nameCol);
                if (sizeCol >= 0 && !c.isNull(sizeCol)) size = c.getLong(sizeCol);
            }
        } catch (Exception e) {
            Report.add(this, "could not ask for name/size: " + e);
        }

        // A sending app that gives no name still needs one for the download.
        if (name == null || name.trim().isEmpty()) {
            name = uri.getLastPathSegment() != null ? uri.getLastPathSegment() : "file";
        }

        Report.add(this, "file received via " + via + ": name='" + name + "' size=" + size
                + " bytes from=" + uri.getAuthority());

        // Opens the file now (while this screen holds the permission to read
        // it) and copies it on a background thread.
        CopyIn.start(getApplicationContext(), uri, name, size);
    }

    /** The versionName set in build.gradle, read back from the installed app. */
    private String versionName() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "?";
        }
    }

    /**
     * What the host page can ask the app to do. Each method marked
     * @JavascriptInterface is callable from the page's script as Android.name().
     * The page calls these on a background thread, so anything touching the
     * screen is passed to the main thread with runOnUiThread.
     */
    private class Bridge {

        /** The copy-in progress line, "" when no copy is running. */
        @JavascriptInterface
        public String status() {
            return CopyIn.status;
        }

        /** Way in 1: open Android's file picker for one file of any type. */
        @JavascriptInterface
        public void chooseFile() {
            runOnUiThread(() -> {
                Intent pick = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                pick.addCategory(Intent.CATEGORY_OPENABLE);   // only things that can be read as a file
                pick.setType("*/*");
                startActivityForResult(pick, PICK_FILE);
            });
        }

        /** Stop: shut the server down (which deletes the files DropCast holds) and close the app. */
        @JavascriptInterface
        public void stop() {
            runOnUiThread(() -> {
                Report.add(MainActivity.this, "Stop tapped");
                stopService(new Intent(MainActivity.this, CastService.class));
                finishAndRemoveTask();
            });
        }
    }
}
