/**
 * SerpentAI Desktop Client - Main Application
 */
const API_BASE = 'http://localhost:8000';

const App = {
  state: {
    currentChatId: null,
    chats: {},
    models: [],
    settings: {
      model: 'gpt-4o',
      temperature: 0.7,
      maxTokens: 4096,
      systemPrompt: 'You are SerpentAI, an intelligent assistant with four-layer memory, reasoning, and tool-calling capabilities.'
    },
    isConnected: false
  },

  async init() {
    await this.loadState();
    Sidebar.init();
    Chat.init();
    Settings.init();
    Tools.init();
    Status.init();
    this.bindEvents();
    await this.checkBackend();
  },

  bindEvents() {
    document.getElementById('btnMinimize')?.addEventListener('click', () => {
      if (window.__TAURI__) window.__TAURI__.window.getCurrentWindow().minimize();
    });
    document.getElementById('btnMaximize')?.addEventListener('click', () => {
      if (window.__TAURI__) {
        const w = window.__TAURI__.window.getCurrentWindow();
        w.isMaximized().then(m => m ? w.unmaximize() : w.maximize());
      }
    });
    document.getElementById('btnClose')?.addEventListener('click', () => {
      if (window.__TAURI__) window.__TAURI__.window.getCurrentWindow().close();
    });
    document.getElementById('btnNewChat')?.addEventListener('click', () => this.newChat());
    document.getElementById('btnSettings')?.addEventListener('click', () => Settings.show());
    document.getElementById('btnTools')?.addEventListener('click', () => Tools.show());
    document.getElementById('btnStatus')?.addEventListener('click', () => Status.show());
    document.getElementById('btnPanelClose')?.addEventListener('click', () => this.closePanel());
  },

  async checkBackend() {
    try {
      await fetch(`${API_BASE}/health`);
      this.state.isConnected = true;
      document.getElementById('tokenInfo').textContent = '\u25CF Connected';
      document.getElementById('tokenInfo').style.color = 'var(--green)';
      try {
        const r = await fetch(`${API_BASE}/api/models`);
        const d = await r.json();
        this.state.models = d.models || [];
      } catch(e) {}
    } catch (e) {
      this.state.isConnected = false;
      document.getElementById('tokenInfo').textContent = '\u25CF Backend not connected';
      document.getElementById('tokenInfo').style.color = 'var(--red)';
    }
  },

  generateId() {
    return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
  },

  newChat() {
    const id = this.generateId();
    this.state.currentChatId = id;
    this.state.chats[id] = { id, title: 'New Chat', messages: [], createdAt: Date.now() };
    Sidebar.render();
    Chat.renderWelcome();
    this.saveState();
  },

  loadChat(id) {
    this.state.currentChatId = id;
    Sidebar.render();
    if (this.state.chats[id] && this.state.chats[id].messages.length > 0) {
      Chat.renderMessages(this.state.chats[id].messages);
    } else {
      Chat.renderWelcome();
    }
  },

  closePanel() {
    document.getElementById('panelOverlay').classList.add('hidden');
  },

  showPanel(title, html) {
    document.getElementById('panelTitle').textContent = title;
    document.getElementById('panelContent').innerHTML = html;
    document.getElementById('panelOverlay').classList.remove('hidden');
  },

  async saveState() {
    localStorage.setItem('serpentai_state', JSON.stringify({
      chats: this.state.chats,
      currentChatId: this.state.currentChatId,
      settings: this.state.settings
    }));
  },

  async loadState() {
    try {
      const raw = localStorage.getItem('serpentai_state');
      if (raw) {
        const d = JSON.parse(raw);
        this.state.chats = d.chats || {};
        this.state.currentChatId = d.currentChatId;
        if (d.settings) Object.assign(this.state.settings, d.settings);
      }
    } catch (e) { console.error('Load state failed:', e); }
  },

  showToast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
  },

  async apiCall(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }
};

window.__triggerVoiceInput = function() {
  document.getElementById('btnVoice')?.click();
};

document.addEventListener('DOMContentLoaded', () => App.init());
