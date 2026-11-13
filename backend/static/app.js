// ZORIN Universal Multi-Device Client Application
// Cross-device Voice, Text, Memory & Remote Device Control Engine

class ZorinApp {
  constructor() {
    this.token = localStorage.getItem('zorin_token') || '';
    this.currentUser = null;
    this.devices = [];
    this.activeTargetDeviceId = null;
    this.conversationId = 'session_' + Math.random().toString(36).substring(2, 9);
    this.isListening = false;
    this.isSpeaking = false;
    this.recognition = null;
    this.ws = null;
    this.synth = window.speechSynthesis;

    this.initDOMElements();
    this.initSpeechRecognition();
    this.initEventListeners();
    this.initWebSocket();
    this.bootstrapApp();
    this.registerServiceWorker();
  }

  initDOMElements() {
    this.dom = {
      aiOrb: document.getElementById('aiOrb'),
      orbStatus: document.getElementById('orbStatus'),
      chatStream: document.getElementById('chatStream'),
      textInput: document.getElementById('textInput'),
      btnMic: document.getElementById('btnMic'),
      btnSend: document.getElementById('btnSend'),
      deviceList: document.getElementById('deviceListContainer'),
      btnRefreshDevices: document.getElementById('btnRefreshDevices'),
      btnAccount: document.getElementById('btnAccount'),
      btnMemories: document.getElementById('btnMemories'),
      accountModal: document.getElementById('accountModal'),
      memoryModal: document.getElementById('memoryModal'),
      btnCloseAccount: document.getElementById('btnCloseAccount'),
      btnCloseMemory: document.getElementById('btnCloseMemory'),
      authSectionLoggedOut: document.getElementById('authSectionLoggedOut'),
      authSectionLoggedIn: document.getElementById('authSectionLoggedIn'),
      authToggleLink: document.getElementById('authToggleLink'),
      authToggleText: document.getElementById('authToggleText'),
      groupDisplayName: document.getElementById('groupDisplayName'),
      btnSubmitAuth: document.getElementById('btnSubmitAuth'),
      modalTitle: document.getElementById('modalTitle'),
      authEmail: document.getElementById('authEmail'),
      authPassword: document.getElementById('authPassword'),
      authDisplayName: document.getElementById('authDisplayName'),
      profileDisplayName: document.getElementById('profileDisplayName'),
      profileEmail: document.getElementById('profileEmail'),
      selectVoice: document.getElementById('selectVoice'),
      btnSavePreferences: document.getElementById('btnSavePreferences'),
      btnLogout: document.getElementById('btnLogout'),
      memoryList: document.getElementById('memoryList'),
      newMemoryInput: document.getElementById('newMemoryInput'),
      btnAddMemory: document.getElementById('btnAddMemory'),
      hubStatusText: document.getElementById('hubStatusText')
    };
    this.isRegisterMode = false;
  }

  // -------------------------------------------------------------
  // SPEECH RECOGNITION (Universal Browser Voice)
  // -------------------------------------------------------------
  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'en-US';

