const Chat = {
  init() {
    const input = document.getElementById('messageInput');
    const send = document.getElementById('btnSend');
    const voice = document.getElementById('btnVoice');
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); this.send(); }
    });
    send.addEventListener('click', () => this.send());
    voice.addEventListener('click', () => this.toggleVoice());
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 150) + 'px';
    });
  },

  async send() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text) return;
    if (!App.state.currentChatId) App.newChat();

    const chat = App.state.chats[App.state.currentChatId];
    chat.messages.push({ role: 'user', content: text, ts: Date.now() });
    if (chat.messages.filter(m => m.role === 'user').length === 1) {
      chat.title = text.substring(0, 30) + (text.length > 30 ? '...' : '');
      Sidebar.render();
    }
    input.value = '';
    input.style.height = 'auto';
    this.renderMessages(chat.messages);
    this.showTyping();

    try {
      const result = await App.apiCall(`/api/agent/chat?session_id=${App.state.currentChatId}`, {
        method: 'POST',
        body: JSON.stringify({
          message: text,
          session_id: App.state.currentChatId,
          model: App.state.settings.model,
          max_iterations: 10
        })
      });
      this.hideTyping();
      const content = typeof result === 'string' ? result :
        (result.response || result.message || result.content || JSON.stringify(result, null, 2));
      chat.messages.push({ role: 'assistant', content, ts: Date.now() });
      this.renderMessages(chat.messages);
      if (result.usage) {
        document.getElementById('tokenInfo').textContent = `Tokens: ${result.usage.total_tokens || '-'}`;
      }
    } catch (e) {
      this.hideTyping();
      chat.messages.push({ role: 'assistant', content: `Request failed: ${e.message}\n\nMake sure the backend is running on localhost:8000`, ts: Date.now() });
      this.renderMessages(chat.messages);
    }
    App.saveState();
  },

  renderMessages(messages) {
    const c = document.getElementById('chatMessages');
    if (!messages || messages.length === 0) { this.renderWelcome(); return; }
    c.innerHTML = messages.map(m => {
      const isUser = m.role === 'user';
      const avatar = isUser ? '\u{1F464}' : '\u{1F40D}';
      const html = isUser ? this.esc(m.content) : this.md(m.content);
      const time = new Date(m.ts).toLocaleTimeString();
      return `<div class="message ${m.role}"><div class="message-avatar">${avatar}</div><div><div class="message-bubble">${html}</div><div class="message-meta">${time}</div></div></div>`;
    }).join('');
    this.scrollBottom();
  },

  renderWelcome() {
    document.getElementById('chatMessages').innerHTML = `
      <div class="welcome">
        <div class="welcome-icon">\u{1F40D}</div>
        <h2>SerpentAI Agent</h2>
        <p>Four-layer Memory &middot; ReAct Reasoning &middot; Multi-Agent Collaboration</p>
        <div class="welcome-stats">
          <div class="stat-card"><div class="stat-value">\u219385%</div><div class="stat-label">Token Reduction</div></div>
          <div class="stat-card"><div class="stat-value">\u219375%</div><div class="stat-label">Hardware Reduction</div></div>
          <div class="stat-card"><div class="stat-value">\u219170%</div><div class="stat-label">Effectiveness Gain</div></div>
        </div>
      </div>`;
  },

  md(text) { try { return marked.parse(text || ''); } catch { return this.esc(text || ''); } },

  showTyping() {
    const c = document.getElementById('chatMessages');
    const el = document.createElement('div');
    el.className = 'message assistant'; el.id = 'typingMsg';
    el.innerHTML = '<div class="message-avatar">\u{1F40D}</div><div class="message-bubble"><div class="typing-indicator"><span></span><span></span><span></span></div></div>';
    c.appendChild(el);
    this.scrollBottom();
  },

  hideTyping() { document.getElementById('typingMsg')?.remove(); },
  scrollBottom() { const c = document.getElementById('chatMessages'); requestAnimationFrame(() => { c.scrollTop = c.scrollHeight; }); },
  esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; },

  recognition: null, isRecording: false,
  toggleVoice() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      App.showToast('Speech recognition not supported'); return;
    }
    if (this.isRecording) { this.recognition?.stop(); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SR();
    this.recognition.lang = 'zh-CN';
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    const btn = document.getElementById('btnVoice');
    btn.classList.add('recording');
    this.recognition.onresult = (e) => {
      document.getElementById('messageInput').value = e.results[0][0].transcript;
      btn.classList.remove('recording'); this.isRecording = false;
    };
    this.recognition.onerror = this.recognition.onend = () => {
      btn.classList.remove('recording'); this.isRecording = false;
    };
    this.isRecording = true;
    this.recognition.start();
  }
};
