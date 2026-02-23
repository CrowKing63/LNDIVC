# LNDIVC

**Apple Vision Pro Persona → Windows Virtual Webcam Streamer**

Stream your Apple Vision Pro's front-facing persona camera and microphone to your Windows PC over a local network or Tailscale VPN, and expose them as a virtual webcam and microphone to any DirectShow-compatible app — Zoom, Teams, OBS, PlayAbility, and more.

**No visionOS app installation required** — uses Safari on Vision Pro to connect to a local web page.

---

## How It Works

```
Apple Vision Pro (Safari)
  └─ getUserMedia() → Persona Camera + Microphone
       └─ WebRTC  (LAN or Tailscale VPN)
            └─ Windows  server.py
                 ├─ Video → OBS Virtual Camera
                 │             └─ Zoom / Teams / PlayAbility
                 └─ Audio → VB-Audio CABLE Input
                               └─ CABLE Output  (mic in Zoom / Teams)
```

---

## Prerequisites (Windows)

| Required | Download |
|----------|----------|
| Python 3.11 or later | https://www.python.org |
| OBS Studio (includes the virtual camera driver) | https://obsproject.com |
| VB-Audio Virtual Cable *(optional — needed for mic passthrough)* | https://vb-audio.com/Cable |

> **OBS note:** After installing OBS, launch it once and click **Tools → Start Virtual Camera** to activate the driver. The virtual camera stays active even after OBS is closed.

---

## Installation (one-time setup)

### 1. Download the repository

Download as a ZIP and extract it anywhere on your Windows PC.

### 2. Run setup.bat

Double-click `setup.bat` inside the `server` folder.

- Creates a Python virtual environment and installs all dependencies automatically
- Launches the certificate setup wizard — choose **Tailscale** or **Self-Signed**

---

## Certificate Mode

HTTPS is required for browser camera access. Choose the mode that fits your setup.

### Mode A — Tailscale (Recommended)

No certificate trust step needed on Vision Pro. Works even when your IP changes.

