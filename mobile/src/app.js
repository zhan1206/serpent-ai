/* SerpentAI Mobile App - 主应用入口 */
(function() {
    'use strict';

    // ===== API Client =====
    class SerpentAPI {
        constructor() {
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            this.baseUrl = (settings.apiUrl || 'http://localhost:8000').replace(/\/+$/, '');
        }

        get _model() {
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            return settings.model || 'gpt-4o';
        }

        async chat(sessionId, message) {
            const res = await fetch(`${this.baseUrl}/api/agent/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId,
                    model: this._model
                })
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            return res.json();
        }

        async getTools(params = {}) {
            const query = new URLSearchParams();
            if (params.category) query.set('category', params.category);
            if (params.type) query.set('tool_type', params.type);
            const res = await fetch(`${this.baseUrl}/api/tools?${query}`);
            if (!res.ok) throw new Error(`获取工具列表失败: ${res.status}`);
            return res.json();
        }

        async getToolCategories() {
            const res = await fetch(`${this.baseUrl}/api/tools/categories`);
            if (!res.ok) throw new Error(`获取分类失败: ${res.status}`);
            return res.json();
        }

        async resetSession(sessionId) {
            const res = await fetch(`${this.baseUrl}/api/agent/reset?session_id=${encodeURIComponent(sessionId)}`, {
                method: 'POST'
            });
            if (!res.ok) throw new Error(`重置会话失败: ${res.status}`);
            return res.json();
        }

        async getHealth() {
            const res = await fetch(`${this.baseUrl}/health`);
            return res.json();
        }

        async getStats() {
            const res = await fetch(`${this.baseUrl}/api/agent/stats`);
            if (!res.ok) throw new Error(`获取统计失败: ${res.status}`);
            return res.json();
        }
    }

    // ===== App Controller =====
    class App {
        constructor() {
            this.api = new SerpentAPI();
            this.currentView = 'chat';
            this.views = {};
            this.ws = null;
        }

        init() {
            // Apply saved theme
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            if (settings.theme) {
                document.documentElement.setAttribute('data-theme', settings.theme);
                this._updateThemeIcon(settings.theme);
            } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                this._updateThemeIcon('dark');
            }

            // Initialize views
            this.views.chat = new ChatView(this.api);
            this.views.voice = new VoiceView(this.api);
            this.views.skills = new SkillsView(this.api);
            this.views.settings = new SettingsView(this.api);

            // Render initial view
            const container = document.getElementById('view-container');
            Object.values(this.views).forEach(view => {
                container.appendChild(view.render());
            });

            // Navigation
            document.querySelectorAll('.nav-item').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const viewName = btn.dataset.view;
                    if (navigator.vibrate) navigator.vibrate(5);
                    this.switchView(viewName);
                });
            });

            // Theme toggle in header
            document.getElementById('btn-theme').addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'light' ? 'dark' : current === 'dark' ? 'light' : 'light';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('serpent_settings', JSON.stringify({
                    ...JSON.parse(localStorage.getItem('serpent_settings') || '{}'),
                    theme: next
                }));
                this._updateThemeIcon(next);
                if (navigator.vibrate) navigator.vibrate(5);
            });

            // Menu button
            document.getElementById('btn-menu').addEventListener('click', () => {
                this.switchView('settings');
            });

            // Register service worker
            this._registerSW();

            // PWA install prompt
            this._setupInstallPrompt();

            // WebSocket for real-time updates
            this._connectWebSocket();
        }

        switchView(name) {
            if (!this.views[name]) return;
            this.currentView = name;

            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            const targetView = document.getElementById(name + '-view');
            if (targetView) targetView.classList.add('active');

            document.querySelectorAll('.nav-item').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.view === name);
            });

            // Lazy-load skills
            if (name === 'skills') {
                this.views.skills.loadTools();
            }
        }

        _updateThemeIcon(theme) {
            const icon = document.querySelector('.theme-icon');
            if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }

        _registerSW() {
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/mobile/sw.js')
                    .then(reg => console.log('SW registered:', reg.scope))
                    .catch(err => console.warn('SW registration failed:', err));
            }
        }

        _setupInstallPrompt() {
            let deferredPrompt;
            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                deferredPrompt = e;
                const banner = document.getElementById('install-banner');
                if (banner) banner.classList.remove('hidden');
            });

            const installBtn = document.getElementById('btn-install');
            if (installBtn) {
                installBtn.addEventListener('click', async () => {
                    if (!deferredPrompt) return;
                    deferredPrompt.prompt();
                    const result = await deferredPrompt.userChoice;
                    if (result.outcome === 'accepted') {
                        if (navigator.vibrate) navigator.vibrate(30);
                    }
                    deferredPrompt = null;
                    document.getElementById('install-banner').classList.add('hidden');
                });
            }

            const dismissBtn = document.getElementById('btn-install-dismiss');
            if (dismissBtn) {
                dismissBtn.addEventListener('click', () => {
                    document.getElementById('install-banner').classList.add('hidden');
                });
            }
        }

        _connectWebSocket() {
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            const wsUrl = (settings.apiUrl || 'http://localhost:8000')
                .replace('http', 'ws') + '/ws';

            try {
                this.ws = new WebSocket(wsUrl);
                this.ws.onopen = () => console.log('WebSocket connected');
                this.ws.onmessage = (e) => {
                    try {
                        const data = JSON.parse(e.data);
                        if (data.type === 'notification') {
                            this._showNotification(data.title, data.body);
                        }
                    } catch {}
                };
                this.ws.onclose = () => {
                    // Reconnect after 5s
                    setTimeout(() => this._connectWebSocket(), 5000);
                };
                this.ws.onerror = () => this.ws.close();
            } catch {
                // WebSocket not available, fine
            }
        }

        _showNotification(title, body) {
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification(title, { body, icon: '🐍' });
            }
        }
    }

    // ===== Boot =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new App().init());
    } else {
        new App().init();
    }
})();
