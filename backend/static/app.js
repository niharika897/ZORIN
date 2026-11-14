/**
 * ZORIN AI - UNIVERSAL WEB CLIENT (DESKTOP TWIN)
 * Replicates desktop/modern_ui.py RobotWidget, Cyberpunk styling,
 * voice conversation, barge-in, and multi-device hub features.
 */

// =========================================================
// APPLICATION STATE
// =========================================================
const state = {
  robotState: 'idle', // 'idle' | 'listening' | 'thinking' | 'speaking'
  isVoiceActive: false,
  activeConversationId: null,
  conversations: [],
  recognition: null,
  currentAudioUtterance: null,
  voicePreference: 'Aoede',
  deviceFleet: []
};

// =========================================================
// HTML5 CANVAS: ROBOT WIDGET (EXACT PORT OF RobotWidget)
// =========================================================
class RobotCanvas {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.t = 0;

    // 65 ambient particles drifting upwards
    this.particles = Array.from({ length: 65 }, () => ({
      x: Math.random(),
      y: Math.random(),
      size: 1 + Math.random() * 2.2
    }));

    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  drawGlow(x, y, radius, colorHex, alpha) {
    const ctx = this.ctx;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
    grad.addColorStop(0, `rgba(${colorHex}, ${alpha})`);
    grad.addColorStop(1, `rgba(${colorHex}, 0)`);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  drawRoundedRect(x, y, w, h, r) {
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  animate() {
    this.t++;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const cx = w / 2;
    const cy = h / 2 - 10;

    // Update particles
    for (const p of this.particles) {
      p.y -= 0.002;
      if (p.y < 0) p.y = 1;
    }

    // 1. Clear with base background
    ctx.fillStyle = '#100D22';
    ctx.fillRect(0, 0, w, h);

    // 2. Ambient dust particles
    for (const p of this.particles) {
      ctx.fillStyle = 'rgba(190, 130, 255, 0.5)';
      ctx.beginPath();
      ctx.arc(p.x * w, p.y * h, p.size, 0, Math.PI * 2);
      ctx.fill();
    }

    // 3. Central background aura glow
    this.drawGlow(cx, cy, 190, '120, 50, 255', 0.3);

    // 4. Holographic concentric dashed rings
    for (let i = 0; i < 3; i++) {
      ctx.save();
      ctx.translate(cx, cy);
      const angle = (this.t * (i % 2 === 0 ? 1 : -1) * Math.PI) / 180;
      ctx.rotate(angle);

      ctx.strokeStyle = `rgba(150, 110, 255, ${0.5 - i * 0.1})`;
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 6]);

      const r = 125 + i * 17;
      ctx.beginPath();
      ctx.ellipse(0, 0, r, r * 0.4, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    // 5. Floating robot transformation
    const floating = Math.sin(this.t * 0.045) * 8;
    ctx.save();
    ctx.translate(cx, cy + floating);

    // Robot shadow
    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    ctx.beginPath();
    ctx.ellipse(0, 150, 90, 12, 0, 0, Math.PI * 2);
    ctx.fill();

    // Robot body
    const bodyGrad = ctx.createLinearGradient(-70, 30, 70, 150);
    bodyGrad.addColorStop(0, '#A855F7');
    bodyGrad.addColorStop(0.5, '#3948A5');
    bodyGrad.addColorStop(1, '#111B48');

    ctx.fillStyle = bodyGrad;
    ctx.strokeStyle = '#C4B5FD';
    ctx.lineWidth = 2;
    this.drawRoundedRect(-72, 35, 144, 115, 30);
    ctx.fill();
    ctx.stroke();

    // Arms
    ctx.strokeStyle = '#A78BFA';
    ctx.lineWidth = 9;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(-65, 65);
    ctx.lineTo(-90, 105);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(65, 65);
    ctx.lineTo(90, 105);
    ctx.stroke();

    // Hands
    ctx.fillStyle = '#C4B5FD';
    ctx.beginPath();
    ctx.arc(-91, 108, 11, 0, Math.PI * 2);
    ctx.arc(91, 108, 11, 0, Math.PI * 2);
    ctx.fill();

    // Chest plate
    ctx.strokeStyle = '#60A5FA';
    ctx.lineWidth = 2;
    ctx.fillStyle = '#10152F';
    this.drawRoundedRect(-38, 65, 76, 58, 16);
    ctx.fill();
    ctx.stroke();

    // Chest reactor pulse
    const pulse = 13 + Math.sin(this.t * 0.12) * 4;
    this.drawGlow(0, 94, 25, '56, 189, 248', 0.55);
    ctx.fillStyle = '#67E8F9';
    ctx.beginPath();
    ctx.arc(0, 94, pulse / 2, 0, Math.PI * 2);
    ctx.fill();

    // Neck
    ctx.fillStyle = '#7770C9';
    this.drawRoundedRect(-15, 10, 30, 30, 8);
    ctx.fill();

    // Head
    const headGrad = ctx.createLinearGradient(-70, -130, 70, 10);
    headGrad.addColorStop(0, '#E9D5FF');
    headGrad.addColorStop(0.5, '#8057E8');
    headGrad.addColorStop(1, '#263B86');

    ctx.fillStyle = headGrad;
    ctx.strokeStyle = '#C4B5FD';
    ctx.lineWidth = 3;
    this.drawRoundedRect(-85, -130, 170, 140, 38);
    ctx.fill();
    ctx.stroke();

    // Face screen
    ctx.strokeStyle = '#93C5FD';
    ctx.lineWidth = 2;
    ctx.fillStyle = '#10152F';
    this.drawRoundedRect(-68, -110, 136, 100, 26);
    ctx.fill();
    ctx.stroke();

    // Antenna
    ctx.strokeStyle = '#C4B5FD';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(0, -130);
    ctx.lineTo(0, -153);
    ctx.stroke();

    this.drawGlow(0, -160, 20, '236, 72, 153', 0.6);
    ctx.fillStyle = '#F0ABFC';
    ctx.beginPath();
    ctx.arc(0, -160, 7, 0, Math.PI * 2);
    ctx.fill();

    // Ears
    ctx.fillStyle = '#A78BFA';
    this.drawRoundedRect(-96, -85, 14, 38, 7);
    ctx.fill();
    this.drawRoundedRect(82, -85, 14, 38, 7);
    ctx.fill();

    // Eyes
    const eyeColor = (state.robotState === 'speaking' || state.robotState === 'listening')
      ? '#67E8F9'
      : '#F0ABFC';

    const blink = this.t % 160 < 7;
    const eyeHeight = blink ? 3 : 19;

    ctx.fillStyle = eyeColor;
    this.drawRoundedRect(-47, -77, 27, eyeHeight, 8);
    ctx.fill();
    this.drawRoundedRect(20, -77, 27, eyeHeight, 8);
    ctx.fill();

    // Mouth
    let mouthHeight = 5;
    if (state.robotState === 'speaking') {
      mouthHeight = 8 + Math.abs(Math.sin(this.t * 0.25)) * 15;
    } else if (state.robotState === 'listening') {
      mouthHeight = 9;
    }

    ctx.fillStyle = '#F0ABFC';
    this.drawRoundedRect(-15, -35, 30, mouthHeight, 6);
    ctx.fill();

    ctx.restore();

    // Bottom Labels
    ctx.fillStyle = '#E9D5FF';
    ctx.font = 'bold 20px "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Z O R I N', cx, h - 45);

    ctx.fillStyle = '#A5A0BD';
    ctx.font = '11px "Segoe UI", sans-serif';
    ctx.fillText('YOUR PERSONAL AI COMPANION', cx, h - 22);

    requestAnimationFrame(this.animate);
  }
}

// =========================================================
// UI CONTROLLER & EVENT LISTENERS
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Robot Canvas
  const robot = new RobotCanvas('robotCanvas');

