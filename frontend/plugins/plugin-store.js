/**
 * SerpentAI Plugin Store UI
 * 功能：插件管理界面，支持加载/卸载/重载插件，搜索插件
 * 要求：原生 JavaScript，包含错误处理、加载状态、用户反馈
 */

class PluginStore {
  /**
   * 构造函数
   * @param {string} containerId - 容器元素 ID
   * @param {string} apiBaseUrl - API 基础 URL
   */
  constructor(containerId, apiBaseUrl = '/api') {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`PluginStore: 找不到容器元素 #${containerId}`);
      return;
    }
    this.apiUrl = apiBaseUrl;
    this.plugins = [];
    this.isLoading = false;
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
   * @param {string} type - 类型：success, error, info
   */
  showToast(message, type = 'info') {
    // 移除已有的 toast
    const existingToast = this.container.querySelector('.ps-toast');
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
      animation: slideIn 0.3s ease;
      background: ${type === 'success' ? '#6bcb77' : type === 'error' ? '#ff4757' : '#00d4ff'};
    `;
    
    // 添加动画样式
    if (!document.querySelector('#ps-toast-style')) {
      const style = document.createElement('style');
      style.id = 'ps-toast-style';
      style.textContent = `
        @keyframes slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
          from { transform: translateX(0); opacity: 1; }
          to { transform: translateX(100px); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    // 3秒后自动移除
    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  /**
   * 加载插件列表
   */
  async loadPlugins() {
    if (this.isLoading) return;
    this.isLoading = true;
    this.showLoading(true);
    
    try {
      const resp = await fetch(`${this.apiUrl}/plugins`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      const data = await resp.json();
      this.plugins = data.plugins || [];
      this.renderList();
      this.showToast(`已加载 ${this.plugins.length} 个插件`, 'success');
    } catch (e) {
      console.error('加载插件失败:', e);
      this.showToast(`加载插件失败: ${e.message}`, 'error');
      this.plugins = [];
      this.renderList();
    } finally {
      this.isLoading = false;
      this.showLoading(false);
    }
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
      const resp = await fetch(`${this.apiUrl}/plugins/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ name })
      });
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
      }
      
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
    this.showLoading(true);
    
    try {
      const resp = await fetch(`${this.apiUrl}/plugins/reload`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ name })
      });
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      this.showToast(`插件 "${name}" 重载成功`, 'success');
      await this.loadPlugins();
    } catch (e) {
      console.error('重载插件失败:', e);
      this.showToast(`重载插件失败: ${e.message}`, 'error');
      this.showLoading(false);
    }
  }

  /**
   * 搜索插件
   * @param {string} query - 搜索关键词
   */
  async search(query) {
    if (!query.trim()) {
      await this.loadPlugins();
      return;
    }
    
    this.showLoading(true);
    
    try {
      const resp = await fetch(`${this.apiUrl}/plugins/search?query=${encodeURIComponent(query)}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      const data = await resp.json();
      this.plugins = data.results || [];
      this.renderList();
      this.showToast(`找到 ${this.plugins.length} 个匹配的插件`, 'info');
    } catch (e) {
      console.error('搜索插件失败:', e);
      this.showToast(`搜索失败: ${e.message}`, 'error');
      this.plugins = [];
      this.renderList();
    } finally {
      this.showLoading(false);
    }
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
        
        this.container.querySelector('.ps-list').appendChild(loader);
      }
    } else {
      if (loader) loader.remove();
    }
  }

  /**
   * 渲染插件商店界面
   */
  render() {
    this.container.innerHTML = `
      <div class="ps">
        <h2>🔌 插件商店</h2>
        <div class="ps-controls">
          <input type="text" placeholder="搜索插件..." oninput="this.closest('.ps')._s.search(this.value)">
          <button onclick="this.closest('.ps')._s.loadPlugins()">🔄 刷新</button>
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
    
    if (!this.plugins.length) {
      el.innerHTML = '<p style="color: #888; text-align: center; padding: 40px 20px;">暂无插件</p>';
      return;
    }
    
    el.innerHTML = this.plugins.map(p => `
      <div class="ps-card ${p.state}">
        <div>
          <b>${p.name}</b> <small style="color: #888;">v${p.version}</small>
          <span class="badge ${p.type}">${p.type}</span>
          <span class="badge ${p.state}">${p.state}</span>
          <br>
          <small style="color: #aaa;">${p.description || '暂无描述'}</small>
        </div>
        <div class="ps-actions">
          <button onclick="this.closest('.ps')._s.toggle('${p.name}','${p.state}')">
            ${(p.state === 'started' || p.state === 'loaded') ? '卸载' : '加载'}
          </button>
          <button onclick="this.closest('.ps')._s.reload('${p.name}')">重载</button>
        </div>
      </div>
    `).join('');
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PluginStore };
}
