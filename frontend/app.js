/**
 * SerpentAI 主应用入口
 * 功能：聊天界面、模型选择、工具管理、插件管理、工作流管理
 * 要求：原生 JavaScript，包含错误处理、加载状态、用户反馈、响应式设计
 */

class SerpentAIApp {
    /**
     * 构造函数
     * @param {Object} options - 配置选项
     * @param {string} options.apiBase - API 基础 URL
     * @param {string} options.containerId - 容器元素 ID
     */
    constructor(options = {}) {
        this.apiBase = options.apiBase || 'http://localhost:8000';
        this.containerId = options.containerId || 'app';
        this.container = document.getElementById(this.containerId);
        
        if (!this.container) {
            console.error(`SerpentAIApp: 找不到容器元素 #${this.containerId}`);
            return;
        }
        
        // 状态管理
        this.state = {
            isLoading: false,
            currentModel: null,
            models: [],
            tools: [],
            plugins: [],
            skills: [],
            messages: [],
            conversations: [],
            currentConversation: null
        };
        
        // 组件实例
        this.components = {
            voiceWidget: null,
            pluginStore: null,
            skillMarketplace: null
        };
        
        this.init();
    }
    
    /**
     * 初始化应用
     */
    async init() {
        try {
            this.render();
            await this.loadInitialData();
            this.initEventListeners();
            this.initVoiceWidget();
            this.showToast('SerpentAI 已就绪', 'success');
        } catch (e) {
            console.error('初始化失败:', e);
            this.showToast('初始化失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 加载初始数据
     */
    async loadInitialData() {
        this.showLoading(true);
        
        try {
            // 并行加载数据
            await Promise.all([
                this.loadModels(),
                this.loadTools(),
                this.loadPlugins(),
                this.loadSkills()
            ]);
        } catch (e) {
            console.error('加载初始数据失败:', e);
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 加载可用模型列表
     */
    async loadModels() {
        try {
            const resp = await this.fetchWithError('/api/models');
            this.state.models = resp.models || [];
            
            if (this.state.models.length > 0) {
                this.state.currentModel = this.state.models[0].id;
                this.updateModelSelector();
            }
        } catch (e) {
            console.error('加载模型失败:', e);
            // 使用默认模型列表
            this.state.models = [
                { id: 'gpt-4', name: 'GPT-4', provider: 'openai' },
                { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai' },
                { id: 'claude-3', name: 'Claude 3', provider: 'anthropic' },
                { id: 'llama-3-8b', name: 'Llama 3 8B (本地)', provider: 'local' }
            ];
            this.state.currentModel = this.state.models[0].id;
            this.updateModelSelector();
        }
    }
    
    /**
     * 加载可用工具列表
     */
    async loadTools() {
        try {
            const resp = await this.fetchWithError('/api/tools');
            this.state.tools = resp.tools || [];
            this.updateToolList();
        } catch (e) {
            console.error('加载工具失败:', e);
        }
    }
    
    /**
     * 加载插件列表
     */
    async loadPlugins() {
        try {
            const resp = await this.fetchWithError('/api/plugins');
            this.state.plugins = resp.plugins || [];
            this.updatePluginList();
        } catch (e) {
            console.error('加载插件失败:', e);
        }
    }
    
    /**
     * 加载技能列表
     */
    async loadSkills() {
        try {
            const resp = await this.fetchWithError('/api/skills');
            this.state.skills = resp.skills || [];
            this.updateSkillList();
        } catch (e) {
            console.error('加载技能失败:', e);
        }
    }
    
    /**
     * 发送聊天消息
     * @param {string} message - 用户消息
     */
    async sendMessage(message) {
        if (!message || !message.trim()) return;
        
        // 添加用户消息到界面
        this.addMessage('user', message);
        
        // 清空输入框
        const input = this.container.querySelector('.sa-chat-input');
        if (input) input.value = '';
        
        // 显示加载状态
        this.addMessage('assistant', '正在思考...', true);
        
        try {
            const resp = await fetch(`${this.apiBase}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    model: this.state.currentModel,
                    conversation_id: this.state.currentConversation?.id || null,
                    tools: this.getEnabledTools()
                })
            });
            
            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
            }
            
            const data = await resp.json();
            
            // 移除加载消息
            this.removeLoadingMessage();
            
            // 添加助手回复
            this.addMessage('assistant', data.response || data.message || '暂无回复');
            
            // 更新对话列表
            if (data.conversation_id) {
                this.state.currentConversation = {
                    id: data.conversation_id,
                    title: message.substring(0, 50)
                };
                this.loadConversations();
            }
        } catch (e) {
            console.error('发送消息失败:', e);
            this.removeLoadingMessage();
            this.addMessage('assistant', `错误: ${e.message}`, false, true);
            this.showToast('发送消息失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 添加消息到聊天界面
     * @param {string} role - 角色 (user/assistant)
     * @param {string} content - 消息内容
     * @param {boolean} isLoading - 是否为加载中消息
     * @param {boolean} isError - 是否为错误消息
     */
    addMessage(role, content, isLoading = false, isError = false) {
        const messagesEl = this.container.querySelector('.sa-messages');
        if (!messagesEl) return;
        
        const messageEl = document.createElement('div');
        messageEl.className = `sa-message sa-message-${role}${isLoading ? ' sa-loading' : ''}${isError ? ' sa-error' : ''}`;
        
        const timestamp = new Date().toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageEl.innerHTML = `
            <div class="sa-message-avatar">${role === 'user' ? '🧑' : '🤖'}</div>
            <div class="sa-message-content">
                <div class="sa-message-header">
                    <span class="sa-message-role">${role === 'user' ? '你' : 'SerpentAI'}</span>
                    <span class="sa-message-time">${timestamp}</span>
                </div>
                <div class="sa-message-text">${this.escapeHtml(content)}</div>
            </div>
        `;
        
        messagesEl.appendChild(messageEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        
        // 保存到状态
        if (!isLoading) {
            this.state.messages.push({
                role,
                content,
                timestamp: new Date().toISOString()
            });
        }
        
        return messageEl;
    }
    
    /**
     * 移除加载中的消息
     */
    removeLoadingMessage() {
        const loadingEl = this.container.querySelector('.sa-message.sa-loading');
        if (loadingEl) loadingEl.remove();
    }
    
    /**
     * 更新模型选择器
     */
    updateModelSelector() {
        const selector = this.container.querySelector('.sa-model-select');
        if (!selector) return;
        
        selector.innerHTML = this.state.models.map(m => 
            `<option value="${m.id}" ${m.id === this.state.currentModel ? 'selected' : ''}>${m.name}</option>`
        ).join('');
    }
    
    /**
     * 更新工具列表
     */
    updateToolList() {
        const toolList = this.container.querySelector('.sa-tool-list');
        if (!toolList) return;
        
        if (this.state.tools.length === 0) {
            toolList.innerHTML = '<p style="color: #888; padding: 12px;">暂无可用工具</p>';
            return;
        }
        
        toolList.innerHTML = this.state.tools.map(t => `
            <div class="sa-tool-item" data-tool="${t.name}">
                <label>
                    <input type="checkbox" ${t.enabled ? 'checked' : ''} onchange="this.closest('.sa')._app.toggleTool('${t.name}', this.checked)">
                    <span class="sa-tool-name">${t.name}</span>
                </label>
                <small style="color: #888; display: block; margin-top: 4px;">${t.description || '暂无描述'}</small>
            </div>
        `).join('');
    }
    
    /**
     * 更新插件列表
     */
    updatePluginList() {
        const pluginList = this.container.querySelector('.sa-plugin-list');
        if (!pluginList) return;
        
        if (this.state.plugins.length === 0) {
            pluginList.innerHTML = '<p style="color: #888; padding: 12px;">暂无已安装插件</p>';
            return;
        }
        
        pluginList.innerHTML = this.state.plugins.map(p => `
            <div class="sa-plugin-item ${p.state}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <b>${p.name}</b> <small style="color: #888;">v${p.version || '1.0.0'}</small>
                        <span class="sa-badge sa-badge-${p.state}">${p.state}</span>
                        <br>
                        <small style="color: #aaa;">${p.description || '暂无描述'}</small>
                    </div>
                    <div style="display: flex; gap: 4px;">
                        <button onclick="this.closest('.sa')._app.togglePlugin('${p.name}', '${p.state}')" 
                                class="sa-btn sa-btn-sm">
                            ${p.state === 'started' ? '停止' : '启动'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    /**
     * 更新技能列表
     */
    updateSkillList() {
        const skillList = this.container.querySelector('.sa-skill-list');
        if (!skillList) return;
        
        if (this.state.skills.length === 0) {
            skillList.innerHTML = '<p style="color: #888; padding: 12px;">暂无已安装技能</p>';
            return;
        }
        
        skillList.innerHTML = this.state.skills.map(s => `
            <div class="sa-skill-item ${s.enabled ? '' : 'sa-disabled'}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 20px; margin-right: 8px;">${s.icon || '📦'}</span>
                        <b>${s.display_name || s.name}</b>
                        ${!s.enabled ? '<span class="sa-badge" style="background: #555;">已禁用</span>' : ''}
                        <br>
                        <small style="color: #aaa;">${s.description || '暂无描述'}</small>
                    </div>
                    <div style="display: flex; gap: 4px;">
                        <button onclick="this.closest('.sa')._app.toggleSkill('${s.name}', ${s.enabled})" 
                                class="sa-btn sa-btn-sm">
                            ${s.enabled ? '禁用' : '启用'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    /**
     * 切换工具启用状态
     * @param {string} toolName - 工具名称
     * @param {boolean} enabled - 是否启用
     */
    async toggleTool(toolName, enabled) {
        try {
            await this.fetchWithError(`/api/tools/${toolName}/${enabled ? 'enable' : 'disable'}`, {
                method: 'POST'
            });
            
            this.showToast(`工具 "${toolName}" 已${enabled ? '启用' : '禁用'}`, 'success');
            await this.loadTools();
        } catch (e) {
            console.error('切换工具状态失败:', e);
            this.showToast('操作失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 切换插件状态
     * @param {string} pluginName - 插件名称
     * @param {string} currentState - 当前状态
     */
    async togglePlugin(pluginName, currentState) {
        const action = currentState === 'started' ? 'stop' : 'start';
        
        try {
            await this.fetchWithError(`/api/plugins/${action}`, {
                method: 'POST',
                body: { name: pluginName }
            });
            
            this.showToast(`插件 "${pluginName}" 已${action === 'start' ? '启动' : '停止'}`, 'success');
            await this.loadPlugins();
        } catch (e) {
            console.error('切换插件状态失败:', e);
            this.showToast('操作失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 切换技能状态
     * @param {string} skillName - 技能名称
     * @param {boolean} currentEnabled - 当前是否启用
     */
    async toggleSkill(skillName, currentEnabled) {
        try {
            await this.fetchWithError(`/api/skills/${skillName}/${currentEnabled ? 'disable' : 'enable'}`, {
                method: 'POST'
            });
            
            this.showToast(`技能 "${skillName}" 已${currentEnabled ? '禁用' : '启用'}`, 'success');
            await this.loadSkills();
        } catch (e) {
            console.error('切换技能状态失败:', e);
            this.showToast('操作失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 获取已启用的工具列表
     * @returns {Array} 已启用的工具名称列表
     */
    getEnabledTools() {
        return this.state.tools
            .filter(t => t.enabled)
            .map(t => t.name);
    }
    
    /**
     * 初始化语音组件
     */
    initVoiceWidget() {
        const voiceContainer = this.container.querySelector('.sa-voice-container');
        if (!voiceContainer) return;
        
        try {
            this.components.voiceWidget = new VoiceWidget({
                apiBase: this.apiBase,
                container: voiceContainer,
                onTranscript: (text) => {
                    this.sendMessage(text);
                },
                onError: (err) => {
                    this.showToast('语音错误: ' + err.message, 'error');
                },
                onStateChange: (state) => {
                    console.log('Voice state:', state);
                }
            });
        } catch (e) {
            console.error('初始化语音组件失败:', e);
        }
    }
    
    /**
     * 初始化事件监听器
     */
    initEventListeners() {
        // 聊天输入
        const input = this.container.querySelector('.sa-chat-input');
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage(input.value);
                }
            });
        }
        
        // 发送按钮
        const sendBtn = this.container.querySelector('.sa-send-btn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                const input = this.container.querySelector('.sa-chat-input');
                if (input) this.sendMessage(input.value);
            });
        }
        
        // 模型选择
        const modelSelect = this.container.querySelector('.sa-model-select');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                this.state.currentModel = e.target.value;
                this.showToast(`已切换到模型: ${e.target.selectedOptions[0].text}`, 'info');
            });
        }
        
        // 标签切换
        this.container.querySelectorAll('.sa-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.tab;
                this.switchTab(target);
            });
        });
    }
    
    /**
     * 切换标签
     * @param {string} tabName - 标签名称
     */
    switchTab(tabName) {
        // 更新标签样式
        this.container.querySelectorAll('.sa-tab').forEach(t => {
            t.classList.toggle('sa-tab-active', t.data-tab === tabName);
        });
        
        // 更新内容显示
        this.container.querySelectorAll('.sa-tab-content').forEach(content => {
            content.style.display = content.dataset.tabContent === tabName ? 'block' : 'none';
        });
    }
    
    /**
     * 渲染应用界面
     */
    render() {
        this.container.innerHTML = `
            <div class="sa">
                <div class="sa-header">
                    <h1>🐍 SerpentAI</h1>
                    <div class="sa-header-actions">
                        <select class="sa-model-select" title="选择模型">
                            <option>加载模型中...</option>
                        </select>
                        <button class="sa-btn" onclick="this.closest('.sa')._app.clearChat()">🗑️ 清空</button>
                    </div>
                </div>
                
                <div class="sa-body">
                    <!-- 聊天主界面 -->
                    <div class="sa-main">
                        <div class="sa-messages"></div>
                        <div class="sa-chat-input-wrapper">
                            <div class="sa-voice-container"></div>
                            <textarea class="sa-chat-input" placeholder="输入消息... (Shift+Enter 换行)"></textarea>
                            <button class="sa-btn sa-send-btn">发送</button>
                        </div>
                    </div>
                    
                    <!-- 侧边栏 -->
                    <div class="sa-sidebar">
                        <div class="sa-tabs">
                            <div class="sa-tab sa-tab-active" data-tab="tools">工具</div>
                            <div class="sa-tab" data-tab="plugins">插件</div>
                            <div class="sa-tab" data-tab="skills">技能</div>
                            <div class="sa-tab" data-tab="workflow">工作流</div>
                        </div>
                        
                        <div class="sa-tab-content" data-tab-content="tools">
                            <h3>可用工具</h3>
                            <div class="sa-tool-list"></div>
                        </div>
                        
                        <div class="sa-tab-content" data-tab-content="plugins" style="display: none;">
                            <h3>已安装插件</h3>
                            <div class="sa-plugin-list"></div>
                        </div>
                        
                        <div class="sa-tab-content" data-tab-content="skills" style="display: none;">
                            <h3>已安装技能</h3>
                            <div class="sa-skill-list"></div>
                        </div>
                        
                        <div class="sa-tab-content" data-tab-content="workflow" style="display: none;">
                            <h3>工作流</h3>
                            <button class="sa-btn" style="width: 100%; margin-bottom: 12px;" 
                                    onclick="window.open('workflow/workflow-editor.html', '_blank')">
                                🔄 打开工作流编辑器
                            </button>
                            <p style="color: #888; font-size: 12px;">在工作流编辑器中创建和管理自动化流程</p>
                        </div>
                    </div>
                </div>
                
                <div class="sa-statusbar">
                    <span class="sa-status-item">
                        <span class="sa-dot sa-dot-green"></span>
                        API: ${this.apiBase}
                    </span>
                    <span class="sa-status-item">
                        模型: ${this.state.currentModel || '未选择'}
                    </span>
                    <span class="sa-status-item">
                        工具: ${this.state.tools.filter(t => t.enabled).length} 已启用
                    </span>
                </div>
            </div>
        `;
        
        // 保存引用
        this.container.querySelector('.sa')._app = this;
        
        // 添加样式
        this.addStyles();
        
        // 添加欢迎消息
        this.addMessage('assistant', '你好！我是 SerpentAI，一个强大的 AI 助手。有什么可以帮你的吗？');
    }
    
    /**
     * 添加 CSS 样式
     */
    addStyles() {
        if (document.querySelector('#sa-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'sa-styles';
        style.textContent = `
            .sa {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                display: flex;
                flex-direction: column;
                height: 100vh;
                background: #0f0f1e;
                color: #e0e0e0;
            }
            
            .sa-header {
                background: #1a1a2e;
                padding: 12px 20px;
                border-bottom: 1px solid #2a2a4a;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .sa-header h1 {
                font-size: 18px;
                color: #00d4ff;
                margin: 0;
            }
            
            .sa-header-actions {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            .sa-model-select {
                background: #252540;
                border: 1px solid #3a3a5a;
                border-radius: 6px;
                padding: 6px 12px;
                color: #e0e0e0;
                font-size: 13px;
                outline: none;
            }
            
            .sa-model-select:focus {
                border-color: #00d4ff;
            }
            
            .sa-btn {
                background: #2a2a4a;
                border: 1px solid #3a3a5a;
                color: #e0e0e0;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
            }
            
            .sa-btn:hover {
                background: #3a3a5a;
                border-color: #00d4ff;
            }
            
            .sa-btn-sm {
                padding: 4px 8px;
                font-size: 12px;
            }
            
            .sa-body {
                flex: 1;
                display: flex;
                overflow: hidden;
            }
            
            .sa-main {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .sa-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
            }
            
            .sa-message {
                display: flex;
                gap: 12px;
                margin-bottom: 16px;
                animation: sa-fadeIn 0.3s ease;
            }
            
            @keyframes sa-fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .sa-message-avatar {
                font-size: 24px;
                min-width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #252540;
                border-radius: 50%;
            }
            
            .sa-message-content {
                flex: 1;
                background: #1a1a2e;
                border-radius: 8px;
                padding: 12px;
            }
            
            .sa-message-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            
            .sa-message-role {
                font-weight: 600;
                color: #00d4ff;
            }
            
            .sa-message-time {
                font-size: 11px;
                color: #888;
            }
            
            .sa-message-text {
                line-height: 1.6;
                white-space: pre-wrap;
                word-break: break-word;
            }
            
            .sa-message.sa-loading .sa-message-text::after {
                content: '...';
                animation: sa-dots 1.5s steps(4, end) infinite;
            }
            
            @keyframes sa-dots {
                0%, 20% { content: ''; }
                40% { content: '.'; }
                60% { content: '..'; }
                80%, 100% { content: '...'; }
            }
            
            .sa-message.sa-error .sa-message-text {
                color: #ff4757;
            }
            
            .sa-chat-input-wrapper {
                display: flex;
                gap: 8px;
                padding: 16px 20px;
                background: #1a1a2e;
                border-top: 1px solid #2a2a4a;
                align-items: flex-end;
            }
            
            .sa-chat-input {
                flex: 1;
                background: #252540;
                border: 1px solid #3a3a5a;
                border-radius: 8px;
                padding: 12px;
                color: #e0e0e0;
                font-size: 14px;
                resize: none;
                min-height: 44px;
                max-height: 120px;
                outline: none;
                font-family: inherit;
            }
            
            .sa-chat-input:focus {
                border-color: #00d4ff;
            }
            
            .sa-send-btn {
                background: #00d4ff;
                color: #0a0a1e;
                border-color: #00d4ff;
                font-weight: 600;
            }
            
            .sa-send-btn:hover {
                background: #00b8e6;
            }
            
            .sa-sidebar {
                width: 320px;
                background: #1a1a2e;
                border-left: 1px solid #2a2a4a;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .sa-tabs {
                display: flex;
                border-bottom: 1px solid #2a2a4a;
            }
            
            .sa-tab {
                flex: 1;
                padding: 12px;
                text-align: center;
                cursor: pointer;
                font-size: 13px;
                color: #888;
                transition: all 0.2s;
                border-bottom: 2px solid transparent;
            }
            
            .sa-tab:hover {
                color: #e0e0e0;
                background: #252540;
            }
            
            .sa-tab-active {
                color: #00d4ff;
                border-bottom-color: #00d4ff;
            }
            
            .sa-tab-content {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
            }
            
            .sa-tab-content h3 {
                font-size: 14px;
                color: #00d4ff;
                margin-bottom: 12px;
            }
            
            .sa-tool-item,
            .sa-plugin-item,
            .sa-skill-item {
                background: #252540;
                border: 1px solid #3a3a5a;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
                transition: all 0.2s;
            }
            
            .sa-tool-item:hover,
            .sa-plugin-item:hover,
            .sa-skill-item:hover {
                border-color: #00d4ff;
            }
            
            .sa-disabled {
                opacity: 0.5;
            }
            
            .sa-badge {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
                margin-left: 4px;
                background: #3a3a5a;
                color: #aaa;
            }
            
            .sa-badge-started {
                background: #6bcb77;
                color: #000;
            }
            
            .sa-badge-stopped {
                background: #ff4757;
                color: #fff;
            }
            
            .sa-statusbar {
                background: #1a1a2e;
                border-top: 1px solid #2a2a4a;
                padding: 6px 20px;
                font-size: 11px;
                color: #666;
                display: flex;
                gap: 20px;
            }
            
            .sa-status-item {
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            .sa-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
            }
            
            .sa-dot-green { background: #6bcb77; }
            .sa-dot-yellow { background: #ffd93d; }
            .sa-dot-red { background: #ff4757; }
            
            /* 响应式设计 */
            @media (max-width: 1024px) {
                .sa-sidebar {
                    width: 280px;
                }
            }
            
            @media (max-width: 768px) {
                .sa-body {
                    flex-direction: column;
                }
                
                .sa-sidebar {
                    width: 100%;
                    height: 300px;
                    border-left: none;
                    border-top: 1px solid #2a2a4a;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    /**
     * 清空聊天记录
     */
    clearChat() {
        if (!confirm('确定要清空聊天记录吗？')) return;
        
        this.state.messages = [];
        this.state.currentConversation = null;
        
        const messagesEl = this.container.querySelector('.sa-messages');
        if (messagesEl) messagesEl.innerHTML = '';
        
        this.addMessage('assistant', '聊天记录已清空。有什么可以帮你的吗？');
        this.showToast('聊天记录已清空', 'info');
    }
    
    /**
     * 显示 toast 通知
     * @param {string} message - 通知消息
     * @param {string} type - 类型：success, error, info
     */
    showToast(message, type = 'info') {
        // 移除已有的 toast
        const existingToast = document.body.querySelector('.sa-toast');
        if (existingToast) existingToast.remove();
        
        const toast = document.createElement('div');
        toast.className = `sa-toast sa-toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-size: 14px;
            z-index: 10000;
            animation: sa-slideIn 0.3s ease;
            background: ${type === 'success' ? '#6bcb77' : type === 'error' ? '#ff4757' : '#00d4ff'};
        `;
        
        // 添加动画样式
        if (!document.querySelector('#sa-toast-style')) {
            const style = document.createElement('style');
            style.id = 'sa-toast-style';
            style.textContent = `
                @keyframes sa-slideIn {
                    from { transform: translateX(100px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes sa-slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        // 3秒后自动移除
        setTimeout(() => {
            toast.style.animation = 'sa-slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    /**
     * 显示/隐藏加载状态
     * @param {boolean} show - 是否显示
     */
    showLoading(show) {
        let loader = this.container.querySelector('.sa-loading');
        
        if (show) {
            if (!loader) {
                loader = document.createElement('div');
                loader.className = 'sa-loading';
                loader.innerHTML = '<div class="sa-spinner"></div><span>加载中...</span>';
                loader.style.cssText = `
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    padding: 20px;
                    color: #888;
                `;
                
                // 添加 spinner 样式
                if (!document.querySelector('#sa-loading-style')) {
                    const style = document.createElement('style');
                    style.id = 'sa-loading-style';
                    style.textContent = `
                        .sa-spinner {
                            width: 20px;
                            height: 20px;
                            border: 2px solid #3a3a5a;
                            border-top-color: #00d4ff;
                            border-radius: 50%;
                            animation: sa-spin 0.8s linear infinite;
                        }
                        @keyframes sa-spin {
                            to { transform: rotate(360deg); }
                        }
                    `;
                    document.head.appendChild(style);
                }
                
                this.container.querySelector('.sa-messages').appendChild(loader);
            }
        } else {
            if (loader) loader.remove();
        }
    }
    
    /**
     * 封装 fetch 请求，自动处理错误
     * @param {string} endpoint - API 端点
     * @param {Object} options - fetch 选项
     * @returns {Promise<Object>} 响应数据
     */
    async fetchWithError(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.apiBase}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        };
        
        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };
        
        const resp = await fetch(url, mergedOptions);
        
        if (!resp.ok) {
            const errorData = await resp.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
        }
        
        return resp.json();
    }
    
    /**
     * HTML 转义
     * @param {string} text - 待转义文本
     * @returns {string} 转义后文本
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 销毁应用
     */
    destroy() {
        // 销毁语音组件
        if (this.components.voiceWidget) {
            this.components.voiceWidget.destroy();
        }
        
        // 移除事件监听器
        // ...（根据实际需要清理）
        
        // 清空容器
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SerpentAIApp;
}

// 自动初始化（如果在浏览器环境中）
if (typeof window !== 'undefined') {
    window.SerpentAIApp = SerpentAIApp;
    
    // DOM 加载完成后自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            if (document.getElementById('app')) {
                window.app = new SerpentAIApp();
            }
        });
    }
}
