# 🤖 ZORIN AI — Central Brain & Multi-Device Universal Assistant

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/niharika897/ZORIN)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/deploy?template=https://github.com/niharika897/ZORIN)

**ZORIN** is a next-generation personal AI assistant designed with a **single centralized AI brain** that connects across multiple computing devices (Windows laptops, Android smartphones, tablets, and web clients) with real-time voice barge-in, shared persistent memory, live 2026 web search, and a cyberpunk desktop interface.

---

## 🚀 1-Click Cloud Deployment

Deploy the Central AI Brain to the cloud in one click:

### Option 1: Deploy on Render (Recommended)
Click the button below to deploy on Render (free tier supported):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/niharika897/ZORIN)

1. Sign in to [Render](https://render.com).
2. Enter your `GEMINI_API_KEY`.
3. Click **Apply**. Render will automatically build the service and give you a permanent `https://<your-app>.onrender.com` URL.

### Option 2: Deploy on Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/deploy?template=https://github.com/niharika897/ZORIN)

---

## ⚡ Key Capabilities

- **🎙️ Real-Time Voice with Instant Barge-In:** Powered by Google Gemini Live. Interrupt ZORIN naturally at any moment while it is speaking, without delays or overlapping audio.
- **🧠 Single Centralized Brain & Shared Memory:** Long-term memories, user preferences, and conversation history are stored centrally and shared seamlessly across all your devices.
- **🛡️ Protected Core Memory:** Critical user facts and preferences are protected by `CoreMemoryProtectedError` and can never be silently overwritten or deleted without explicit user approval.
- **📡 Multi-Device Fleet Management:** Built-in Device Center to register, pair (via 6-digit PIN & QR code), monitor, and route commands across Windows PCs, Android phones, and Bluetooth audio peripherals.
- **🔍 Live 2026 Web Search:** Equipped with real-time web search to look up current 2026 events, breaking news, sports, and facts beyond model training cutoffs.
- **💻 Cyberpunk Desktop GUI:** PySide6 interface with an animated floating robot canvas, holographic rings, ambient particles, conversation history drawer, and hardware routing controls.

---

## 🖥️ How to Run Locally

### 1. Launch the Desktop Application
Double-click `LAUNCH_ZORIN.bat` or run:
```powershell
.\.venv\Scripts\python.exe -m desktop.app
```

### 2. Start the Central Hub Server
```powershell
python start_server.py
```
- Access from your laptop browser: `http://localhost:8000`
- Access from your smartphone on the same Wi-Fi: `http://<YOUR_LOCAL_IP>:8000`

---

## 📱 Pairing a Phone or Second Device
1. Open the Desktop Application and click **`📱 DEVICES`** (or open the live deployment link).
2. Go to the **Pair Android / Phone** tab.
3. Scan the QR code or enter the temporary 6-digit PIN on your phone to link it to your central brain.

---

## 📦 Windows Standalone Packaging
To bundle ZORIN into a standalone Windows executable (`.exe`):
```powershell
pip install pyinstaller
pyinstaller zorin_desktop.spec
```
The output executable will be generated in `dist/ZORIN_Assistant/ZORIN_Assistant.exe`.

---

## 📄 License & Attribution
Designed and built for personal AI autonomy and cross-device intelligence.
Repository: [https://github.com/niharika897/ZORIN](https://github.com/niharika897/ZORIN)