  // Elements
  const btnVoiceToggle = document.getElementById('btnVoiceToggle');
  const robotStatusTitle = document.getElementById('robotStatusTitle');
  const robotStatusDesc = document.getElementById('robotStatusDesc');
  const connectionStatus = document.getElementById('connectionStatus');
  const chatStream = document.getElementById('chatStream');
  const textInput = document.getElementById('textInput');
  const btnSend = document.getElementById('btnSend');
  const btnStop = document.getElementById('btnStop');
  const voiceSelect = document.getElementById('voiceSelect');
  const btnToggleHistory = document.getElementById('btnToggleHistory');
  const chatsSidebar = document.getElementById('chatsSidebar');
  const btnNewChat = document.getElementById('btnNewChat');
  const searchChatsInput = document.getElementById('searchChatsInput');
  const conversationList = document.getElementById('conversationList');

  // Modals
  const btnDevices = document.getElementById('btnDevices');
  const devicesModal = document.getElementById('devicesModal');
  const btnCloseDevicesModal = document.getElementById('btnCloseDevicesModal');
  const btnMemories = document.getElementById('btnMemories');
  const memoriesModal = document.getElementById('memoriesModal');
  const btnCloseMemoriesModal = document.getElementById('btnCloseMemoriesModal');

  // Voice Preference
  if (voiceSelect) {
    voiceSelect.addEventListener('change', (e) => {
      state.voicePreference = e.target.value;
    });
  }

