# 📱 ZORIN AI ASSISTANT - ANDROID MULTI-DEVICE ARCHITECTURE & INTEGRATION GUIDE

This document defines the complete architecture, network protocol, and connection specifications for integrating Android smartphones, tablets, and mobile clients with the central ZORIN AI Assistant.

---

## 1. Architectural Overview

```
                      ┌──────────────────────────────────────────────┐
                      │          ZORIN CENTRAL AI HUB                │
                      │  FastAPI + WebSocket + Gemini Live Engine   │
                      │         (Binds 0.0.0.0:8000)                 │
                      └──────┬───────────────────────┬───────────────┘
                             │                       │
           WebSocket & REST  │                       │  WebSocket & REST
                             ▼                       ▼
      ┌─────────────────────────────┐        ┌─────────────────────────────┐
      │     WINDOWS LAPTOP NODE     │        │    ANDROID MOBILE CLIENT    │
      │  - PySide6 Animated GUI     │        │  - PWA / Native Kotlin App  │
      │  - Vosk Wake-Word Engine    │        │  - Speech Recognition / Mic │
      │  - Audio In / Audio Out     │        │  - Shared Persistent Memory │
      │  - App Execution Controller │        │  - Cross-Device Chat Stream │
      └─────────────────────────────┘        └─────────────────────────────┘
                             │                       │
                             └───────────┬───────────┘
                                         ▼
                      ┌──────────────────────────────────────────────┐
                      │         UNIFIED SHARED MEMORY VAULT          │
                      │  - Shared Conversation History               │
                      │  - Protected Core Memory (Never Overwritten) │
                      │  - Extracted Long-Term Facts                 │
                      │  - Real-Time Device Status Registry          │
                      └──────────────────────────────────────────────┘
```

ZORIN operates as **ONE Central AI Brain**. Connected devices do **not** run isolated AI models; they stream input to and receive responses from the same central brain. When a conversation occurs on Android, the Windows laptop immediately shares the updated memory and conversation history.

---

## 2. Android Connection Modes

### Mode A: Progressive Web App (Zero Setup, Ready Now)
1. Ensure your Android smartphone is connected to the same Wi-Fi network as the laptop.
2. Open **Google Chrome** on Android and navigate to:
   ```
   http://<LAPTOP_LOCAL_IP>:8000
   ```
   *(e.g., `http://192.168.1.27:8000`)*
3. On the laptop, click **📱 DEVICES** in the ZORIN interface or click the top Central Hub badge.
4. Under the **Pair Android / Phone** tab, note the **6-digit pairing PIN** or scan the **QR Code**.
5. On your phone, enter the PIN and tap **Pair**.
6. Tap Chrome's menu (`⋮`) -> **Add to Home Screen** to install ZORIN as a standalone Android app.

### Mode B: Native Android Client (Kotlin / Jetpack Compose)
A native Android application can connect using OkHttp WebSockets and Retrofit REST APIs.

---

## 3. Communication Protocol & APIs

### 3.1 Device Pairing (`POST /api/devices/pair/confirm`)
Links a new Android phone to the user account using the 6-digit PIN.

**Request:**
```http
POST /api/devices/pair/confirm HTTP/1.1
Host: 192.168.1.27:8000
Content-Type: application/json

{
  "pin_or_token": "471683",
  "identity": {
    "device_id": "android-samsung-s24-001",
    "device_name": "Niharika's Galaxy S24",
    "operating_system": "Android 14",
    "client_type": "mobile",
    "device_type": "android_phone",
    "has_microphone": true,
    "has_speaker": true,
    "capabilities": ["voice_input", "audio_output", "camera", "notifications", "shared_memory"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Device 'Niharika's Galaxy S24' successfully paired with ZORIN!",
  "device": {
    "device_id": "android-samsung-s24-001",
    "device_name": "Niharika's Galaxy S24",
    "status": "online",
    "is_default": 0
  },
  "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### 3.2 Real-Time WebSocket Channel (`/ws/device/{device_id}`)
Maintains persistent bi-directional communication between Android and the central hub.

**URL:**
```
ws://<SERVER_IP>:8000/ws/device/android-samsung-s24-001?token=<AUTH_TOKEN>
```

#### Handshake (Sent by Android upon connection):
```json
{
  "type": "handshake",
  "identity": {
    "device_id": "android-samsung-s24-001",
    "device_name": "Niharika's Galaxy S24",
    "operating_system": "Android 14",
    "client_type": "mobile",
    "device_type": "android_phone",
    "capabilities": ["voice_input", "audio_output", "notifications"]
  }
}
```

#### Heartbeat (Every 30 seconds):
```json
{ "type": "ping" }
```
*Server replies with:*
```json
{ "type": "pong" }
```

---

### 3.3 Assistant Chat with Shared Memory (`POST /api/assistant/chat`)
Streams user voice transcript or text query to the central Gemini Live brain with automatic memory injection.

**Request:**
```http
POST /api/assistant/chat HTTP/1.1
Host: 192.168.1.27:8000
Authorization: Bearer <AUTH_TOKEN>
Content-Type: application/json

