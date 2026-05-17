/* ChatView - 聊天界面视图 */
class ChatView {
    constructor(api) {
        this.api = api;
        this.bubble = new MessageBubble();
        this.messages = [];
        this.sessionId = this._getOrCreateSession();
        this.isLoading = false;
        this.isPulling = false;
        this.pullStartY = 0;
        this.pullEl = null;
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view active';
        view.id = 'chat-view';

        // Pull indicator
        this.pullEl = document.createElement('div');
        this.pullEl.className = 'pull-indicator';
        this.pullEl.textContent = '下拉刷新';
        this.pullEl.style.opacity = '0';
        view.appendChild(this.pullEl);

        // Messages container
        this.msgContainer = document.createElement('div');
        this.msgContainer.className = 'chat-messages';
        this._addPullToRefresh(this.msgContainer);

        // Load stored messages
        this._loadMessages();
        if (this.messages.length === 0) {
            this.msgContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#x1F40D;</div>
                    <h3>SerpentAI</h3>
                    <p>我是您的AI智能助手，随时为您效劳。<br>有什么我可以帮您的吗？</p>
                </div>`;
        } else {
            this.messages.forEach(msg => {
                this.msgContainer.appendChild(this.bubble.create(msg));
            });
        }
        view.appendChild(this.msgContainer);

        // Input bar
        this.inputBar = document.createElement('div');
        this.inputBar.className = 'chat-input-bar';

        this.inputWrapper = document.createElement('div');
        this.inputWrapper.className = 'chat-input-wrapper';

        this.textarea = document.createElement('textarea');
        this.textarea.placeholder = '输入消息...';
        this.textarea.rows = 1;
        this.textarea.addEventListener('input', () => this._autoResize());
        this.textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._sendMessage();
            }
        });

        this.inputWrapper.appendChild(this.textarea);

        this.sendBtn = document.createElement('button');
        this.sendBtn.className = 'send-btn';
        this.sendBtn.innerHTML = '&#x2191;';
        this.sendBtn.disabled = true;
        this.sendBtn.addEventListener('click', () => this._sendMessage());

        this.inputBar.appendChild(this.inputWrapper);
        this.inputBar.appendChild(this.sendBtn);
        view.appendChild(this.inputBar);

        // Watch textarea for enabling send
        this.textarea.addEventListener('input', () => {
            this.sendBtn.disabled = !this.textarea.value.trim();
        });

        return view;
    }

    _getOrCreateSession() {
        let sid = localStorage.getItem('serpent_session_id');
        if (!sid) {
            sid = 'mobile_' + Date.now() + '_' + Math.random().toString(36).substr(2, 8);
            localStorage.setItem('serpent_session_id', sid);
        }
        return sid;
    }

    _autoResize() {
        this.textarea.style.height = 'auto';
        this.textarea.style.height = Math.min(this.textarea.scrollHeight, 100) + 'px';
    }

    async _sendMessage() {
        const text = this.textarea.value.trim();
        if (!text || this.isLoading) return;

        // Clear empty state
        const empty = this.msgContainer.querySelector('.empty-state');
        if (empty) empty.remove();

        const userMsg = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
            timestamp: Date.now()
        };

        this.messages.push(userMsg);
        this.msgContainer.appendChild(this.bubble.create(userMsg));
        this._saveMessages();

        this.textarea.value = '';
        this.textarea.style.height = 'auto';
        this.sendBtn.disabled = true;
        this._scrollToBottom();

        // Show typing indicator
        this.isLoading = true;
        const typing = this.bubble.createTyping();
        this.msgContainer.appendChild(typing);
        this._scrollToBottom();

        try {
            const response = await this.api.chat(this.sessionId, text);
            this.msgContainer.removeChild(typing);

            const aiMsg = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.response || response.content || '（无响应）',
                timestamp: Date.now(),
                model: response.model,
                usage: response.usage
            };
            this.messages.push(aiMsg);
            this.msgContainer.appendChild(this.bubble.create(aiMsg));
            this._saveMessages();
        } catch (e) {
            this.msgContainer.removeChild(typing);
            const errMsg = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `请求失败: ${e.message}`,
                timestamp: Date.now()
            };
            this.messages.push(errMsg);
            this.msgContainer.appendChild(this.bubble.create(errMsg));
        }

        this.isLoading = false;
        this._scrollToBottom();
    }

    _scrollToBottom() {
        requestAnimationFrame(() => {
            this.msgContainer.scrollTop = this.msgContainer.scrollHeight;
        });
    }

    _loadMessages() {
        try {
            const data = localStorage.getItem('serpent_messages');
            if (data) this.messages = JSON.parse(data);
        } catch (e) {
            this.messages = [];
        }
    }

    _saveMessages() {
        try {
            // Keep last 200 messages
            const toSave = this.messages.slice(-200);
            localStorage.setItem('serpent_messages', JSON.stringify(toSave));
        } catch (e) {
            console.warn('保存消息失败:', e);
        }
    }

    clearChat() {
        this.messages = [];
        localStorage.removeItem('serpent_messages');
        this.msgContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">&#x1F40D;</div>
                <h3>SerpentAI</h3>
                <p>我是您的AI智能助手，随时为您效劳。<br>有什么我可以帮您的吗？</p>
            </div>`;
    }

    _addPullToRefresh(el) {
        el.addEventListener('touchstart', (e) => {
            if (el.scrollTop <= 0) {
                this.pullStartY = e.touches[0].clientY;
                this.isPulling = true;
            }
        }, { passive: true });

        el.addEventListener('touchmove', (e) => {
            if (!this.isPulling) return;
            const dy = e.touches[0].clientY - this.pullStartY;
            if (dy > 0 && dy < 120) {
                this.pullEl.style.opacity = Math.min(dy / 80, 1);
                this.pullEl.textContent = dy > 60 ? '松开刷新' : '下拉刷新';
            }
        }, { passive: true });

        el.addEventListener('touchend', (e) => {
            if (!this.isPulling) return;
            this.isPulling = false;
            this.pullEl.style.opacity = '0';
            const dy = e.changedTouches[0].clientY - this.pullStartY;
            if (dy > 60) {
                if (navigator.vibrate) navigator.vibrate(10);
                this._refreshChat();
            }
        }, { passive: true });
    }

    async _refreshChat() {
        try {
            const health = await fetch('/health').then(r => r.json());
            if (health.status === 'healthy') {
                this.pullEl.textContent = '已连接';
            } else {
                this.pullEl.textContent = '服务异常';
            }
        } catch {
            this.pullEl.textContent = '离线模式';
        }
        setTimeout(() => { this.pullEl.style.opacity = '0'; }, 1500);
    }
}

window.ChatView = ChatView;
