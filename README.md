# DropZone — Instant LAN File Sharing

LAN file sharing where only the host needs to install anything to get going. Everyone else just uses their browser — no app needed.

## Description

Sharing files between phones and computers on the same WiFi should be simple. It isn't.

**AirDrop** works beautifully — but only if everyone has Apple hardware. Android apps like **LocalSend** and **SHAREit** are great — but everyone in the room has to download and install the same app before anything can happen. And getting a group of people to do that in the moment, especially across different devices and comfort levels, is friction.

**DropZone** takes a different approach: only the host installs anything. Everyone else uses the browser they already have.

The host starts DropZone on their phone or laptop. A QR code appears on screen. Anyone nearby scans it with their camera — the same way you'd scan a menu at a restaurant — and their browser opens a simple page where they can instantly download whatever the host has shared, or upload files of their own back to the group. No app store. No account. No "wait, what version are you on?" It works on any phone, any laptop, any operating system, as long as you're on the same WiFi.

The only requirement for guests: a browser. Which everyone already has.

## Requirements
Python 3.6+  (zero extra packages — pure stdlib)

## How it works

Host page   →  http://localhost:7070
Remote page →  http://your-ip:7070/remote  (or scan the QR)

Both pages have:
  • Tap-to-pick file upload using the device's native file picker
  • A live list of all shared files, grouped by user, with download buttons
  • Editable display name (auto-assigned friendly name on first visit)

The host page also shows a QR code — scan it to open the Remote page
instantly on any phone without typing a URL.

## Run it

  cd /your/script/directory/
  python3 DropZone.py

Then open http://localhost:7070 in your browser.
The QR code on that page points remote users straight to http://your-ip:7070/remote.

Make sure your DropZone.py is actually in /your/script/directory/.

## On Android (via Termux app)

Install Termux. 
[Termux on github](https://github.com/termux/termux-app) or F-Droid.

### One-time set-up

Optionally choose your repository mirror region
```
termux-change-repo
```

Install Python
```
pkg update && pkg install python
```

Grant storage permission
```
termux-setup-storage        
```
An Android system permissions dialog should pop up.

Done! See **Run it** section above.

#### One-tap home screen shortcut set-up

This screen shortcut is optional for convenience. You can always just **Run it** from terminal.

Install **Termux:Widget**.
[Termux-Widget on github](https://github.com/termux/termux-widget) or F-Droid.

Enable "Appear on top" permission for Termux:
	Android Settings > Apps > Triple dot menu > Special Access > Appear on top > Enable for Termux

##### In Termux — create the shortcuts folder

```
mkdir -p ~/.shortcuts
chmod 700 ~/.shortcuts
```

##### Create the launcher script

From the terminal:
```
cat > ~/.shortcuts/DropZone << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd /your/script/directory/
python3 DropZone.py
EOF
```

Or use nano:

```bash
nano ~/.shortcuts/DropZone
```

```nano
#!/data/data/com.termux/files/usr/bin/bash
cd /your/script/directory/
python3 DropZone.py
```
Save with Ctrl+O → Enter, exit with Ctrl+X

##### Give the script Permission to Run

```
chmod +x ~/.shortcuts/DropZone
```

Without this, Termux:Widget will see the file but won't be able to run it.

##### Create the Widget

Use normal Android Widget methods (usually long click the home screen). Choose **Termux:Widget**. 

## Notes
• Uploaded files are stored in a system temp folder while the server runs
• Temp files are automatically deleted when you stop with Ctrl+C
• State is in-memory — restarting clears the shared file lists
• Change the port by editing: PORT = 7070  near the top of DropZone.py
