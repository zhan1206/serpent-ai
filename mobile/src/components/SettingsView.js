/* SettingsView - 设置面板视图 */
class SettingsView {
    constructor(api) {
        this.api = api;
        this.settings = this._loadSettings();
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view';
        view.id = 'settings-view';

        this.container = document.createElement('div');
        this.container.className = 'settings-view';
        view.appendChild(this.container);

        this._renderSettings();
        return view;
    }

    _renderSettings() {
        this.container.innerHTML = `
            <div class="settings-group">
                <div class="settings-group-title">通用</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">API 地址</div>
                        <div class="settings-item-desc">后端服务地址</div>
                    </div>
                    <input type="text" class="settings-input" id="setting-api-url"
                        value="${this._esc(this.settings.apiUrl || 'http://localhost:8000')}"
                        placeholder="http://localhost:8000">
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">模型</div>
                        <div class="settings-item-desc">默认对话模型</div>
                    </div>
                    <select class="settings-select" id="setting-model">
                        <option value="gpt-4o" ${this.settings.model === 'gpt-4o' ? 'selected' : ''}>GPT-4o</option>
                        <option value="gpt-4o-mini" ${this.settings.model === 'gpt-4o-mini' ? 'selected' : ''}>GPT-4o Mini</option>
                        <option value="gpt-3.5-turbo" ${this.settings.model === 'gpt-3.5-turbo' ? 'selected' : ''}>GPT-3.5 Turbo</option>
                        <option value="claude-3-5-sonnet" ${this.settings.model === 'claude-3-5-sonnet' ? 'selected' : ''}>Claude 3.5 Sonnet</option>
                        <option value="claude-3-haiku" ${this.settings.model === 'claude-3-haiku' ? 'selected' : ''}>Claude 3 Haiku</option>
                    </select>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">会话ID</div>
                        <div class="settings-item-desc">${this._esc(this._getSessionId())}</div>
                    </div>
                    <button class="icon-btn" id="btn-copy-session" aria-label="复制">&#x1F4CB;</button>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">界面</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">深色模式</div>
                        <div class="settings-item-desc">切换深色/浅色主题</div>
                    </div>
                    <button class="toggle ${this.settings.theme === 'dark' || (!this.settings.theme && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'on' : ''}" id="setting-theme"></button>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">触觉反馈</div>
                        <div class="settings-item-desc">操作时振动</div>
                    </div>
                    <button class="toggle ${this.settings.haptic !== false ? 'on' : ''}" id="setting-haptic"></button>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">语音</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">语音回复</div>
                        <div class="settings-item-desc">语音模式下朗读AI回复</div>
                    </div>
                    <button class="toggle ${this.settings.voiceReply !== false ? 'on' : ''}" id="setting-voice-reply"></button>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">识别语言</div>
                        <div class="settings-item-desc">语音识别语言</div>
                    </div>
                    <select class="settings-select" id="setting-lang">
                        <option value="zh-CN" ${this.settings.lang === 'zh-CN' ? 'selected' : ''}>中文</option>
                        <option value="en-US" ${this.settings.lang === 'en-US' ? 'selected' : ''}>English</option>
                        <option value="ja-JP" ${this.settings.lang === 'ja-JP' ? 'selected' : ''}>日本語</option>
                    </select>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">数据</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">消息数量</div>
                        <div class="settings-item-desc">本地存储的消息条数</div>
                    </div>
                    <span style="color:var(--text-secondary);font-size:14px;">${this._getMessageCount()}</span>
                </div>
                <div style="padding:8px 0;">
                    <button class="danger-btn" id="btn-clear-chat">清空聊天记录</button>
                </div>
                <div style="padding:4px 0;">
                    <button class="danger-btn" id="btn-clear-session">重置会话</button>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">关于</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">版本</div>
                        <div class="settings-item-desc">SerpentAI Mobile v1.0.0</div>
                    </div>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">PWA</div>
                        <div class="settings-item-desc">${window.matchMedia('(display-mode: standalone)').matches ? '已安装' : '未安装'}</div>
                    </div>
                    <span style="color:${window.matchMedia('(display-mode: standalone)').matches ? 'var(--success)' : 'var(--text-secondary)'};font-size:14px;">${window.matchMedia('(display-mode: standalone)').matches ? '&#x2705;' : '&#x274C;'}</span>
                </div>
            </div>
        `;

        this._bindEvents();
    }

