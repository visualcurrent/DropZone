package com.visualcurrent.dropcast;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.WebView;
import android.widget.FrameLayout;
import android.widget.TextView;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import java.io.File;
import java.util.List;
import java.util.Locale;

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
    private static final int SAVE_FILE = 8;   // ... and our save-dialog request
    private String pendingSaveFid = null;     // the received file whose save dialog is open

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
        } else {
            pendingSaveFid = saved.getString("pendingSaveFid");
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

    /** Both of Android's dialogs return here: the file picker and the save dialog. */
    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (result != RESULT_OK || data == null || data.getData() == null) return;   // cancelled

        if (request == PICK_FILE) {
            shareFile(data.getData(), "file picker");
        } else if (request == SAVE_FILE && pendingSaveFid != null) {
            // The host chose where to save; copy the file there in the background.
            String fid = pendingSaveFid;
            pendingSaveFid = null;
            PyObject info = fileInfo(fid);
            if (info == null) {
                Report.problem = "That file is no longer held in DropCast.";
                return;
            }
            List<PyObject> f = info.asList();   // [name, path, size]
            SaveOut.start(getApplicationContext(), data.getData(), fid,
                    f.get(0).toString(), new File(f.get(1).toString()));
        }
    }

    /** Keep the id of the file being saved if Android rebuilds the screen while its save dialog is open. */
    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putString("pendingSaveFid", pendingSaveFid);
    }

    /** dc_host.file_info(fid) -> [name, path, size], or null when the file is not held or the server is down. */
    private PyObject fileInfo(String fid) {
        if (!CastService.running) return null;
        return Python.getInstance().getModule("dc_host").callAttr("file_info", fid);   // Python None arrives as null
    }

    /**
     * "Download" on a received file: check there is room, then open Android's
     * save dialog with the file's name filled in. onActivityResult continues.
     */
    private void beginSave(String fid) {
        PyObject info = fileInfo(fid);
        if (info == null) {
            Report.problem = "That file is no longer held in DropCast.";
            return;
        }
        List<PyObject> f = info.asList();   // [name, path, size]
        String name = f.get(0).toString();
        long size = f.get(2).toLong();

        // Free-space check (Gabe, 2026-11-13): saving is a copy, so the phone
        // needs room for a second copy. Measured on the phone's own storage,
        // which is where a save normally goes; a save to a memory card or a
        // cloud folder is not measured.
        long free = Environment.getDataDirectory().getUsableSpace();
        if (size > free) {
            Report.add(this, "save refused, not enough space: '" + name + "' size=" + size + " free=" + free);
            Report.problem = "Not enough space to save this file. It is " + (size / 1048576)
                    + " MB and this phone has " + (free / 1048576) + " MB free.";
            return;
        }

        // The save dialog wants the kind of file; take it from the name's ending.
        int dot = name.lastIndexOf('.');
        String ext = dot >= 0 ? name.substring(dot + 1).toLowerCase(Locale.US) : "";
        String type = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);

        Intent save = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        save.addCategory(Intent.CATEGORY_OPENABLE);
        save.setType(type != null ? type : "application/octet-stream");   // octet-stream = "any file"
        save.putExtra(Intent.EXTRA_TITLE, name);
        pendingSaveFid = fid;
        startActivityForResult(save, SAVE_FILE);
    }

    /** Stop: shut the server down (which deletes the files DropCast holds) and close the app. */
    private void stopNow() {
        Report.add(this, "Stop confirmed");
        stopService(new Intent(this, CastService.class));
        finishAndRemoveTask();
    }

    /** Stop was tapped: ask first when received files have not been saved (PLAN M2). */
    private void askStop() {
        int unsaved = 0;
        if (CastService.running) {
            unsaved = Python.getInstance().getModule("dc_host").callAttr("unsaved_count").toInt();
        }
        if (unsaved == 0) {
            stopNow();
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Stop sharing?")
                .setMessage("You have " + unsaved + (unsaved == 1 ? " unsaved file" : " unsaved files")
                        + ". Stopping removes " + (unsaved == 1 ? "it" : "them") + " from this phone. Stop anyway?")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Stop anyway", (d, which) -> stopNow())
                .show();
    }

    /** True while the phone is allowed to pause this app in the background. */
    private boolean batteryRestricted() {
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        return !pm.isIgnoringBatteryOptimizations(getPackageName());
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

        /** The progress line of a copy-in or a save, "" when neither is running. */
        @JavascriptInterface
        public String status() {
            return !CopyIn.status.isEmpty() ? CopyIn.status : SaveOut.status;
        }

        /** The last failure the host should be told about, "" when none. */
        @JavascriptInterface
        public String problem() {
            return Report.problem;
        }

        /** The host tapped OK on the problem box. */
        @JavascriptInterface
        public void clearProblem() {
            Report.problem = "";
        }

        /**
         * True while the phone may pause DropCast in the background. On the
         * Xiaomi that freezes the server (guests' pages hang) until the app's
         * battery option is set to "No restrictions"; see CLAUDE.md.
         */
        @JavascriptInterface
        public boolean batteryRestricted() {
            return MainActivity.this.batteryRestricted();
        }

        /** Open this app's page in the phone's Settings, where the battery option lives. */
        @JavascriptInterface
        public void openAppSettings() {
            runOnUiThread(() -> startActivity(new Intent(
                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName()))));
        }

        /** "Download" on a received file: save it through Android's save dialog. */
        @JavascriptInterface
        public void save(String fid) {
            runOnUiThread(() -> beginSave(fid));
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

        /** Stop: asks first if received files are unsaved, then stops and closes. */
        @JavascriptInterface
        public void stop() {
            runOnUiThread(() -> askStop());
        }
    }
}
