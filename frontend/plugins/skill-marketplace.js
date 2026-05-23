/**
 * SerpentAI Skill Marketplace UI
 * 功能：技能市场界面，支持安装/移除/启用/禁用技能，搜索技能，评分
 * 要求：原生 JavaScript，包含错误处理、加载状态、用户反馈
 */

class SkillMarketplace {
  /**
   * 构造函数
   * @param {string} containerId - 容器元素 ID
   * @param {string} apiBaseUrl - API 基础 URL
   */
  constructor(containerId, apiBaseUrl = '/api') {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`SkillMarketplace: 找不到容器元素 #${containerId}`);
      return;
    }
    this.apiUrl = apiBaseUrl;
    this.skills = [];
    this.isLoading = false;
    this.init();
  }

  /**
   * 初始化技能市场
   */
  async init() {
    this.render();
    await this.loadSkills();
  }

  /**
   * 显示 toast 通知
   * @param {string} message - 通知消息
   * @param {string} type - 类型：success, error, info
   */
  showToast(message, type = 'info') {
    // 移除已有的 toast
    const existingToast = document.body.querySelector('.sm-toast');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = `sm-toast sm-toast-${type}`;
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
      animation: sm-slideIn 0.3s ease;
      background: ${type === 'success' ? '#6bcb77' : type === 'error' ? '#ff4757' : '#00d4ff'};
    `;
    
    // 添加动画样式
    if (!document.querySelector('#sm-toast-style')) {
      const style = document.createElement('style');
      style.id = 'sm-toast-style';
      style.textContent = `
        @keyframes sm-slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes sm-slideOut {
          from { transform: translateX(0); opacity: 1; }
          to { transform: translateX(100px); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    // 3秒后自动移除
    setTimeout(() => {
      toast.style.animation = 'sm-slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  /**
   * 加载技能列表
   */
  async loadSkills() {
    if (this.isLoading) return;
    this.isLoading = true;
    this.showLoading(true);
    
    try {
      const resp = await fetch(`${this.apiUrl}/skills`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      const data = await resp.json();
      this.skills = data.skills || [];
      this.renderList();
      this.showToast(`已加载 ${this.skills.length} 个技能`, 'success');
    } catch (e) {
      console.error('加载技能失败:', e);
      this.showToast(`加载技能失败: ${e.message}`, 'error');
      this.skills = [];
      this.renderList();
    } finally {
      this.isLoading = false;
      this.showLoading(false);
    }
  }

  /**
   * 安装技能
   * @param {string} url - 技能 URL 或 npm 包名
   */
  async install(url) {
    if (!url) {
      url = prompt('请输入技能 URL 或 npm 包名:');
      if (!url) return;
    }
    
    this.showLoading(true);
    
    try {
      const resp = await fetch(`${this.apiUrl}/skills/install`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ url })
      });
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      const result = await resp.json();
      this.showToast(`技能安装成功: ${result.name || url}`, 'success');
      await this.loadSkills();
    } catch (e) {
      console.error('安装技能失败:', e);
      this.showToast(`安装失败: ${e.message}`, 'error');
      this.showLoading(false);
    }
  }

  /**
   * 移除技能
   * @param {string} name - 技能名称
   */
  async remove(name) {
    if (!confirm(`确定要移除技能 "${name}" 吗？此操作不可撤销。`)) return;
    
    this.showLoading(true);
    
    try {
      const resp = await fetch(`${this.apiUrl}/skills/${name}`, {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      this.showToast(`技能 "${name}" 已移除`, 'success');
      await this.loadSkills();
    } catch (e) {
      console.error('移除技能失败:', e);
      this.showToast(`移除失败: ${e.message}`, 'error');
      this.showLoading(false);
    }
  }

  /**
   * 切换技能状态（启用/禁用）
   * @param {string} name - 技能名称
   * @param {boolean} enabled - 当前是否启用
   */
  async toggle(name, enabled) {
    this.showLoading(true);
    
    try {
      const action = enabled ? 'disable' : 'enable';
      const resp = await fetch(`${this.apiUrl}/skills/${name}/${action}`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      this.showToast(`技能 "${name}" 已${enabled ? '禁用' : '启用'}`, 'success');
      await this.loadSkills();
    } catch (e) {
      console.error('切换技能状态失败:', e);
      this.showToast(`操作失败: ${e.message}`, 'error');
      this.showLoading(false);
    }
  }

  /**
   * 评分技能
   * @param {string} name - 技能名称
   * @param {number} rating - 评分（1-5）
   */
  async rate(name, rating) {
    try {
      const resp = await fetch(`${this.apiUrl}/skills/${name}/rate?rating=${rating}`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      this.showToast(`已为技能 "${name}" 评分 ${rating} 星`, 'success');
      await this.loadSkills();
    } catch (e) {
      console.error('评分失败:', e);
      this.showToast(`评分失败: ${e.message}`, 'error');
    }
  }

  /**
   * 搜索技能
   * @param {string} query - 搜索关键词
   */
  async search(query) {
    if (!query.trim()) {
      await this.loadSkills();
      return;
    }
    
    this.showLoading(true);
    
    try {
      const resp = await fetch(`${this.apiUrl}/skills/search?query=${encodeURIComponent(query)}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      
      const data = await resp.json();
      this.skills = data.results || [];
      this.renderList();
      this.showToast(`找到 ${this.skills.length} 个匹配的技能`, 'info');
    } catch (e) {
      console.error('搜索技能失败:', e);
      this.showToast(`搜索失败: ${e.message}`, 'error');
      this.skills = [];
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
    let loader = this.container.querySelector('.sm-loading');
    
    if (show) {
      if (!loader) {
        loader = document.createElement('div');
        loader.className = 'sm-loading';
        loader.innerHTML = '<div class="sm-spinner"></div><span>加载中...</span>';
        loader.style.cssText = `
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 20px;
          color: #888;
        `;
        
        // 添加 spinner 样式
        if (!document.querySelector('#sm-loading-style')) {
          const style = document.createElement('style');
          style.id = 'sm-loading-style';
          style.textContent = `
            .sm-spinner {
              width: 20px;
              height: 20px;
              border: 2px solid #3a3a5a;
              border-top-color: #00d4ff;
              border-radius: 50%;
              animation: sm-spin 0.8s linear infinite;
            }
            @keyframes sm-spin {
              to { transform: rotate(360deg); }
            }
          `;
          document.head.appendChild(style);
        }
        
        this.container.querySelector('.sm-list').appendChild(loader);
      }
    } else {
      if (loader) loader.remove();
    }
  }

  /**
   * 渲染技能市场界面
   */
  render() {
    this.container.innerHTML = `
      <div class="sm">
        <h2>🎯 技能市场</h2>
        <div class="sm-controls">
          <input type="text" placeholder="搜索技能..." oninput="this.closest('.sm')._s.search(this.value)">
          <button onclick="this.closest('.sm')._s.install()">📥 安装</button>
          <button onclick="this.closest('.sm')._s.loadSkills()">🔄 刷新</button>
        </div>
        <div class="sm-list"></div>
      </div>
    `;
    this.container.querySelector('.sm')._s = this;
    
    // 添加响应式样式
    if (!document.querySelector('#sm-style')) {
      const style = document.createElement('style');
      style.id = 'sm-style';
      style.textContent = `
        .sm { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .sm h2 { color: #00d4ff; margin-bottom: 16px; }
        .sm-controls { display: flex; gap: 8px; margin-bottom: 16px; }
        .sm-controls input { 
          flex: 1; 
          background: #252540; 
          border: 1px solid #3a3a5a; 
          border-radius: 6px; 
          padding: 8px 12px; 
          color: #e0e0e0; 
          font-size: 14px;
        }
        .sm-controls input:focus { border-color: #00d4ff; outline: none; }
        .sm-controls button { 
          background: #2a2a4a; 
          border: 1px solid #3a3a5a; 
          color: #e0e0e0; 
          padding: 8px 16px; 
          border-radius: 6px; 
          cursor: pointer; 
          font-size: 14px;
          transition: all 0.2s;
        }
        .sm-controls button:hover { background: #3a3a5a; border-color: #00d4ff; }
        .sm-controls button:first-of-type { background: #00d4ff; color: #0a0a1e; border-color: #00d4ff; }
        .sm-list { display: grid; gap: 12px; }
        .sm-card { 
          background: #1e1e3a; 
          border: 1px solid #3a3a5a; 
          border-radius: 8px; 
          padding: 16px; 
          display: flex; 
          justify-content: space-between; 
          align-items: center;
          transition: all 0.2s;
        }
        .sm-card:hover { border-color: #00d4ff; transform: translateY(-2px); }
        .sm-card.disabled { opacity: 0.5; border-color: #555; }
        .sm-card .icon { font-size: 24px; margin-right: 8px; }
        .badge { 
          display: inline-block; 
          padding: 2px 8px; 
          border-radius: 3px; 
          font-size: 11px; 
          margin-left: 4px;
          background: #3a3a5a;
          color: #aaa;
        }
        .sm-actions { display: flex; gap: 8px; }
        .sm-actions button { 
          background: #2a2a4a; 
          border: 1px solid #3a3a5a; 
          color: #e0e0e0; 
          padding: 6px 12px; 
          border-radius: 4px; 
          cursor: pointer; 
          font-size: 12px;
          transition: all 0.2s;
        }
        .sm-actions button:hover { background: #3a3a5a; border-color: #00d4ff; }
        .sm-actions button:first-child { background: #00d4ff; color: #0a0a1e; border-color: #00d4ff; }
        
        /* 评分星星 */
        .rating {
          display: inline-block;
          margin-left: 8px;
        }
        .rating span {
          cursor: pointer;
          font-size: 16px;
          color: #ffd93d;
        }
        .rating span:hover { transform: scale(1.2); }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
          .sm-card { flex-direction: column; align-items: flex-start; gap: 12px; }
          .sm-actions { width: 100%; justify-content: flex-end; }
        }
      `;
      document.head.appendChild(style);
    }
  }

  /**
   * 渲染技能列表
   */
  renderList() {
    const el = this.container.querySelector('.sm-list');
    if (!el) return;
    
    if (!this.skills.length) {
      el.innerHTML = '<p style="color: #888; text-align: center; padding: 40px 20px;">暂无技能</p>';
      return;
    }
    
    el.innerHTML = this.skills.map(s => `
      <div class="sm-card ${s.enabled ? '' : 'disabled'}">
        <div>
          <span class="icon">${s.icon || '📦'}</span>
          <b>${s.display_name || s.name}</b> <small style="color: #888;">v${s.version || '1.0.0'}</small>
          <span class="badge">${s.category || 'other'}</span>
          <br>
          <small style="color: #aaa;">${s.description || '暂无描述'}</small>
          ${s.rating ? `
            <br>
            <small style="color: #ffd93d;">★ ${s.rating.toFixed(1)} (${s.rating_count || 0} 评分)</small>
            <div class="rating">
              ${[1,2,3,4,5].map(i => `
                <span onclick="this.closest('.sm')._s.rate('${s.name}',${i})">${i <= Math.round(s.rating) ? '★' : '☆'}</span>
              `).join('')}
            </div>
          ` : ''}
        </div>
        <div class="sm-actions">
          <button onclick="this.closest('.sm')._s.toggle('${s.name}',${s.enabled})">
            ${s.enabled ? '禁用' : '启用'}
          </button>
          <button onclick="this.closest('.sm')._s.remove('${s.name}')">移除</button>
        </div>
      </div>
    `).join('');
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SkillMarketplace };
}
