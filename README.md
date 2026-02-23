# LNDIVC

**Stream your Apple Vision Pro Persona to Windows as a virtual webcam — no visionOS app required.**

LNDIVC captures your Vision Pro's front camera (Persona) and microphone over your local network and feeds them into Windows as a virtual camera and microphone. Any app that accepts a webcam input — Zoom, Teams, OBS, PlayAbility — works out of the box.

---

## How it works

```
Vision Pro Safari
  └─ getUserMedia() → Persona camera + mic
       └─ WebRTC  (local network or Tailscale VPN)
            └─ LNDIVC.exe  (Windows)
                 ├─ Video → OBS Virtual Camera  →  Zoom / Teams / OBS
                 └─ Audio → VB-Audio CABLE Input →  CABLE Output (mic)
```

No visionOS app installation needed. Vision Pro opens a local webpage in Safari; everything else is handled by the Windows app.

---

## Prerequisites

Python is **not** required — it is bundled inside the exe.

| Required | Download |
|----------|----------|
| OBS Studio (includes Virtual Camera driver) | https://obsproject.com |
| VB-Audio Virtual Cable *(optional — for mic input in Zoom/Teams)* | https://vb-audio.com/Cable |

> **OBS note:** After installing, open OBS once and click **Tools → Start Virtual Camera**. You can close OBS afterwards — the virtual camera driver stays active.

---

## Quick Start

1. Download **LNDIVC.zip** from the [Releases](../../releases) page
2. **Extract** the zip (do not run the exe from inside the zip)
3. Run **LNDIVC.exe**
4. A setup wizard appears on first launch — choose your language and certificate mode
5. Done. LNDIVC lives in your system tray.

Everything — start/stop server, settings, QR code, uninstall — is accessible from the tray icon. No terminal, no command line.

---

## Certificate Setup

HTTPS is required because browsers block `getUserMedia` on non-secure origins.
Choose one of two modes on first launch (changeable later via tray → Settings):

### Option A — Tailscale (Recommended)

No certificate trust configuration needed on Vision Pro. Works even if your PC's IP address changes.

1. Install [Tailscale](https://tailscale.com/download) on both your Windows PC and Vision Pro, and sign in to the same account
2. Go to [admin.tailscale.com/dns](https://login.tailscale.com/admin/dns) → enable **MagicDNS** and **HTTPS**
3. In the LNDIVC setup wizard, select **Tailscale** — the certificate is issued automatically

### Option B — Self-Signed

For local network use without Tailscale. Requires a one-time trust step on Vision Pro.

1. In the wizard, select **Self-Signed** — `cert.pem` is generated automatically
2. Transfer `cert.pem` to Vision Pro via **AirDrop or Mail**
3. Open the file on Vision Pro → install the profile
4. **Settings → General → About → Certificate Trust Settings** → enable **LNDIVC Local** → Continue

---

## Daily Usage

### Windows

Right-click the **LNDIVC tray icon** and select **Start Server**.
The icon turns orange (waiting) and then green once Vision Pro connects.
Use **Show QR Code** to get the connection URL.

### Vision Pro

1. Open **Safari** and navigate to the URL shown in the QR code window
2. Tap **Start Streaming**
3. Allow camera and microphone access
4. The status indicator turns green — streaming is active

### Zoom / Teams

| Setting | Value |
|---------|-------|
| Camera | `OBS Virtual Camera` |
| Microphone | `CABLE Output (VB-Audio Virtual Cable)` |

---

## Tray Menu Reference

| Menu Item | Description |
|-----------|-------------|
| Start / Stop Server | Toggle the WebRTC server |
| Show QR Code | Display connection URL and QR for Vision Pro |
| Settings | Change language or reconfigure certificate |
| OBS Status | Check virtual camera and VB-Audio availability |
| Uninstall | Remove config and certificate files |
| Quit | Stop server and exit |

---

## Troubleshooting

**"This connection is not secure" on Vision Pro (Self-Signed mode)**
→ The certificate trust step was not completed. Tapping through the warning still blocks `getUserMedia`. Complete the profile installation and trust steps, or switch to Tailscale mode.

**Tailscale certificate fails**
→ Confirm both **MagicDNS** and **HTTPS** are enabled at [admin.tailscale.com/dns](https://login.tailscale.com/admin/dns).
→ Vision Pro must also have Tailscale installed and signed in to the same account.

**Camera permission keeps being denied**
→ On Vision Pro: **Settings → Privacy & Security → Camera** → enable Safari.

**OBS Virtual Camera not showing up**
→ Open OBS Studio → **Tools → Start Virtual Camera**, then check tray → OBS Status.

**No microphone in Zoom**
→ Restart Windows after installing VB-Audio Virtual Cable.
→ In Zoom audio settings, select `CABLE Output (VB-Audio Virtual Cable)`.

**IP address changed, can't connect (Self-Signed mode)**
→ Open tray → Show QR Code for the current address. Switch to Tailscale to avoid this entirely.

---

## Building from Source

Requires Python 3.11+.

```
server/build.bat
```

`build.bat` is self-contained: it creates a virtual environment, installs all dependencies, runs PyInstaller, and outputs `dist/LNDIVC.zip` — ready to distribute.

### Repository layout

```
LNDIVC/
├── README.md
└── server/
    ├── tray_app.py        # Main entry point — tray icon + all GUI windows
    ├── server.py          # HTTPS + WebSocket + WebRTC server (aiohttp + aiortc)
    ├── setup_wizard.py    # Certificate setup logic (Tailscale / self-signed)
    ├── generate_cert.py   # Self-signed certificate generator
    ├── install_drivers.py # Driver status helper
    ├── i18n.py            # Korean / English strings
    ├── requirements.txt   # Python dependencies
    ├── build.bat          # PyInstaller build script → dist/LNDIVC.zip
    ├── LNDIVC.spec        # PyInstaller spec
    └── static/
        └── index.html     # Vision Pro Safari interface (WebRTC client)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Streaming protocol | WebRTC — aiortc |
| Signaling | WebSocket over WSS — aiohttp |
| Video codec | H.264 / VP8 (negotiated) |
| Audio codec | Opus 48 kHz mono |
| Virtual camera | pyvirtualcam → OBS Virtual Camera driver |
| Virtual microphone | sounddevice → VB-Audio Virtual Cable |
| Certificate | Tailscale (Let's Encrypt) or self-signed (cryptography) |
| GUI | pystray (tray) + customtkinter (windows) |
