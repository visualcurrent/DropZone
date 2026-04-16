# DropZone — Instant LAN File Sharing

LAN file sharing where only the host needs to install anything. Everyone else just uses their browser — no app needed.

## Description

Sharing files between phones and computers on the same WiFi should be simple. It isn't.

**AirDrop** works beautifully — but only if everyone has Apple hardware. Android apps like **LocalSend** and **SHAREit** are great — but everyone in the room has to download and install the same app before anything can happen. And getting a group of people to do that in the moment, especially across different devices and comfort levels, is friction.

**DropZone** takes a different approach: only the host installs anything. Everyone else uses the browser they already have.

The host starts DropZone on their phone or laptop. A QR code appears on screen. Anyone nearby scans it with their camera — the same way you'd scan a menu at a restaurant — and their browser opens a simple page where they can instantly download whatever the host has shared, or upload files of their own back to the group. No app store. No account. No "wait, what version are you on?" It works on any phone, any laptop, any operating system, as long as you're on the same WiFi.

The only requirement for guests: a browser. Which everyone already has.

## Requirements

Python 3.6+ (zero extra packages — pure stdlib)

## How It Works

- **Host page** → `http://localhost:7070`
- **Remote page** → `http://your-ip:7070/remote` (or scan the QR code)

Both pages have:
- Tap-to-pick file upload using the device's native file picker
- A live list of all shared files, grouped by user, with download buttons
- An editable display name (auto-assigned a friendly name on first visit)

The host page also shows a QR code — scan it to open the Remote page instantly on any phone without typing a URL. The Remote page shows the same QR at the bottom, so anyone already in can invite others by passing their phone around.

## Run It

From any Python 3-enabled terminal:

```bash
cd /your/script/directory/
python3 DropZone.py
```

Then open `http://localhost:7070` in your browser. The QR code on that page points remote users straight to `http://your-ip:7070/remote`.

## Host on Android

These instructions use Termux. Install it from [GitHub](https://github.com/termux/termux-app) or F-Droid.

> **Important:** Termux and any Termux add-ons (like Termux:Widget) must all be installed from the **same source** — all from F-Droid, or all from GitHub. Mixing sources causes a signature mismatch error.

### One-Time Setup

Optionally choose your repository mirror region:
```bash
termux-change-repo
```

Install Python:
```bash
pkg update && pkg install python
```

Grant storage permission:
```bash
termux-setup-storage
```
An Android system permissions dialog will appear. Then see **Run It** above.

### Optional: One-Tap Home Screen Shortcut

Install **[Termux:Widget](https://github.com/termux/termux-widget)** from the same source as Termux.

Enable "Appear on top" permission for Termux:
> Android Settings → Apps → ⋮ Menu → Special Access → Appear on top → Enable for Termux

**Create the shortcuts folder:**
```bash
mkdir -p ~/.shortcuts
chmod 700 ~/.shortcuts
```

**Create the launcher script** using nano:
```
nano ~/.shortcuts/DropZone
```
Type the following inside nano:
```
#!/data/data/com.termux/files/usr/bin/bash
cd /your/script/directory/
python3 DropZone.py
```
Save: `Ctrl+O` → `Enter`, exit: `Ctrl+X`

**Make it executable:**
```
chmod +x ~/.shortcuts/DropZone
```

**Add the widget:** long-press your home screen → Widgets → Termux:Widget → drag it onto your screen. Tap **DropZone** to launch.

## Notes

- Uploaded files are stored in a system temp folder while the server runs
- Temp files are automatically deleted when you stop the server with `Ctrl+C`
- State is in-memory — restarting the server clears the shared file lists
- To change the port, edit `PORT = 7070` near the top of `DropZone.py`