  // Toggle History Sidebar
  if (btnToggleHistory && chatsSidebar) {
    btnToggleHistory.addEventListener('click', () => {
      chatsSidebar.classList.toggle('collapsed');
    });
  }

  // Set Visual State
  function setRobotState(newState) {
    state.robotState = newState;
    connectionStatus.textContent = `● ${newState.toUpperCase()}`;

    if (newState === 'listening') {
      robotStatusTitle.textContent = 'LISTENING...';
      robotStatusDesc.textContent = 'Speak naturally, ZORIN is listening.';
      btnVoiceToggle.classList.add('active');
      btnVoiceToggle.innerHTML = '🛑 STOP VOICE CONVERSATION';
    } else if (newState === 'thinking') {
      robotStatusTitle.textContent = 'THINKING...';
      robotStatusDesc.textContent = 'Consulting Gemini AI central brain...';
    } else if (newState === 'speaking') {
      robotStatusTitle.textContent = 'SPEAKING...';
      robotStatusDesc.textContent = 'ZORIN is responding (interrupt anytime)';
      btnVoiceToggle.classList.add('active');
    } else {
      robotStatusTitle.textContent = 'ZORIN IS READY';
      robotStatusDesc.textContent = "Say 'Hey Zorin' or click below to start voice.";
      btnVoiceToggle.classList.remove('active');
      btnVoiceToggle.innerHTML = '🎙️ START VOICE CONVERSATION';
    }
  }

  // Stop All Speech & Generation
  function stopAll() {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (state.recognition) {
      try { state.recognition.stop(); } catch (e) {}
    }
    setRobotState('idle');
  }

  if (btnStop) {
    btnStop.addEventListener('click', stopAll);
  }