    _bindEvents() {
        // API URL
        const apiInput = document.getElementById('setting-api-url');
        if (apiInput) {
            apiInput.addEventListener('change', () => {
                this.settings.apiUrl = apiInput.value.replace(/\/+$/, '');
                this._saveSettings();
                this.api.baseUrl = this.settings.apiUrl;
            });
        }

        // Model
        const modelSelect = document.getElementById('setting-model');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                this.settings.model = modelSelect.value;
                this._saveSettings();
            });
        }

        // Copy session
        const copyBtn = document.getElementById('btn-copy-session');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(this._getSessionId()).then(() => {
                    if (navigator.vibrate) navigator.vibrate(10);
                    copyBtn.innerHTML = '&#x2705;';
                    setTimeout(() => { copyBtn.innerHTML = '&#x1F4CB;'; }, 1500);
                });
            });
        }

        // Theme toggle
        const themeToggle = document.getElementById('setting-theme');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                themeToggle.classList.toggle('on');
                const isDark = themeToggle.classList.contains('on');
                this.settings.theme = isDark ? 'dark' : 'light';
                this._saveSettings();
                document.documentElement.setAttribute('data-theme', this.settings.theme);
            });
        }

        // Haptic toggle
        const hapticToggle = document.getElementById('setting-haptic');
        if (hapticToggle) {
            hapticToggle.addEventListener('click', () => {
                hapticToggle.classList.toggle('on');
                this.settings.haptic = hapticToggle.classList.contains('on');
                this._saveSettings();
            });
        }

        // Voice reply toggle
        const voiceReplyToggle = document.getElementById('setting-voice-reply');
        if (voiceReplyToggle) {
            voiceReplyToggle.addEventListener('click', () => {
                voiceReplyToggle.classList.toggle('on');
                this.settings.voiceReply = voiceReplyToggle.classList.contains('on');
                this._saveSettings();
            });
        }

        // Language
        const langSelect = document.getElementById('setting-lang');
        if (langSelect) {
            langSelect.addEventListener('change', () => {
                this.settings.lang = langSelect.value;
                this._saveSettings();
            });
        }

        // Clear chat
        const clearChatBtn = document.getElementById('btn-clear-chat');
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', () => {
                if (confirm('确定要清空聊天记录吗？')) {
                    localStorage.removeItem('serpent_messages');
                    this._renderSettings();
                    if (navigator.vibrate) navigator.vibrate(20);
                }
            });
        }

        // Clear session
        const clearSessionBtn = document.getElementById('btn-clear-session');
        if (clearSessionBtn) {
            clearSessionBtn.addEventListener('click', async () => {
                if (confirm('确定要重置会话吗？这将清除服务端上下文。')) {
                    const sid = this._getSessionId();
                    try {
                        await this.api.resetSession(sid);
                    } catch (e) {}
                    localStorage.removeItem('serpent_session_id');
                    localStorage.removeItem('serpent_messages');
                    this._renderSettings();
                    if (navigator.vibrate) navigator.vibrate(20);
                }
            });
        }
    }

    _loadSettings() {
        try {
            const data = localStorage.getItem('serpent_settings');
            return data ? JSON.parse(data) : {};
        } catch { return {}; }
    }

    _saveSettings() {
        localStorage.setItem('serpent_settings', JSON.stringify(this.settings));
    }

    _getSessionId() {
        return localStorage.getItem('serpent_session_id') || 'N/A';
    }

    _getMessageCount() {
        try {
            const msgs = JSON.parse(localStorage.getItem('serpent_messages') || '[]');
            return msgs.length;
        } catch { return 0; }
    }

    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }
}

window.SettingsView = SettingsView;
