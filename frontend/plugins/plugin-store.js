/**
 * SerpentAI Plugin Store UI
 * 功能：插件管理界面，支持加载/卸载/重载插件，搜索插件，查看插件详情
 * 要求：原生 JavaScript，包含错误处理、加载状态、用户反馈
 * 版本：2.0.0
 */

class PluginStore {
  /**
   * 构造函数
   * @param {string} containerId - 容器元素 ID
   * @param {string} apiBaseUrl - API 基础 URL
   * @param {Object} options - 配置选项
   * @param {number} options.timeout - 请求超时时间（毫秒）
   * @param {number} options.retryAttempts - 重试次数
   */
  constructor(containerId, apiBaseUrl = '/api', options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`PluginStore: 找不到容器元素 #${containerId}`);
      return;
    }
    
    this.apiUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
    this.timeout = options.timeout || 30000;
    this.retryAttempts = options.retryAttempts || 3;
    
    this.plugins = [];
    this.filteredPlugins = [];
    this.isLoading = false;
    this.currentFilter = 'all'; // all, started, stopped, loaded, error
    this.searchQuery = '';
    
    this.init();
  }

  /**
   * 初始化插件商店
   */
  async init() {
    this.render();
    await this.loadPlugins();
  }

  /**
   * 显示 toast 通知
   * @param {string} message - 通知消息
   * @param {string} type - 类型：success, error, info, warning
   */
  showToast(message, type = 'info') {
    // 移除已有的 toast
    const existingToast = document.body.querySelector('.ps-toast');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = `ps-toast ps-toast-${type}`;
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
      animation: ps-slideIn 0.3s ease;
      background: ${type === 'success' ? '#6bcb77' : type === 'error' ? '#ff4757' : type === 'warning' ? '#ffd93d' : '#00d4ff'};
      color: ${type === 'warning' ? '#000' : '#fff'};
      max-width: 400px;
      word-break: break-word;
    `;
    
    // 添加动画样式
    if (!document.querySelector('#ps-toast-style')) {
      const style = document.createElement('style');
      style.id = 'ps-toast-style';
      style.textContent = `
        @keyframes ps-slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes ps-slideOut {
          from { transform: translateX(0); opacity: 1; }
          to { transform: translateX(100px); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    // 3秒后自动移除
    setTimeout(() => {
      toast.style.animation = 'ps-slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  /**
   * 封装 fetch 请求，自动处理超时
   * @param {string} endpoint - API 端点
   * @param {Object} options - fetch 选项
   * @returns {Promise<Object>} 响应数据
   */
  async fetchWithTimeout(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${this.apiUrl}${endpoint}`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    
    const defaultOptions = {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      signal: controller.signal
    };
    
    const mergedOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers
      }
    };
    
    try {
      const resp = await fetch(url, mergedOptions);
      
      clearTimeout(timeoutId);
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      return resp.json();
    } catch (e) {
      clearTimeout(timeoutId);
      
      if (e.name === 'AbortError') {
        throw new Error(`请求超时 (${this.timeout}ms)`);
      }
      
      throw e;
    }
  }

  /**
   * 加载插件列表（带重试）
   * @param {number} attempt - 当前尝试次数
   */
  async loadPlugins(attempt = 1) {
    if (this.isLoading) return;
    
    this.isLoading = true;
    this.showLoading(true);
    
    try {
      const data = await this.fetchWithTimeout('/plugins');
      this.plugins = data.plugins || [];
      this.applyFilters();
      this.renderList();
      this.showToast(`已加载 ${this.plugins.length} 个插件`, 'success');
    } catch (e) {
      console.error(`加载插件失败 (尝试 ${attempt}/${this.retryAttempts}):`, e);
      
      if (attempt < this.retryAttempts) {
        await this.delay(1000 * attempt);
        return this.loadPlugins(attempt + 1);
      }
      
      this.showToast(`加载插件失败: ${e.message}`, 'error');
      this.plugins = [];
      this.applyFilters();
      this.renderList();
    } finally {
      this.isLoading = false;
      this.showLoading(false);
    }
  }

  /**
   * 应用过滤器和搜索
   */
  applyFilters() {
    let filtered = [...this.plugins];
    
    // 应用状态过滤
    if (this.currentFilter !== 'all') {
      filtered = filtered.filter(p => p.state === this.currentFilter);
    }
    
    // 应用搜索过滤
    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(query) ||
        (p.description && p.description.toLowerCase().includes(query))
      );
    }
    
    this.filteredPlugins = filtered;
  }

  /**
   * 切换插件状态（加载/卸载）
   * @param {string} name - 插件名称
   * @param {string} state - 当前状态
   */
  async toggle(name, state) {
    const action = (state === 'started' || state === 'loaded' || state === 'initialized') ? '卸载' : '加载';
    
    if (!confirm(`确定要${action}插件 "${name}" 吗？`)) return;
    
    this.showLoading(true);
    
    try {
      const endpoint = (state === 'started' || state === 'loaded' || state === 'initialized') ? 'unload' : 'load';
      await this.fetchWithTimeout(`/plugins/${endpoint}`, {
        method: 'POST',
        body: JSON.stringify({ name })
      });
      
      this.showToast(`插件 "${name}" ${action}成功`, 'success');
      await this.loadPlugins();
    } catch (e) {
      console.error(`${action}插件失败:`, e);
      this.showToast(`${action}插件失败: ${e.message}`, 'error');
      this.showLoading(false);
    }
  }

  /**
   * 重载插件
   * @param {string} name - 插件名称
   */
  async reload(name) {
    if (!confirm(`确定要重载插件 "${name}" 吗？`)) return;
    
    this.showLoading(true);
    
    try {
      await this.fetchWithTimeout('/plugins/reload', {
        method: 'POST',
        body: JSON.stringify({ name })
      });
      
      this.showToast(`插件 "${name}" 重载成功`, 'success');
      await this.loadPlugins();
    } catch (e) {
      console.error('重载插件失败:', e);
      this.showToast(`重载插件失败: ${e.message}`, 'error');
      this.showLoading(false);
    }
  }

  /**
   * 查看插件详情
   * @param {string} name - 插件名称
   */
  async viewDetails(name) {
    const plugin = this.plugins.find(p => p.name === name);
    if (!plugin) {
      this.showToast(`找不到插件 "${name}"`, 'error');
      return;
    }
    
    // 创建详情模态框
    const modal = document.createElement('div');
    modal.className = 'ps-details-modal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10001;
    `;
    
    modal.innerHTML = `
      <div style="background: #1a1a2e; border: 1px solid #3a3a5a; border-radius: 12px; padding: 24px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;">
        <h2 style="color: #00d4ff; margin-bottom: 16px;">🔌 ${this.escapeHtml(plugin.name)}</h2>
        
        <div style="margin-bottom: 12px;">
          <b>版本:</b> <span style="color: #aaa;">${plugin.version || '1.0.0'}</span>
        </div>
        
        <div style="margin-bottom: 12px;">
          <b>状态:</b> <span class="badge ${plugin.state}">${plugin.state}</span>
        </div>
        
        <div style="margin-bottom: 12px;">
          <b>类型:</b> <span class="badge ${plugin.type}">${plugin.type || 'unknown'}</span>
        </div>
        
        <div style="margin-bottom: 16px;">
          <b>描述:</b>
          <p style="color: #aaa; margin-top: 8px; line-height: 1.6;">${this.escapeHtml(plugin.description || '暂无描述')}</p>
        </div>
        
        ${plugin.author ? `
          <div style="margin-bottom: 12px;">
            <b>作者:</b> <span style="color: #aaa;">${this.escapeHtml(plugin.author)}</span>
          </div>
        ` : ''}
        
        ${plugin.homepage ? `
          <div style="margin-bottom: 12px;">
            <b>主页:</b> <a href="${this.escapeHtml(plugin.homepage)}" target="_blank" style="color: #00d4ff;">${this.escapeHtml(plugin.homepage)}</a>
          </div>
        ` : ''}
        
        ${plugin.dependencies && plugin.dependencies.length > 0 ? `
          <div style="margin-bottom: 16px;">
            <b>依赖:</b>
            <ul style="color: #aaa; margin-top: 8px; padding-left: 20px;">
              ${plugin.dependencies.map(d => `<li>${this.escapeHtml(d)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 24px;">
          <button class="ps-btn" onclick="this.closest('.ps-details-modal').remove()">关闭</button>
        </div>
      </div>
    `;
    
    // 添加按钮样式
    if (!document.querySelector('#ps-details-style')) {
      const style = document.createElement('style');
      style.id = 'ps-details-style';
      style.textContent = `
        .ps-btn {
          background: #2a2a4a;
          border: 1px solid #3a3a5a;
          color: #e0e0e0;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }
        .ps-btn:hover {
          background: #3a3a5a;
          border-color: #00d4ff;
        }
        .ps-btn-primary {
          background: #00d4ff;
          color: #0a0a1e;
          border-color: #00d4ff;
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(modal);
    
    // 点击背景关闭
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });
  }

  /**
   * 搜索插件
   * @param {string} query - 搜索关键词
   */
  async search(query) {
    this.searchQuery = query;
    this.applyFilters();
    this.renderList();
    
    if (query.trim()) {
      this.showToast(`找到 ${this.filteredPlugins.length} 个匹配的插件`, 'info');
    }
  }

  /**
   * 过滤插件
   * @param {string} filter - 过滤条件 (all, started, stopped, loaded, error)
   */
  filter(filter) {
    this.currentFilter = filter;
    this.applyFilters();
    this.renderList();
    
    // 更新过滤按钮样式
    this.container.querySelectorAll('.ps-filter-btn').forEach(btn => {
      btn.classList.toggle('ps-filter-active', btn.dataset.filter === filter);
    });
  }

  /**
   * 显示/隐藏加载状态
   * @param {boolean} show - 是否显示
   */
  showLoading(show) {
    let loader = this.container.querySelector('.ps-loading');
    
    if (show) {
      if (!loader) {
        loader = document.createElement('div');
        loader.className = 'ps-loading';
        loader.innerHTML = '<div class="ps-spinner"></div><span>加载中...</span>';
        loader.style.cssText = `
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 20px;
          color: #888;
        `;
        
        // 添加 spinner 样式
        if (!document.querySelector('#ps-loading-style')) {
          const style = document.createElement('style');
          style.id = 'ps-loading-style';
          style.textContent = `
            .ps-spinner {
              width: 20px;
              height: 20px;
              border: 2px solid #3a3a5a;
              border-top-color: #00d4ff;
              border-radius: 50%;
              animation: ps-spin 0.8s linear infinite;
            }
            @keyframes ps-spin {
              to { transform: rotate(360deg); }
            }
          `;
          document.head.appendChild(style);
        }
        
        const listEl = this.container.querySelector('.ps-list');
        if (listEl) {
          listEl.appendChild(loader);
        }
      }
    } else {
      if (loader) loader.remove();
    }
  }

  /**
   * 延迟函数
   * @param {number} ms - 延迟毫秒数
   * @returns {Promise}
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * HTML 转义
   * @param {string} text - 待转义文本
   * @returns {string} 转义后文本
   */
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * 渲染插件商店界面
   */
  render() {
    this.container.innerHTML = `
      <div class="ps">
        <h2>🔌 插件商店</h2>
        
        <div class="ps-controls">
          <input type="text" 
                 placeholder="搜索插件..." 
                 oninput="this.closest('.ps')._s.search(this.value)"
                 style="flex: 1;">
          <button onclick="this.closest('.ps')._s.loadPlugins()" class="ps-btn">🔄 刷新</button>
        </div>
        
        <div class="ps-filters" style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
          <button class="ps-filter-btn ps-filter-active" data-filter="all" onclick="this.closest('.ps')._s.filter('all')">全部</button>
          <button class="ps-filter-btn" data-filter="started" onclick="this.closest('.ps')._s.filter('started')">运行中</button>
          <button class="ps-filter-btn" data-filter="stopped" onclick="this.closest('.ps')._s.filter('stopped')">已停止</button>
          <button class="ps-filter-btn" data-filter="loaded" onclick="this.closest('.ps')._s.filter('loaded')">已加载</button>
          <button class="ps-filter-btn" data-filter="error" onclick="this.closest('.ps')._s.filter('error')">错误</button>
        </div>
        
        <div class="ps-list"></div>
      </div>
    `;
    
    this.container.querySelector('.ps')._s = this;
    
    // 添加响应式样式
    if (!document.querySelector('#ps-style')) {
      const style = document.createElement('style');
      style.id = 'ps-style';
      style.textContent = `
        .ps { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .ps h2 { color: #00d4ff; margin-bottom: 16px; }
        .ps-controls { display: flex; gap: 8px; margin-bottom: 16px; }
        .ps-controls input { 
          flex: 1; 
          background: #252540; 
          border: 1px solid #3a3a5a; 
          border-radius: 6px; 
          padding: 8px 12px; 
          color: #e0e0e0; 
          font-size: 14px;
        }
        .ps-controls input:focus { border-color: #00d4ff; outline: none; }
        .ps-controls button { 
          background: #2a2a4a; 
          border: 1px solid #3a3a5a; 
          color: #e0e0e0; 
          padding: 8px 16px; 
          border-radius: 6px; 
          cursor: pointer; 
          font-size: 14px;
          transition: all 0.2s;
        }
        .ps-controls button:hover { background: #3a3a5a; border-color: #00d4ff; }
        .ps-btn {
          background: #2a2a4a;
          border: 1px solid #3a3a5a;
          color: #e0e0e0;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }
        .ps-btn:hover { background: #3a3a5a; border-color: #00d4ff; }
        .ps-btn-primary {
          background: #00d4ff;
          color: #0a0a1e;
          border-color: #00d4ff;
        }
        .ps-filter-btn {
          background: #252540;
          border: 1px solid #3a3a5a;
          color: #888;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          transition: all 0.2s;
        }
        .ps-filter-btn:hover {
          background: #2a2a4a;
          border-color: #00d4ff;
          color: #e0e0e0;
        }
        .ps-filter-active {
          background: #00d4ff;
          color: #0a0a1e;
          border-color: #00d4ff;
        }
        .ps-list { display: grid; gap: 12px; }
        .ps-card { 
          background: #1e1e3a; 
          border: 1px solid #3a3a5a; 
          border-radius: 8px; 
          padding: 16px; 
          display: flex; 
          justify-content: space-between; 
          align-items: center;
          transition: all 0.2s;
        }
        .ps-card:hover { border-color: #00d4ff; transform: translateY(-2px); }
        .ps-card.started { border-color: #6bcb77; }
        .ps-card.stopped { border-color: #ff4757; }
        .ps-card.loaded { border-color: #ffd93d; }
        .ps-card.error { border-color: #ff6b6b; }
        .badge { 
          display: inline-block; 
          padding: 2px 8px; 
          border-radius: 3px; 
          font-size: 11px; 
          margin-left: 4px;
        }
        .badge.core { background: #4dabf7; color: white; }
        .badge.tool { background: #ffd93d; color: black; }
        .badge.integration { background: #da77f2; color: white; }
        .badge.started { background: #6bcb77; color: black; }
        .badge.stopped { background: #ff4757; color: white; }
        .badge.loaded { background: #ffd93d; color: black; }
        .badge.error { background: #ff6b6b; color: white; }
        .ps-actions { display: flex; gap: 8px; }
        .ps-actions button { 
          background: #2a2a4a; 
          border: 1px solid #3a3a5a; 
          color: #e0e0e0; 
          padding: 6px 12px; 
          border-radius: 4px; 
          cursor: pointer; 
          font-size: 12px;
          transition: all 0.2s;
        }
        .ps-actions button:hover { background: #3a3a5a; border-color: #00d4ff; }
        .ps-actions button:first-child { background: #00d4ff; color: #0a0a1e; border-color: #00d4ff; }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
          .ps-card { flex-direction: column; align-items: flex-start; gap: 12px; }
          .ps-actions { width: 100%; justify-content: flex-end; }
          .ps-filters { justify-content: center; }
        }
      `;
      document.head.appendChild(style);
    }
  }

  /**
   * 渲染插件列表
   */
  renderList() {
    const el = this.container.querySelector('.ps-list');
    if (!el) return;
    
    if (!this.filteredPlugins.length) {
      el.innerHTML = '<p style="color: #888; text-align: center; padding: 40px 20px;">暂无插件</p>';
      return;
    }
    
    el.innerHTML = this.filteredPlugins.map(p => `
      <div class="ps-card ${p.state}">
        <div style="flex: 1;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <b>${this.escapeHtml(p.name)}</b> <small style="color: #888;">v${p.version || '1.0.0'}</small>
            <span class="badge ${p.type}">${p.type || 'unknown'}</span>
            <span class="badge ${p.state}">${p.state}</span>
          </div>
          <small style="color: #aaa; display: block; margin-bottom: 8px;">${this.escapeHtml(p.description || '暂无描述')}</small>
          ${p.author ? `<small style="color: #666;">作者: ${this.escapeHtml(p.author)}</small>` : ''}
        </div>
        <div class="ps-actions">
          <button onclick="this.closest('.ps')._s.viewDetails('${this.escapeHtml(p.name)}')">详情</button>
          <button onclick="this.closest('.ps')._s.toggle('${this.escapeHtml(p.name)}','${p.state}')">
            ${(p.state === 'started' || p.state === 'loaded') ? '卸载' : '加载'}
          </button>
          <button onclick="this.closest('.ps')._s.reload('${this.escapeHtml(p.name)}')">重载</button>
        </div>
      </div>
    `).join('');
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PluginStore };
}