{
  "message": "Open Chrome on my laptop and remember I have an exam tomorrow",
  "conversation_id": "shared_thread_001",
  "target_device": "test-win-pc-001"
}
```

**Response:**
```json
{
  "success": true,
  "reply": "I've opened Chrome on your laptop, and I've noted that you have an exam tomorrow.",
  "tool_results": [
    {
      "action": "open_app",
      "success": true,
      "message": "Opened Chrome."
    },
    {
      "action": "save_memory",
      "success": true,
      "message": "Saved to long-term memory: Exam scheduled for tomorrow."
    }
  ],
  "conversation_id": "shared_thread_001",
  "voice": "Aoede"
}
```

---

### 3.4 Shared Memory Management (`GET /api/memory` & `POST /api/memory`)
Android clients have full read/write access to the central memory vault.

* **Retrieve Memories:** `GET /api/memory`
* **Filter Core Memories:** `GET /api/memory?core_only=true`
* **Add Memory:** `POST /api/memory` (body: `{"category": "work", "content": "Project due Friday", "importance": 2, "is_core": false}`)
* **Pin to Protected Core Memory:** `PATCH /api/memory/{id}/pin`
* **Delete Memory:** `DELETE /api/memory/{id}` *(Core memory requires explicit confirmation)*

---

## 4. Sample Native Android Kotlin WebSocket Client

For developers implementing a dedicated native APK using Kotlin and OkHttp:

```kotlin
package ai.zorin.mobile

import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class ZorinDeviceAgent(
    private val serverUrl: String,
    private val deviceId: String,
    private val authToken: String
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null

    fun connect() {
        val wsUrl = "$serverUrl/ws/device/$deviceId?token=$authToken"
        val request = Request.Builder().url(wsUrl).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                // Send Handshake
                val handshake = JSONObject().apply {
                    put("type", "handshake")
                    put("identity", JSONObject().apply {
                        put("device_id", deviceId)
                        put("device_name", android.os.Build.MODEL)
                        put("operating_system", "Android " + android.os.Build.VERSION.RELEASE)
                        put("client_type", "mobile")
                        put("device_type", "android_phone")
                        put("has_microphone", true)
                        put("has_speaker", true)
                    })
                }
                webSocket.send(handshake.toString())
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val data = JSONObject(text)
                when (data.optString("type")) {
                    "execute_command" -> handleRemoteCommand(data)
                    "device_status_changed" -> onDeviceStatusChanged(data)
                }
            }
        })
    }

    private fun handleRemoteCommand(data: JSONObject) {
        val commandId = data.getString("command_id")
        val action = data.getString("action")
        
        // Execute local action on phone (e.g. trigger notification, play sound)
        val reply = JSONObject().apply {
            put("type", "command_result")
            put("command_id", commandId)
            put("result", JSONObject().apply { put("success", true) })
        }
        webSocket?.send(reply.toString())
    }

    private fun onDeviceStatusChanged(data: JSONObject) {
        // Update Android UI device indicators
    }
}
```

---

## 5. Security & Verification

1. **Token Authentication:** Every WebSocket and REST transaction requires a signed JWT token or valid 6-digit one-time PIN.
2. **Local Subnet Privacy:** The hub binds to `0.0.0.0:8000`, accepting connections exclusively across the local Wi-Fi / VPN subnet.
3. **Core Memory Safety:** Remote mobile clients cannot silently erase protected Core Memory without explicit confirmation flags.