**Steps:**
1. Install [Tailscale](https://tailscale.com/download) on both your Windows PC and Vision Pro, and sign in to the same account
2. Go to [admin.tailscale.com/dns](https://login.tailscale.com/admin/dns) → enable **MagicDNS** and **HTTPS**
3. Run `setup.bat` → select `[1] Tailscale`

`setup.bat` will automatically issue the certificate using the `tailscale cert` CLI command.

---

### Mode B — Self-Signed (Local network only)

Use this if you don't have Tailscale.

Run `setup.bat` → select `[2] Self-Signed`, then complete the trust step below:

1. Send `server/cert.pem` to your Vision Pro via **AirDrop** or **email**
2. Open the file on Vision Pro — a profile installation screen will appear → tap **Install**
3. Go to **Settings → General → About → Certificate Trust Settings**
   → enable the toggle for `LNDIVC Local` → tap **Continue**

---

## Daily Usage

### Windows

1. Double-click `server/start.bat`
2. Note the URL shown in the terminal

```
=======================================================
  LNDIVC Server Running
  Open the URL below in Vision Pro Safari:

    https://my-pc.tail12345.ts.net:8443   ← Tailscale
    https://192.168.x.x:8443              ← Self-Signed
=======================================================
```

Or launch `LNDIVC.exe` (system tray GUI) if you are using the pre-built executable.

### Vision Pro

1. Open Safari and navigate to the URL above
2. Tap **Start Streaming**
3. Allow camera and microphone permissions
4. Wait for the status to show **Streaming**

### Zoom / Teams / PlayAbility settings

| Setting | Value |
|---------|-------|
| Camera | `OBS Virtual Camera` |
| Microphone | `CABLE Output (VB-Audio Virtual Cable)` |

---

## Testing & Verification

You can validate each stage of the pipeline individually, without needing Vision Pro connected.

### Step 1 — Verify server startup

After running `start.bat` (or `python server.py`), confirm the output looks like this:

```
=======================================================
  LNDIVC Server Running
  Open the URL below in Vision Pro Safari:

    https://my-pc.tail12345.ts.net:8443   ← Tailscale
    https://192.168.x.x:8443              ← Self-Signed

  Virtual Camera: OBS Virtual Camera       ← "Inactive" means OBS is not set up
  Audio Output:   VB-Audio CABLE Input     ← "Default Speaker" means VB-Cable not found
=======================================================
```

| Item | Expected | Problem if wrong |
|------|----------|-----------------|
| cert.pem / key.pem | Server starts without errors | Run `setup.bat` first |
| Virtual Camera | `OBS Virtual Camera` | OBS not installed or virtual cam not started |
| Audio Output | `VB-Audio CABLE Input` | VB-Audio Cable not installed |

---

### Step 2 — Verify HTTPS from your PC browser

Open the server URL in Windows Chrome or Edge to confirm connectivity before using Vision Pro.

1. Navigate to `https://192.168.x.x:8443` (or your Tailscale address)
2. **Tailscale mode:** padlock icon appears → connection is valid
3. **Self-signed mode:** "Not secure" warning → click **Advanced → Continue** → page loads

> If the page opens from your PC, the server, certificates, and network are all working correctly.

---

### Step 3 — Verify WebSocket signaling (browser DevTools)

Open the page in your PC browser, press F12 → **Network** tab → filter by `WS`.

1. Click **Start Streaming** on the page
2. Confirm `wss://…/ws` shows a **101 Switching Protocols** status
3. In the **Messages** tab, verify `offer` and `answer` messages are exchanged

---

### Step 4 — Test Vision Pro connection

1. Navigate to the server URL in Vision Pro Safari
2. Tap **Start Streaming** → grant camera and microphone permissions
3. Status should change to **✅ Streaming** when WebRTC connects successfully
4. Confirm the following lines appear in the Windows terminal:

```
WebRTC state: connected
Video track received
Audio track received
```

---

### Step 5 — Verify virtual camera output

1. Open the **Camera** app on Windows → click the switch camera button at the top
2. Select `OBS Virtual Camera`
3. If the Vision Pro persona video appears, the video pipeline is working

> You can also verify in OBS Studio's preview window instead of the Camera app.

---

### Step 6 — Verify virtual audio output

1. Open Windows **Settings → System → Sound → Volume Mixer**
2. Select the `CABLE Output (VB-Audio Virtual Cable)` device and speak from Vision Pro
3. If the level meter moves, the audio pipeline is working

---

### Step 7 — Zoom integration test

| Location | Value |
|----------|-------|
| Zoom Settings → Video → Camera | `OBS Virtual Camera` |
| Zoom Settings → Audio → Microphone | `CABLE Output (VB-Audio Virtual Cable)` |

1. Start a Zoom test meeting → confirm persona video appears in the video preview
2. Test the microphone → record and play back to confirm Vision Pro audio is captured

---

### Troubleshooting Decision Table

| Symptom | Suspect step | How to check |
|---------|--------------|-------------|
| Server exits immediately | Step 1 | Check that cert.pem / key.pem exist |
| Page won't open in browser | Step 2 | Allow port 8443 in Windows Firewall |
| Status stuck at "Negotiating" | Step 3 | Check WS tab in browser DevTools |
| Connected but no image in Camera app | Step 5 | Enable OBS Virtual Camera |
| No audio in Zoom microphone | Step 6 | Install VB-Audio Cable and restart Windows |

---

## Build a Standalone .exe (Optional)

Generate a self-contained executable that runs on PCs without Python installed.

```
Double-click server/build.bat
  → creates dist/LNDIVC/ folder
```

**Distribution:**
1. Copy the entire `dist/LNDIVC/` folder to the target PC
2. Run `LNDIVC.exe --setup` → complete certificate configuration
3. Run `LNDIVC.exe` → server starts via the system tray GUI

> OBS Studio and VB-Audio Virtual Cable must be installed separately on the target PC.

---

## File Structure

```
LNDIVC/
├── README.md
└── server/
    ├── server.py           # Core server — HTTPS + WebSocket + WebRTC (aiortc)
    ├── tray_app.py         # System tray GUI (customtkinter + pystray)
    ├── setup_wizard.py     # Certificate setup wizard (Tailscale / Self-Signed)
    ├── generate_cert.py    # Self-signed certificate generator
    ├── i18n.py             # Localization — Korean / English
    ├── install_drivers.py  # OBS / VB-Audio driver detection
    ├── requirements.txt    # Python dependencies
    ├── setup.bat           # First-time setup script
    ├── start.bat           # Server launch script
    ├── build.bat           # PyInstaller .exe build script
    ├── LNDIVC.spec         # PyInstaller configuration
    └── static/
        └── index.html      # Vision Pro Safari client page
```

---

## Troubleshooting

### "This connection is not secure" in Safari (Self-Signed mode)

The certificate trust step was not completed.
Clicking **Advanced → Visit this website** on the warning page will still block `getUserMedia`. Complete the profile trust step described in [Mode B](#mode-b--self-signed-local-network-only) above.
Switch to **Tailscale mode** to skip this step entirely.

### Tailscale certificate issuance fails

Make sure **MagicDNS** and **HTTPS** are both enabled at [admin.tailscale.com/dns](https://login.tailscale.com/admin/dns).
Tailscale must also be installed and signed in on your Vision Pro to access the Tailscale hostname.

### Camera permission is repeatedly denied

Check **Settings → Privacy & Security → Camera** on Vision Pro and ensure Safari has permission.

### OBS Virtual Camera not in the camera list

Open OBS Studio → **Tools → Start Virtual Camera**. The virtual camera stays active after OBS is closed.

### Microphone not appearing in Zoom

Install VB-Audio Virtual Cable, then restart Windows.
In Zoom microphone settings, select `CABLE Output (VB-Audio Virtual Cable)`.

### IP address changed, can't connect (Self-Signed mode)

The current IP is printed in the terminal each time `start.bat` is run.
Switch to **Tailscale mode** to get a stable hostname that doesn't change with IP reassignments.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Streaming protocol | WebRTC (browser ↔ aiortc) |
| Signaling | WebSocket over WSS (aiohttp) |
| Video codec | H.264 / VP8 (auto-negotiated) |
| Audio codec | Opus 48 kHz mono |
| Virtual camera | pyvirtualcam → OBS Virtual Camera driver |
| Virtual audio | sounddevice → VB-Audio Virtual Cable |
| Certificates | Tailscale (Let's Encrypt) or self-signed (cryptography) |
| GUI | customtkinter + pystray |
| Distribution | PyInstaller |

---

## License

MIT