      this.recognition.onstart = () => {
        this.isListening = true;
        this.dom.btnMic.classList.add('active');
        this.dom.aiOrb.classList.add('listening');
        this.dom.orbStatus.textContent = "Listening to your voice...";
      };

      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript.trim()) {
          this.handleSendMessage(transcript);
        }
      };

      this.recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        this.stopListening();
        this.dom.orbStatus.textContent = "Could not hear audio clearly. Tap mic to retry.";
      };

      this.recognition.onend = () => {
        this.stopListening();
      };
    } else {
      console.warn("Browser SpeechRecognition API not supported. Using keyboard input.");
    }
  }

  toggleListening() {
    if (!this.recognition) {
      alert("Voice recognition is not supported in this browser. Please use text input or Chrome/Safari.");
      return;
    }

    if (this.isListening) {
      this.recognition.stop();
    } else {
      try {
        this.recognition.start();
      } catch (e) {
        console.warn("Recognition start error:", e);
      }
    }
  }

  stopListening() {
    this.isListening = false;
    this.dom.btnMic.classList.remove('active');
    this.dom.aiOrb.classList.remove('listening');
    if (!this.isSpeaking) {
      this.dom.orbStatus.textContent = "ZORIN is standing by.";
    }
  }

  // -------------------------------------------------------------
  // SPEECH SYNTHESIS (Voice Response)
  // -------------------------------------------------------------
  speakText(text) {
    if (!this.synth) return;

    // Do not speak in browser if web audio is muted or on desktop PC
    // where the native ZORIN desktop app is already playing high-quality audio
    const isMobile = /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);
    if (!isMobile || localStorage.getItem('zorin_web_muted') === 'true') {
      return;
    }

    // Cancel existing utterance
    this.synth.cancel();

    // Clean text of markdown asterisks/brackets
    const cleanText = text.replace(/[*_#`\[\]]/g, '').trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    const voices = this.synth.getVoices();
    const voicePref = this.currentUser?.voice_preference || 'Aoede';
    const isFemale = voicePref.toLowerCase() === 'aoede' || voicePref.toLowerCase() === 'female';

    const preferredVoice = voices.find(v => {
      const name = v.name.toLowerCase();
      return isFemale
        ? (name.includes('female') || name.includes('zira') || name.includes('samantha') || name.includes('victoria') || name.includes('karen'))
        : (name.includes('male') || name.includes('david') || name.includes('alex') || name.includes('daniel'));
    }) || voices[0];

    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.dom.aiOrb.classList.add('speaking');
      this.dom.orbStatus.textContent = "ZORIN is speaking...";
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.dom.aiOrb.classList.remove('speaking');
      this.dom.orbStatus.textContent = "ZORIN is standing by.";
    };

    utterance.onerror = () => {
      this.isSpeaking = false;
      this.dom.aiOrb.classList.remove('speaking');
      this.dom.orbStatus.textContent = "ZORIN is standing by.";
    };

    this.synth.speak(utterance);
  }

  // -------------------------------------------------------------
  // WEBSOCKET (Real-Time Device Synchronization)
  // -------------------------------------------------------------
  initWebSocket() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const clientId = 'web_' + Math.random().toString(36).substring(2, 9);
    const wsUrl = `${proto}//${window.location.host}/ws/client/${clientId}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.dom.hubStatusText.textContent = "Hub Connected";
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'device_status_changed') {
            console.log("Device status push received:", data);
            this.fetchDevices();
          }
        } catch (e) {}
      };

      this.ws.onclose = () => {
        this.dom.hubStatusText.textContent = "Reconnecting...";
        setTimeout(() => this.initWebSocket(), 4000);
      };
    } catch (e) {
      console.warn("WebSocket init failed:", e);
    }
  }

  // -------------------------------------------------------------
  // EVENT LISTENERS
  // -------------------------------------------------------------
  initEventListeners() {
    // Mic button
    this.dom.btnMic.addEventListener('click', () => this.toggleListening());
    this.dom.aiOrb.addEventListener('click', () => this.toggleListening());

    // Send button
    this.dom.btnSend.addEventListener('click', () => {
      const text = this.dom.textInput.value.trim();
      if (text) {
        this.handleSendMessage(text);
        this.dom.textInput.value = '';
      }
    });

    // Enter key
    this.dom.textInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const text = this.dom.textInput.value.trim();
        if (text) {
          this.handleSendMessage(text);
          this.dom.textInput.value = '';
        }
      }
    });

    // Suggestion chips
    document.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const prompt = chip.getAttribute('data-prompt');
        if (prompt) {
          this.handleSendMessage(prompt);
        }
      });
    });

    // Quick action buttons in sidebar
    document.querySelectorAll('.quick-btn[data-action]').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-action');
        const param = btn.getAttribute('data-param');
        this.executeQuickAction(action, param);
      });
    });

    // Refresh devices
    this.dom.btnRefreshDevices.addEventListener('click', () => this.fetchDevices());

    // Modal controls
    this.dom.btnAccount.addEventListener('click', () => this.openAccountModal());
    this.dom.btnCloseAccount.addEventListener('click', () => this.closeAccountModal());
    this.dom.btnMemories.addEventListener('click', () => this.openMemoryModal());
    this.dom.btnCloseMemory.addEventListener('click', () => this.closeMemoryModal());

    // Auth toggles
    this.dom.authToggleLink.addEventListener('click', (e) => {
      e.preventDefault();
      this.isRegisterMode = !this.isRegisterMode;
      this.updateAuthFormUI();
    });

    this.dom.btnSubmitAuth.addEventListener('click', () => this.submitAuth());
    this.dom.btnLogout.addEventListener('click', () => this.logout());
    this.dom.btnSavePreferences.addEventListener('click', () => this.savePreferences());

    // Memory actions
    this.dom.btnAddMemory.addEventListener('click', () => this.addMemory());
    this.dom.newMemoryInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.addMemory();
    });

    // Device PIN Pairing
    const btnSubmitPair = document.getElementById('btnSubmitPair');
    const inputPairPin = document.getElementById('inputPairPin');
    const pairStatusMsg = document.getElementById('pairStatusMsg');

    if (btnSubmitPair && inputPairPin) {
      btnSubmitPair.addEventListener('click', async () => {
        const pin = inputPairPin.value.trim();
        if (!pin) return;
        pairStatusMsg.style.display = 'block';
        pairStatusMsg.style.color = '#67E8F9';
        pairStatusMsg.textContent = 'Verifying PIN with central hub...';

        const isAndroid = /Android/i.test(navigator.userAgent);
        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        const devName = isAndroid ? 'Android Smartphone' : (isIOS ? 'Apple iPhone' : 'Mobile Web Client');

        const identity = {
          device_id: 'phone-' + Math.random().toString(36).substring(2, 10),
          device_name: devName,
          operating_system: isAndroid ? 'Android' : (isIOS ? 'iOS' : 'Mobile Web'),
          client_type: 'mobile',
          device_type: isAndroid ? 'android_phone' : (isIOS ? 'iphone' : 'mobile'),
          has_microphone: true,
          has_speaker: true,
          capabilities: ['voice_input', 'audio_output', 'shared_memory']
        };

        try {
          const resp = await fetch('/api/devices/pair/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin_or_token: pin, identity })
          });
          const result = await resp.json();
          if (resp.ok && result.success) {
            pairStatusMsg.style.color = '#34D399';
            pairStatusMsg.textContent = '✓ ' + result.message;
            if (result.auth_token) {
              this.token = result.auth_token;
              localStorage.setItem('zorin_token', result.auth_token);
              await this.fetchCurrentUser();
              await this.fetchDevices();
            }
          } else {
            pairStatusMsg.style.color = '#F87171';
            pairStatusMsg.textContent = '✕ ' + (result.detail || result.error || 'Failed to pair device.');
          }
        } catch (err) {
          pairStatusMsg.style.color = '#F87171';
          pairStatusMsg.textContent = '✕ Network error connecting to hub.';
        }
      });
    }
  }

  // -------------------------------------------------------------
  // BOOTSTRAP APP & AUTH
  // -------------------------------------------------------------
  async bootstrapApp() {
    await this.fetchCurrentUser();
    await this.fetchDevices();
  }

  async fetchCurrentUser() {
    try {
      const headers = this.getAuthHeaders();
      const res = await fetch('/api/auth/me', { headers });
      if (res.ok) {
        const data = await res.json();
        this.currentUser = data.user;
        this.renderUserUI();
      } else {
        // Fallback to anonymous/demo
        this.currentUser = null;
        this.renderUserUI();
      }
    } catch (e) {
      console.warn("User fetch error:", e);
    }
  }

  getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  renderUserUI() {
    if (this.currentUser) {
      this.dom.authSectionLoggedOut.style.display = 'none';
      this.dom.authSectionLoggedIn.style.display = 'block';
      this.dom.profileDisplayName.textContent = this.currentUser.display_name || 'User';
      this.dom.profileEmail.textContent = this.currentUser.email || '';
      if (this.currentUser.voice_preference) {
        this.dom.selectVoice.value = this.currentUser.voice_preference;
      }
    } else {
      this.dom.authSectionLoggedOut.style.display = 'block';
      this.dom.authSectionLoggedIn.style.display = 'none';
    }
  }

  updateAuthFormUI() {
    if (this.isRegisterMode) {
      this.dom.modalTitle.textContent = "Create Account";
      this.dom.groupDisplayName.style.display = 'block';
      this.dom.btnSubmitAuth.textContent = "Register";
      this.dom.authToggleText.textContent = "Already have an account?";
      this.dom.authToggleLink.textContent = "Sign In";
    } else {
      this.dom.modalTitle.textContent = "Sign In";
      this.dom.groupDisplayName.style.display = 'none';
      this.dom.btnSubmitAuth.textContent = "Sign In";
      this.dom.authToggleText.textContent = "Need an account?";
      this.dom.authToggleLink.textContent = "Register";
    }
  }

  async submitAuth() {
    const email = this.dom.authEmail.value.trim();
    const password = this.dom.authPassword.value.trim();
    const displayName = this.dom.authDisplayName.value.trim();

    if (!email || !password) {
      alert("Please enter both email and password.");
      return;
    }

    const endpoint = this.isRegisterMode ? '/api/auth/register' : '/api/auth/login';
    const body = { email, password };
    if (this.isRegisterMode) body.display_name = displayName;

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (res.ok && data.success) {
        this.token = data.token;
        localStorage.setItem('zorin_token', this.token);
        this.currentUser = data.user;
        this.renderUserUI();
        this.fetchDevices();
        this.closeAccountModal();
      } else {
        alert(data.detail || "Authentication failed.");
      }
    } catch (e) {
      alert("Connection error: " + e.message);
    }
  }

  logout() {
    this.token = '';
    localStorage.removeItem('zorin_token');
    this.currentUser = null;
    this.renderUserUI();
    this.fetchDevices();
  }

  async savePreferences() {
    const voicePref = this.dom.selectVoice.value;
    try {
      const headers = this.getAuthHeaders();
      const res = await fetch('/api/auth/settings', {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ voice_preference: voicePref })
      });
      if (res.ok) {
        const data = await res.json();
        this.currentUser = data.user;
        alert("Preferences saved!");
        this.closeAccountModal();
      }
    } catch (e) {
      alert("Failed to save preferences.");
    }
  }

  // -------------------------------------------------------------
  // DEVICE ECOSYSTEM MANAGEMENT
  // -------------------------------------------------------------
  async fetchDevices() {
    try {
      const headers = this.getAuthHeaders();
      const res = await fetch('/api/devices', { headers });
      if (res.ok) {
        const data = await res.json();
        this.devices = data.devices || [];
        this.renderDevices();
      }
    } catch (e) {
      console.warn("Failed to fetch devices:", e);
    }
  }

  renderDevices() {
    const container = this.dom.deviceList;
    if (this.devices.length === 0) {
      container.innerHTML = `
        <div style="color:var(--text-muted);font-size:0.85rem;text-align:center;padding:16px;">
          No devices registered yet.<br>Run the ZORIN agent on your computer to connect it.
        </div>
      `;
      return;
    }

    container.innerHTML = this.devices.map(dev => {
      const isOnline = Boolean(dev.is_online);
      const isDefault = Boolean(dev.is_default);
      let osIcon = '💻';
      const osLower = (dev.operating_system || '').toLowerCase();
      if (osLower.includes('win')) osIcon = '🪟';
      else if (osLower.includes('mac') || osLower.includes('darwin')) osIcon = '🍎';
      else if (osLower.includes('linux')) osIcon = '🐧';
      else if (osLower.includes('android')) osIcon = '🤖';
      else if (osLower.includes('ios')) osIcon = '📱';

      return `
        <div class="device-item ${isDefault ? 'active-target' : ''}" data-device-id="${dev.device_id}">
          <div class="device-info">
            <span class="device-icon">${osIcon}</span>
            <div class="device-names">
              <h4>${dev.device_name} ${isDefault ? '★' : ''}</h4>
              <p>${dev.operating_system} • ${dev.client_type}</p>
            </div>
          </div>
          <div>
            <span class="device-status-pill ${isOnline ? 'online' : 'offline'}">
              ${isOnline ? '● Online' : 'Offline'}
            </span>
          </div>
        </div>
      `;
    }).join('');

    // Click to make default
    container.querySelectorAll('.device-item').forEach(item => {
      item.addEventListener('click', async () => {
        const devId = item.getAttribute('data-device-id');
        await this.setDefaultDevice(devId);
      });
    });
  }

  async setDefaultDevice(deviceId) {
    try {
      const headers = this.getAuthHeaders();
      const res = await fetch(`/api/devices/${deviceId}/default`, {
        method: 'POST',
        headers
      });
      if (res.ok) {
        await this.fetchDevices();
      }
    } catch (e) {
      console.warn("Failed to set default device:", e);
    }
  }

  async executeQuickAction(action, param) {
    let prompt = "";
    if (action === 'open_app') {
      prompt = `Open ${param} on my computer`;
    }
    this.handleSendMessage(prompt);
  }

  // -------------------------------------------------------------
  // CHAT & CONVERSATION
  // -------------------------------------------------------------
  async handleSendMessage(text) {
    text = text.trim();
    if (!text) return;

    // Append user message to UI
    this.appendMessage('user', text);

    // Orb to thinking state
    this.dom.aiOrb.classList.add('listening');
    this.dom.orbStatus.textContent = "ZORIN is thinking & routing commands...";

    try {
      const headers = this.getAuthHeaders();
      const res = await fetch('/api/assistant/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: text,
          conversation_id: this.conversationId,
          target_device: this.activeTargetDeviceId
        })
      });

      const data = await res.json();
      this.dom.aiOrb.classList.remove('listening');

      if (res.ok && data.success) {
        // Display tool execution badges if any occurred
        if (data.tool_results && data.tool_results.length > 0) {
          data.tool_results.forEach(tr => {
            const toolMsg = `⚡ Remote Action: [${tr.tool}] on ${tr.result?.target_device_name || 'Device'} (${tr.result?.success ? 'Success' : 'Failed'})`;
            this.appendMessage('tool-event', toolMsg);
          });
        }

        // Append assistant response
        this.appendMessage('assistant', data.reply);

        // Speak aloud
        this.speakText(data.reply);
      } else {
        this.appendMessage('assistant', data.reply || "Sorry, I encountered an error processing your request.");
      }
    } catch (e) {
      this.dom.aiOrb.classList.remove('listening');
      this.appendMessage('assistant', "Network connection error. Please ensure the ZORIN server is reachable.");
    }
  }

  appendMessage(role, content) {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${role}`;
    bubble.textContent = content;
    this.dom.chatStream.appendChild(bubble);
    this.dom.chatStream.scrollTop = this.dom.chatStream.scrollHeight;
  }

  // -------------------------------------------------------------
  // MEMORY INSPECTOR
  // -------------------------------------------------------------
  async openMemoryModal() {
    this.dom.memoryModal.classList.add('open');
    await this.fetchMemories();
  }

  closeMemoryModal() {
    this.dom.memoryModal.classList.remove('open');
  }

  async fetchMemories() {
    try {
      const headers = this.getAuthHeaders();
      const res = await fetch('/api/memory', { headers });
      if (res.ok) {
        const data = await res.json();
        this.renderMemories(data.memories || []);
      }
    } catch (e) {
      console.warn("Memory fetch error:", e);
    }
  }

  renderMemories(memories) {
    const list = this.dom.memoryList;
    if (memories.length === 0) {
      list.innerHTML = `<div style="font-size:0.85rem;color:var(--text-muted);text-align:center;padding:16px;">No saved memories found. Say "Remember that I like..." or add one below!</div>`;
      return;
    }

    list.innerHTML = memories.map(m => `
      <div style="background:rgba(255,255,255,0.03);border:1px solid var(--border-glass);border-radius:var(--radius-sm);padding:8px 12px;display:flex;align-items:center;justify-content:space-between;">
        <span style="font-size:0.88rem;">${m.content}</span>
        <button onclick="window.zorinApp.deleteMemory(${m.id})" style="background:none;border:none;color:var(--accent-red);cursor:pointer;font-size:0.9rem;padding:4px;">✕</button>
      </div>
    `).join('');
  }

  async addMemory() {
    const text = this.dom.newMemoryInput.value.trim();
    if (!text) return;

    try {
      const headers = this.getAuthHeaders();
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers,
        body: JSON.stringify({ category: 'user_note', content: text, importance: 2 })
      });
      if (res.ok) {
        this.dom.newMemoryInput.value = '';
        await this.fetchMemories();
      }
    } catch (e) {
      alert("Failed to add memory.");
    }
  }

  async deleteMemory(id) {
    try {
      const headers = this.getAuthHeaders();
      const res = await fetch(`/api/memory/${id}`, { method: 'DELETE', headers });
      if (res.ok) {
        await this.fetchMemories();
      }
    } catch (e) {
      alert("Failed to delete memory.");
    }
  }

  openAccountModal() {
    this.dom.accountModal.classList.add('open');
  }

  closeAccountModal() {
    this.dom.accountModal.classList.remove('open');
  }

  // -------------------------------------------------------------
  // SERVICE WORKER REGISTRATION (PWA)
  // -------------------------------------------------------------
  registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js').catch(err => {
        console.warn("Service worker registration skipped:", err);
      });
    }
  }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.zorinApp = new ZorinApp();
});
