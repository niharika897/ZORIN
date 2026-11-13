# ZORIN AI Assistant - Deployment & Production Architecture Guide

This guide details the deployment procedures for ZORIN across:
1. **Central AI Backend Hub** (Server / Cloud / Local Network)
2. **Windows Desktop Client** (PyInstaller Executable Distribution)
3. **Android Client Integration** (PWA & Native Kotlin Roadmap)

---

## 1. Central AI Backend Hub Deployment

The Central Hub manages Gemini AI communications, active WebSocket sessions, device registration, and persistent shared memory.

### Option A: Local Network Deployment (Windows / Linux)
To run the server across your home or office local network:
```powershell
# 1. Ensure .env is populated with GEMINI_API_KEY
copy .env.example .env

# 2. Start the server
python start_server.py
```
The server binds to `0.0.0.0:8000`, making it accessible to any device on your local Wi-Fi at `http://<YOUR_LOCAL_IP>:8000` (e.g. `http://192.168.1.27:8000`).

### Option B: Docker Container Deployment
Use Docker for automated, isolated production deployment:
```bash
# 1. Build and run container in background
docker compose up -d --build

# 2. Check health status
curl http://localhost:8000/health
```
Data persistence is preserved via the mounted `./data` volume.

---

## 2. Windows Desktop Client Packaging (PyInstaller)

To distribute ZORIN to other Windows computers without requiring Python installation:

### Build Process:
1. Ensure PyInstaller is installed:
   ```powershell
   pip install pyinstaller
   ```
2. Build using the provided specification file:
   ```powershell
   pyinstaller zorin_desktop.spec
   ```
3. The standalone distribution will be generated in `dist/ZORIN_Assistant/`.
4. Double-click `dist/ZORIN_Assistant/ZORIN_Assistant.exe` to run.

### Security on First-Run:
- API secrets and `.env` are intentionally **excluded** from the packaged binary.
- On first launch, the desktop application reads `.env` from its local folder or prompts the user for their Gemini API key, ensuring zero secret leakage.

---

## 3. Android Connectivity Roadmap

### Current Operational State:
- **Zero-Install Progressive Web App (PWA):** Open `http://<SERVER_IP>:8000` on Chrome or Firefox on your Android phone.
- **6-Digit PIN Pairing:** In the desktop Device Center, navigate to *📱 Pair Android / Phone*, generate a PIN, and enter it into the mobile web client.
- **Microphone & Speaker Streaming:** Mobile browsers stream audio directly to the Central Hub over WebSockets.

### Native Kotlin Android Client Roadmap:
To build a fully native Android APK:
1. Implement `ZorinWebSocketClient.kt` as specified in [ANDROID_ARCHITECTURE_GUIDE.md](file:///c:/Users/Niharika/OneDrive/Desktop/ZORIN/ANDROID_ARCHITECTURE_GUIDE.md).
2. Use Android `AudioRecord` (16kHz PCM mono) for voice input.
3. Use Android `AudioTrack` (24kHz PCM mono) for streaming speech output.
4. Authenticate via `POST /api/devices/pair/confirm` using the temporary 6-digit PIN.