  // Append Message to Stream
  function appendMessage(role, text) {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${role}`;

    const author = document.createElement('div');
    author.className = 'msg-author';
    author.textContent = role === 'user' ? 'YOU' : 'ZORIN';

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.textContent = text;

    const time = document.createElement('div');
    time.className = 'msg-time';
    const now = new Date();
    time.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    bubble.appendChild(author);
    bubble.appendChild(content);
    bubble.appendChild(time);

    chatStream.appendChild(bubble);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  // Speak Text using SpeechSynthesis (with voice selection)
  function speakResponse(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    state.currentAudioUtterance = utterance;

    const voices = window.speechSynthesis.getVoices();
    const isFemale = state.voicePreference === 'Aoede' || state.voicePreference === 'Kore';
    const chosenVoice = voices.find(v => isFemale ? (v.name.includes('Female') || v.name.includes('Google US English') || v.name.includes('Samantha') || v.name.includes('Zira')) : (v.name.includes('Male') || v.name.includes('David') || v.name.includes('Alex')));
    if (chosenVoice) utterance.voice = chosenVoice;

    utterance.rate = 1.05;
    utterance.pitch = isFemale ? 1.1 : 0.95;

    utterance.onstart = () => setRobotState('speaking');
    utterance.onend = () => {
      setRobotState('idle');
      if (state.isVoiceActive) startListening();
    };
    utterance.onerror = () => setRobotState('idle');

    window.speechSynthesis.speak(utterance);
  }

  // Send Prompt to Central Brain
  async function sendPrompt(promptText) {
    if (!promptText || !promptText.trim()) return;
    const text = promptText.trim();
    appendMessage('user', text);
    textInput.value = '';

    setRobotState('thinking');

    try {
      const resp = await fetch('/api/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: text,
          conversation_id: state.activeConversationId
        })
      });

      if (!resp.ok) {
        throw new Error(`Server returned ${resp.status}`);
      }

      const data = await resp.json();
      const reply = data.response || data.reply || data.text || 'I processed your command.';
      appendMessage('assistant', reply);
      speakResponse(reply);

    } catch (err) {
      console.error('Chat error:', err);
      const fallback = `I encountered an issue connecting to the brain: ${err.message}`;
      appendMessage('assistant', fallback);
      setRobotState('idle');
    }
  }

  // Send button click & Enter key
  if (btnSend) {
    btnSend.addEventListener('click', () => sendPrompt(textInput.value));
  }
  if (textInput) {
    textInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendPrompt(textInput.value);
    });
  }

  // Voice Recognition (Web Speech API)
  function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Your browser does not support Web Speech Recognition. Please use Chrome or Safari.');
      return;
    }

    if (state.recognition) {
      try { state.recognition.abort(); } catch (e) {}
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setRobotState('listening');
    };

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      if (transcript) {
        sendPrompt(transcript);
      }
    };

    recognition.onerror = (e) => {
      console.warn('Recognition error:', e);
      setRobotState('idle');
    };

    recognition.onend = () => {
      if (state.robotState === 'listening') {
        setRobotState('idle');
      }
    };

    state.recognition = recognition;
    recognition.start();
  }

  // Voice Button Toggle
  if (btnVoiceToggle) {
    btnVoiceToggle.addEventListener('click', () => {
      if (state.robotState === 'listening' || state.robotState === 'speaking') {
        state.isVoiceActive = false;
        stopAll();
      } else {
        state.isVoiceActive = true;
        startListening();
      }
    });
  }

  // =======================================================
  // MODALS: DEVICES & MEMORY
  // =======================================================
  if (btnDevices && devicesModal) {
    btnDevices.addEventListener('click', async () => {
      devicesModal.classList.add('open');
      loadDeviceFleet();
    });
  }
  if (btnCloseDevicesModal && devicesModal) {
    btnCloseDevicesModal.addEventListener('click', () => {
      devicesModal.classList.remove('open');
    });
  }

  if (btnMemories && memoriesModal) {
    btnMemories.addEventListener('click', () => {
      memoriesModal.classList.add('open');
      loadMemories();
    });
  }
  if (btnCloseMemoriesModal && memoriesModal) {
    btnCloseMemoriesModal.addEventListener('click', () => {
      memoriesModal.classList.remove('open');
    });
  }

  // Modal Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  async function loadDeviceFleet() {
    const grid = document.getElementById('fleetGrid');
    if (!grid) return;
    try {
      const res = await fetch('/api/devices');
      if (res.ok) {
        const data = await res.json();
        const devices = data.devices || [];
        if (devices.length > 0) {
          grid.innerHTML = devices.map(d => `
            <div class="device-card ${d.is_default ? 'active-card' : ''}">
              <div class="device-card-header">
                <span class="device-type-badge">${d.device_type === 'laptop' ? '💻' : '📱'} ${d.device_type}</span>
                <span class="status-online">● ${d.status ? d.status.toUpperCase() : 'ONLINE'}</span>
              </div>
              <div class="device-card-name">${d.name || d.device_name || 'Connected Node'}</div>
              <div class="device-card-sub">${d.ip_address || 'Cloud Hub'} · ${d.is_default ? 'Default Target' : 'Secondary'}</div>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      console.warn('Failed to fetch devices:', e);
    }
  }

  async function loadMemories() {
    const list = document.getElementById('memoryItemsList');
    if (!list) return;
    try {
      const res = await fetch('/api/memory');
      if (res.ok) {
        const data = await res.json();
        const memories = data.memories || [];
        if (memories.length > 0) {
          list.innerHTML = memories.map(m => `
            <div class="memory-item">
              <span>${m.content || m.fact || m}</span>
              <span style="color:#A78BFA;font-size:0.75rem;">Persistent</span>
            </div>
          `).join('');
        } else {
          list.innerHTML = '<div style="color:#8E8AAB;text-align:center;padding:20px;">No facts stored yet. Type one above!</div>';
        }
      }
    } catch (e) {
      list.innerHTML = '<div style="color:#8E8AAB;text-align:center;padding:20px;">Memory bank accessible on primary host.</div>';
    }
  }

  // Pre-load voices
  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.getVoices();
    };
  }
});
