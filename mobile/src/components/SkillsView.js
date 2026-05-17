/* SkillsView - 技能/工具管理视图 */
class SkillsView {
    constructor(api) {
        this.api = api;
        this.tools = [];
        this.categories = [];
        this.isLoading = false;
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view';
        view.id = 'skills-view';

        this.container = document.createElement('div');
        this.container.className = 'skills-view';
        view.appendChild(this.container);

        this._render();

        // Auto-load on first show
        if (this.tools.length === 0) this.loadTools();

        return view;
    }

    _render() {
        this.container.innerHTML = `
            <div class="skills-header">
                <h2>&#x1F9E9; 技能中心</h2>
                <button class="icon-btn" id="btn-reload-skills" aria-label="刷新">&#x1F504;</button>
            </div>
            <div id="skills-loading" style="text-align:center;padding:40px;">
                <div class="spinner" style="margin:0 auto 12px;"></div>
                <p style="color:var(--text-secondary);font-size:14px;">正在加载技能...</p>
            </div>
            <div id="skills-content"></div>`;

        document.getElementById('btn-reload-skills').addEventListener('click', () => {
            this.loadTools();
        });
    }

    async loadTools() {
        if (this.isLoading) return;
        this.isLoading = true;

        const loading = document.getElementById('skills-loading');
        const content = document.getElementById('skills-content');
        if (loading) loading.style.display = '';
        if (content) content.innerHTML = '';

        try {
            const data = await this.api.getTools();
            this.tools = data.tools || [];
            this.categories = data.categories || [];

            if (this.tools.length === 0) {
                if (content) content.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">&#x1F9E9;</div>
                        <h3>暂无技能</h3>
                        <p>请确保后端服务已启动并注册了工具</p>
                    </div>`;
                return;
            }

            this._renderTools(content);
        } catch (e) {
            if (content) content.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#x26A0;&#xFE0F;</div>
                    <h3>加载失败</h3>
                    <p>${e.message}<br>请检查后端连接: ${this.api.baseUrl}</p>
                </div>`;
        }

        if (loading) loading.style.display = 'none';
        this.isLoading = false;
    }

    _renderTools(container) {
        if (!container) return;

        // Group by category
        const grouped = {};
        this.tools.forEach(tool => {
            const cat = tool.category || '其他';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(tool);
        });

        const iconMap = {
            'search': '&#x1F50D;', 'file': '&#x1F4C4;', 'web': '&#x1F310;',
            'system': '&#x2699;&#xFE0F;', 'communication': '&#x1F4E8;',
            'productivity': '&#x1F4DD;', 'custom': '&#x2728;',
            '其他': '&#x1F527;'
        };

        let html = '';
        for (const [cat, tools] of Object.entries(grouped)) {
            const icon = iconMap[cat] || '&#x1F527;';
            html += `<div class="skill-category">
                <div class="skill-category-title">${icon} ${cat}</div>
                <div class="skill-list">`;

            tools.forEach(tool => {
                const badgeClass = tool.type === 'builtin' ? 'builtin' : tool.type === 'mcp' ? 'mcp' : 'custom';
                const badgeText = tool.type === 'builtin' ? '内置' : tool.type === 'mcp' ? 'MCP' : '自定义';
                const desc = (tool.description || '').substring(0, 50);

                html += `<div class="skill-card" data-tool="${this._escAttr(tool.name || tool.tool_name)}">
                    <div class="skill-icon">${icon}</div>
                    <div class="skill-info">
                        <div class="skill-name">${this._esc(tool.name || tool.tool_name)}</div>
                        <div class="skill-desc">${this._esc(desc)}</div>
                    </div>
                    <span class="skill-badge ${badgeClass}">${badgeText}</span>
                </div>`;
            });

            html += '</div></div>';
        }

        container.innerHTML = html;

        // Tap to show details
        container.querySelectorAll('.skill-card').forEach(card => {
            card.addEventListener('click', () => {
                if (navigator.vibrate) navigator.vibrate(5);
                const name = card.dataset.tool;
                this._showToolDetail(name);
            });
        });
    }

    _showToolDetail(name) {
        const tool = this.tools.find(t => (t.name || t.tool_name) === name);
        if (!tool) return;

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:300;display:flex;align-items:flex-end;justify-content:center;';
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });

        const sheet = document.createElement('div');
        sheet.style.cssText = 'background:var(--bg-card);border-radius:20px 20px 0 0;padding:20px;padding-bottom:calc(20px + var(--safe-bottom));width:100%;max-width:500px;max-height:60vh;overflow-y:auto;animation:slideUp 0.3s ease;';
        sheet.innerHTML = `
            <style>@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }</style>
            <div style="width:40px;height:4px;border-radius:2px;background:var(--border);margin:0 auto 16px;"></div>
            <h3 style="font-size:18px;margin-bottom:8px;">${this._esc(tool.name || tool.tool_name)}</h3>
            <p style="color:var(--text-secondary);font-size:14px;line-height:1.5;margin-bottom:12px;">${this._esc(tool.description || '暂无描述')}</p>
            ${tool.parameters ? `<pre style="font-size:12px;padding:12px;background:var(--bg-input);border-radius:8px;overflow-x:auto;">${this._esc(JSON.stringify(tool.parameters, null, 2))}</pre>` : ''}
            <div style="margin-top:12px;">
                <span class="skill-badge ${tool.type === 'builtin' ? 'builtin' : tool.type === 'mcp' ? 'mcp' : 'custom'}">${tool.type || 'unknown'}</span>
                ${tool.category ? `<span style="font-size:12px;color:var(--text-secondary);margin-left:8px;">${this._esc(tool.category)}</span>` : ''}
            </div>`;

        overlay.appendChild(sheet);
        document.body.appendChild(overlay);
    }

    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    _escAttr(s) {
        return (s || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
}

window.SkillsView = SkillsView;
