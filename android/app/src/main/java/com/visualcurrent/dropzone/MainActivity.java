package com.visualcurrent.dropzone;

import android.Manifest;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/**
 * The app's only screen, styled after the DropZone web page (same colours,
 * logo and wording).
 *
 * Layout, top to bottom:
 *   header   - logo, name, "Host" badge, tagline
 *   card     - three rows, each "information on the left, its button on the
 *              right":  Server -> Start/Stop,  Your host page -> Open,
 *              Others join at -> Copy.  The buttons share one column.
 *   steps    - "How it works" in three lines
 *   footer   - script version (left) and app version (right)
 *
 * The host page itself opens in the phone's browser, not inside the app: the
 * browser already handles file picking and multi-GB downloads.
 *
 * Everything is built in code (no layout XML) so the whole screen is in this
 * one file. Colours come from DropZone.py's CSS variables; see loadPalette().
 */
public class MainActivity extends Activity {

    private static final String HOST_URL = "http://localhost:7070";

    // Button looks, used by styleButton().
    private static final int FILLED = 0, OUTLINE = 1, TONAL = 2, DISABLED = 3;

    // Palette (filled in by loadPalette for light or dark mode).
    private int cBg, cSurf, cOff, cBorder, cDiv, cTxt, cMuted, cPri, cPriHl, cOnPri, cErr, cDotOff;
    private float density;   // pixels per dp on this screen

    // Widgets that change between Stopped and Running.
    private View serverDot;
    private TextView serverState, serverSub, hostMain, hostSub, joinMain, joinSub, stopNote, step1Num, step1Text;
    private Button serverBtn, openBtn, copyBtn;

    // What the screen currently shows, so the once-a-second refresh only
    // restyles widgets when something actually changed.
    private String shownState = null;

    // Re-reads ServerService's state once a second while the screen is visible.
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable refresher = new Runnable() {
        @Override public void run() {
            refresh();
            handler.postDelayed(this, 1000);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        density = getResources().getDisplayMetrics().density;
        boolean night = (getResources().getConfiguration().uiMode
                & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        loadPalette(night);

        // System bars: match the page colours, and ask for dark icons on the
        // light theme. (Android 15+ ignores the two colour calls and instead
        // draws the app under the bars; the root's fitsSystemWindows below
        // keeps our content clear of them either way.)
        getWindow().setBackgroundDrawable(new ColorDrawable(cBg));
        getWindow().setStatusBarColor(cSurf);
        getWindow().setNavigationBarColor(cSurf);
        if (!night) {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(cSurf);          // shows behind the status bar, same as the header
        root.setFitsSystemWindows(true);         // pad for status + navigation bars
        root.addView(buildHeader());

        // The middle scrolls, so nothing is cut off on a small phone or with
        // a large system font; the footer stays at the bottom.
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(cBg);
        scroll.setFillViewport(true);
        scroll.addView(buildBody());
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));   // weight 1 = take the leftover height

        root.addView(buildFooter());
        setContentView(root);

        // Android 13+ hides notifications until the user allows them. The
        // server runs either way; this only makes its notification visible.
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                   != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.post(refresher);
    }

    @Override
    protected void onPause() {
        handler.removeCallbacks(refresher);
        super.onPause();
    }

    // ── Colours ──────────────────────────────────────────────────────────────

    /** Same values as the :root / [data-theme="dark"] CSS variables in DropZone.py. */
    private void loadPalette(boolean night) {
        if (night) {
            cBg = 0xFF171614; cSurf = 0xFF1C1B19; cOff = 0xFF27261F;
            cBorder = 0xFF383632; cDiv = 0xFF262422;
            cTxt = 0xFFD0CFC9; cMuted = 0xFF8A8880;
            cPri = 0xFF4F98A3; cPriHl = 0x244F98A3;   // 0x24 = 14% opacity
            cOnPri = 0xFF171614;                      // dark text on the lighter teal, for contrast
            cErr = 0xFFD163A7; cDotOff = 0xFF8A8880;
        } else {
            cBg = 0xFFF4F3EF; cSurf = 0xFFF9F8F5; cOff = 0xFFEDEAE5;
            cBorder = 0xFFD4D1CA; cDiv = 0xFFDCD9D5;
            cTxt = 0xFF28251D; cMuted = 0xFF6B6A66;
            cPri = 0xFF01696F; cPriHl = 0x1F01696F;   // 0x1F = 12% opacity
            cOnPri = Color.WHITE;
            cErr = 0xFFA12C7B; cDotOff = 0xFFA09D96;
        }
    }

    // ── Building blocks ──────────────────────────────────────────────────────

    /** dp -> pixels. All sizes below are written in dp, like the mockup. */
    private int px(float dp) {
        return Math.round(dp * density);
    }

    /** A rounded rectangle background. strokeColor 0 means no outline. */
    private GradientDrawable shape(int fillColor, int strokeColor, float radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fillColor);
        d.setCornerRadius(px(radiusDp));
        if (strokeColor != 0) d.setStroke(px(1), strokeColor);
        return d;
    }

