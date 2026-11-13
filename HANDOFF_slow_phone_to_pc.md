# HANDOFF — slow transfers from the phone to this PC

Written 2026-11-13 for a future session. Self-contained: nothing else needs to be read first. Closed as an issue for the DropZone/DropCast project (Gabe, 2026-11-13); kept here as an open question about the PC or the network.

## The problem in one line
Files sent from Gabe's Android phone to this Windows PC over the home WiFi arrive at about 5 MB/s, while the same phone sends the same file to a second phone at about 47 MB/s, and this PC downloads from the internet at about 52 MB/s.

## Devices
| Role | Device | Address | Link |
|---|---|---|---|
| Sender ("host's phone") | Xiaomi 23116PN5BC, Android 16, adb serial `fc0f334f` | 192.168.7.110 | WiFi 6 (11ax), 5745 MHz (5 GHz, channel 149), 1200 Mbps, RSSI -50 [verified: `dumpsys wifi` 2026-11-13] |
| Slow receiver ("the PC") | Windows 11 Pro, MediaTek Wi-Fi 7 MT7925 | 192.168.7.133 | 1.2 Gbps reported; band not read [verified: `Get-NetAdapter`] |
| Fast receiver ("guest's phone") | Android 16, Firefox | 192.168.7.94 | not read |

The sender is the DropCast app (or the DropZone app; same server code): a Python `http.server` inside an Android app, plain HTTP on port 7071 (DropZone: 7070). A download is `GET /api/download?id=<id>`.

## Measurements
All sender-side timings are from the app's own log on the phone, 2026-11-13 unless dated.

| From | To | Size | Time | Rate | Tag |
|---|---|---|---|---|---|
| Host's phone | PC (curl) | 2.13 GB | 428 s | 4.75 MB/s | [verified: curl + log] |
| Host's phone | PC (Firefox) | 766 MB | 180 s | 4.3 MB/s | [verified: log] |
| Host's phone | PC (curl), while a phone uploaded | 1.4 GB | 264 s | 5.5 MB/s | [verified: curl + log] |
| Host's phone | PC (Chrome) | 2.0 GB | 395 s | 5.5 MB/s | [verified: log] |
| Host's phone | Guest's phone | 1.4 GB | 31 s | 47 MB/s | [verified: log] |
| Host's phone | its own browser (loopback) | 766 MB | 3 s | about 255 MB/s | [verified: log] |
| Guest's phone | Host's phone | 1.4 GB | 19 s | 76 MB/s | [verified: log] |
| Guest's phone | Host's phone, while the PC downloaded | 1.6 GB | 197 s | 8.2 MB/s | [verified: log] |
| PC | Host's phone (upload, 2026-11-11, DropZone app) | 2.6 GB | 108 s | 24 MB/s | [verified: project log 2026-11-11] |
| Internet | PC | — | — | 427 and 415 Mbps down (about 52 MB/s) | [verified: Gabe's two speed tests, bandwidthplace.com and librespeed.org] |
| PC | Internet | — | — | 101.5 and 48.5 Mbps up | [verified: same tests] |

## What is established
- The phone's server is not the limit: it sends at 47 MB/s to another phone and about 255 MB/s to itself. [verified]
- The PC's WiFi is not slow in general: it receives about 52 MB/s from the internet through the same router. [verified: Gabe's speed tests]
- The slowness is specific to the pair phone -> PC. It is the same in curl, Firefox and Chrome, so it is not a browser's doing. [verified]
- It is steady near 5 MB/s whether or not other traffic is running. [verified]
- While it runs, a phone-to-phone transfer on the same WiFi drops from 76 to about 8 MB/s. [verified]
- PC -> phone is about 5 times faster than phone -> PC (24 against 5 MB/s). [verified, different days and apps]

## Retracted
An earlier conclusion in the project log, "the slow leg is this PC's WiFi reception", was wrong as worded. The PC receives fast from the internet. What the data supports is narrower: the path from this phone to this PC is slow.

## Facts gathered about the PC
- Route to the phone is the `Wi-Fi` adapter directly; no VPN or virtual adapter is in the path. [verified: `Find-NetRoute`, `Get-NetAdapter` 2026-11-13]
- The WiFi network is set to `Public` in Windows. [verified: `Get-NetConnectionProfile`]
- TCP receive-window auto-tuning is `normal`. [verified: `netsh interface tcp show global`]
- `netsh wlan show interfaces` printed nothing in the agent's shell, so the PC's band, channel and signal are not known. [verified: empty output] Windows may need location permission for that command.

## Not yet examined (candidate causes, none tested)
Each is [assumed] until a test says otherwise.
1. The PC and the phone on different bands or links of the router (the adapter is WiFi 7 and may be on 6 GHz or a multi-link connection while the phone is on 5 GHz), with a slow bridge between them inside the router.
2. Security software on the PC inspecting plain-HTTP traffic from a local address (Windows Defender network inspection or a third-party web shield).
3. The MediaTek driver's handling of traffic that arrives from another WiFi client, as opposed to from the router's wired side.
4. A router feature that treats client-to-client traffic differently (airtime fairness, "smart connect", a guest or isolation setting) for this PC.
5. Retries on the router-to-PC radio leg for this traffic only; that would also explain why the phone-to-phone transfer slows while it runs, since retries use shared air time.

## Suggested first tests, cheapest first
1. Read the PC's WiFi band, channel, signal and receive rate (`netsh wlan show interfaces` in a normal user terminal). Compare with the phone's 5745 MHz.
2. Take the app out of the picture: run `iperf3` between phone and PC in both directions (Termux is installed on the phone as a test bench; `pkg install iperf3`), and between the PC and a wired device if one exists.
3. Repeat the download with the PC on an Ethernet cable to the router. Fast means the PC's radio leg is the cause; still slow means the router's handling of the phone's traffic, or the PC's software.
4. Repeat with real-time protection briefly off, or with the port excluded, to rule the security software in or out. This changes a protection setting, so Gabe does it himself.
5. Watch the PC's adapter statistics during a download for retransmissions and receive errors (`Get-NetAdapterStatistics`, Resource Monitor).

## How to reproduce a measurement
1. On the phone open DropCast and share any large file; the screen shows its address, `http://192.168.7.110:7071/f/<id>`.
2. On the PC, time the download without storing it: `curl -s -o NUL -w "%{speed_download}" "http://192.168.7.110:7071/api/download?id=<id>"` (cmd; in Git Bash use `-o /dev/null`).
3. The phone's side of the timing is in its log: `C:\adb\adb.exe shell run-as com.visualcurrent.dropcast tail -n 20 files/DropZone.log` (`download:` and `download done:` lines).

The phone's WiFi address can change between sessions; DropCast's screen always shows the current one.