    private TextView text(String s, float sizeSp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sizeSp);
        t.setTextColor(color);
        if (bold) makeBold(t);
        return t;
    }

    /**
     * Bold that works on every phone. Some makers' system fonts (seen on a
     * Xiaomi) ignore the stock Typeface.DEFAULT_BOLD and draw it regular.
     * Deriving bold from the view's own current font lets Android thicken the
     * strokes itself when that font has no real bold weight.
     */
    private void makeBold(TextView t) {
        t.setTypeface(t.getTypeface(), Typeface.BOLD);
    }

    /** Small upper-case caption, like the web page's card titles. */
    private TextView caption(String s) {
        TextView t = text(s, 11, cMuted, true);
        t.setAllCaps(true);
        t.setLetterSpacing(0.07f);
        return t;
    }

    /** A 96 x 48 dp button with no system styling; styleButton() gives it a look. */
    private Button button(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(15);
        makeBold(b);
        b.setStateListAnimator(null);     // no raised-button shadow
        b.setMinHeight(0);
        b.setMinimumHeight(0);
        b.setPadding(0, 0, 0, 0);
        b.setLayoutParams(new LinearLayout.LayoutParams(px(96), px(48)));
        return b;
    }

    private void styleButton(Button b, int look) {
        b.setEnabled(look != DISABLED);
        if (look == FILLED) {
            b.setBackground(shape(cPri, 0, 10));        b.setTextColor(cOnPri);
        } else if (look == OUTLINE) {
            b.setBackground(shape(Color.TRANSPARENT, cErr, 10)); b.setTextColor(cErr);
        } else if (look == TONAL) {
            b.setBackground(shape(cPriHl, 0, 10));      b.setTextColor(cPri);
        } else {
            b.setBackground(shape(cOff, cBorder, 10));  b.setTextColor(cMuted);
        }
    }

    /** One card row: a column of text that takes the free width, then its button. */
    private LinearLayout row(Button b, View... lines) {
        LinearLayout info = new LinearLayout(this);
        info.setOrientation(LinearLayout.VERTICAL);
        for (View v : lines) info.addView(v);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);   // weight 1 = all width the button leaves
        lp.rightMargin = px(14);

        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setGravity(Gravity.CENTER_VERTICAL);
        r.setPadding(px(16), px(16), px(16), px(16));
        r.addView(info, lp);
        r.addView(b);
        return r;
    }

    /** 1 dp line between card rows. */
    private View divider() {
        View v = new View(this);
        v.setBackgroundColor(cDiv);
        v.setLayoutParams(new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, px(1)));
        return v;
    }

    /** One "How it works" line: a 24 dp numbered circle, then the sentence. */
    private LinearLayout step(TextView num, TextView sentence) {
        num.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(px(24), px(24));
        np.rightMargin = px(10);
        LinearLayout s = new LinearLayout(this);
        s.setOrientation(LinearLayout.HORIZONTAL);
        s.setPadding(0, px(10), 0, 0);
        s.addView(num, np);
        s.addView(sentence, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        return s;
    }

    private TextView stepNumber(String n) {
        TextView t = text(n, 12, cPri, true);
        t.setBackground(shape(cPriHl, 0, 12));   // radius 12 on a 24 dp square = a circle
        return t;
    }

    // ── Screen sections ──────────────────────────────────────────────────────

    private View buildHeader() {
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.ic_logo);
        logo.setColorFilter(cPri);                // tint the white strokes teal
        LinearLayout.LayoutParams logoLp = new LinearLayout.LayoutParams(px(26), px(26));
        logoLp.rightMargin = px(10);

        TextView name = text("DropZone", 21, cPri, true);

        TextView badge = text("Host", 11, cPri, true);
        badge.setLetterSpacing(0.04f);
        badge.setBackground(shape(cPriHl, 0, 999));          // pill
        badge.setPadding(px(10), px(3), px(10), px(3));

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.addView(logo, logoLp);
        top.addView(name, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        top.addView(badge);                                  // pushed to the right edge by the name's weight

        TextView tagline = text("Share files with anyone on this WiFi. Only this phone needs the app.",
                14, cMuted, false);
        tagline.setPadding(0, px(6), 0, 0);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setBackgroundColor(cSurf);
        header.setPadding(px(20), px(18), px(20), px(16));
        header.addView(top);
        header.addView(tagline);

        // Header + its bottom border line.
        LinearLayout wrap = new LinearLayout(this);
        wrap.setOrientation(LinearLayout.VERTICAL);
        wrap.addView(header);
        View border = new View(this);
        border.setBackgroundColor(cBorder);
        wrap.addView(border, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, px(1)));
        return wrap;
    }

    private View buildBody() {
        // Row 1: Server -> Start / Stop
        serverDot = new View(this);
        LinearLayout.LayoutParams dotLp = new LinearLayout.LayoutParams(px(10), px(10));
        dotLp.rightMargin = px(8);
        serverState = text("", 17, cTxt, true);
        LinearLayout stateLine = new LinearLayout(this);
        stateLine.setOrientation(LinearLayout.HORIZONTAL);
        stateLine.setGravity(Gravity.CENTER_VERTICAL);
        stateLine.setPadding(0, px(3), 0, px(3));
        stateLine.addView(serverDot, dotLp);
        stateLine.addView(serverState);
        serverSub = text("", 13, cMuted, false);
        serverBtn = button("Start");
        serverBtn.setOnClickListener(v -> {
            Intent svc = new Intent(this, ServerService.class);
            if (ServerService.running) {
                stopService(svc);
            } else {
                ServerService.lastError = "";
                startForegroundService(svc);
            }
        });

        // Row 2: Your host page -> Open (in the phone's browser)
        hostMain = text("Add files, show the QR code", 15, cTxt, false);
        hostMain.setPadding(0, px(3), 0, px(3));
        hostSub = text("", 13, cMuted, false);
        openBtn = button("Open");
        openBtn.setOnClickListener(v ->
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(HOST_URL))));

        // Row 3: Others join at -> Copy
        joinMain = text("", 14, cTxt, false);
        joinMain.setTypeface(Typeface.MONOSPACE);
        joinMain.setTextIsSelectable(true);
        joinMain.setPadding(0, px(3), 0, px(3));
        joinSub = text("", 13, cMuted, false);
        copyBtn = button("Copy");
        copyBtn.setOnClickListener(v -> {
            ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            cm.setPrimaryClip(ClipData.newPlainText("DropZone address", ServerService.remoteUrl));
            // Android 13+ shows its own "copied" bubble; older versions show nothing.
            if (Build.VERSION.SDK_INT < 33) {
                Toast.makeText(this, "Address copied", Toast.LENGTH_SHORT).show();
            }
        });

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(shape(cSurf, cBorder, 14));
        card.addView(row(serverBtn, caption("Server"), stateLine, serverSub));
        card.addView(divider());
        card.addView(row(openBtn, caption("Your host page"), hostMain, hostSub));
        card.addView(divider());
        card.addView(row(copyBtn, caption("Others join at"), joinMain, joinSub));

        stopNote = text("Stopping the server deletes the files shared in this session.", 13, cMuted, false);
        stopNote.setPadding(px(6), px(16), px(6), 0);

        // How it works
        step1Num = stepNumber("1");
        step1Text = text("Start the server on this phone.", 14, cTxt, false);
        LinearLayout how = new LinearLayout(this);
        how.setOrientation(LinearLayout.VERTICAL);
        how.setPadding(px(6), px(20), px(6), 0);
        how.addView(caption("How it works"));
        how.addView(step(step1Num, step1Text));
        how.addView(step(stepNumber("2"),
                text("Open your host page to add files and show the QR code.", 14, cTxt, false)));
        how.addView(step(stepNumber("3"),
                text("Others scan it and join in their browser. No app, no account.", 14, cTxt, false)));

        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(px(16), px(20), px(16), px(20));
        body.addView(card);
        body.addView(stopNote);
        body.addView(how);
        return body;
    }

    private View buildFooter() {
        // Both numbers are written into the app when it is built (app/build.gradle),
        // so they are known before the server has ever been started.
        TextView core = text("DropZone v" + BuildConfig.CORE_VERSION + " " + BuildConfig.CORE_STAGE,
                12, cMuted, false);
        TextView app = text("App " + BuildConfig.WRAPPER_VERSION, 12, cMuted, false);

        LinearLayout footer = new LinearLayout(this);
        footer.setOrientation(LinearLayout.HORIZONTAL);
        footer.setBackgroundColor(cBg);
        footer.setPadding(px(20), px(12), px(20), px(16));
        footer.addView(core, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        footer.addView(app);
        return footer;
    }

    // ── State -> screen ──────────────────────────────────────────────────────

    /** Copy ServerService's published state onto the screen (only when it changed). */
    private void refresh() {
        boolean on = ServerService.running;
        String error = ServerService.lastError;
        String state = on + "|" + ServerService.remoteUrl + "|" + error;
        if (state.equals(shownState)) return;
        shownState = state;

        // Row 1: server
        GradientDrawable dot = new GradientDrawable();
        dot.setShape(GradientDrawable.OVAL);
        dot.setColor(on ? cPri : cDotOff);
        serverDot.setBackground(dot);
        serverState.setText(on ? "Running" : "Stopped");
        serverState.setTextColor(on ? cPri : cTxt);
        if (on) {
            serverSub.setText("Keeps going with the screen off.");
            serverSub.setTextColor(cMuted);
        } else if (!error.isEmpty()) {
            serverSub.setText("Could not start: " + error);
            serverSub.setTextColor(cErr);
        } else {
            serverSub.setText("Nothing is shared right now.");
            serverSub.setTextColor(cMuted);
        }
        serverBtn.setText(on ? "Stop" : "Start");
        styleButton(serverBtn, on ? OUTLINE : FILLED);

        // Row 2: host page
        hostMain.setVisibility(on ? View.VISIBLE : View.GONE);
        hostSub.setText(on ? "Opens in your browser."
                           : "Opens in your browser once the server is running.");
        styleButton(openBtn, on ? FILLED : DISABLED);

        // Row 3: address for the others. Shown without "http://" to fit one
        // line; the Copy button copies the full address.
        joinMain.setVisibility(on ? View.VISIBLE : View.GONE);
        joinMain.setText(ServerService.remoteUrl.replaceFirst("^http://", ""));
        joinSub.setText(on ? "Same WiFi. No app, no account."
                           : "The address appears here when the server is running.");
        styleButton(copyBtn, on ? TONAL : DISABLED);

        stopNote.setVisibility(on ? View.VISIBLE : View.GONE);

        // Step 1 is ticked off once the server runs.
        step1Num.setText(on ? "✓" : "1");
        step1Num.setTextColor(on ? cOnPri : cPri);
        step1Num.setBackground(shape(on ? cPri : cPriHl, 0, 12));
        step1Text.setTextColor(on ? cMuted : cTxt);
    }
}
