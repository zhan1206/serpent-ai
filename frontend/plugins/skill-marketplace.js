/**
 * SerpentAI Skill Marketplace UI
 * 功能：技能市场界面，支持安装/移除/启用/禁用技能，搜索技能，评分，查看详情
 * 要求：原生 JavaScript，包含错误处理、加载状态、用户反馈
 * 版本：2.0.0
 */

class SkillMarketplace {
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
      console.error(`SkillMarketplace: 找不到容器元素 #${containerId}`);
      return;
    }
    
    this.apiUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
    this.timeout = options.timeout || 30000;
    this.retryAttempts = options.retryAttempts || 3;
    
    this.skills = [];
    this.filteredSkills = [];
    this.isLoading = false;
    this.currentFilter = 'all'; // all, enabled, disabled
    this.currentCategory = 'all'; // all, other categories
    this.searchQuery = '';
    
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
   * @param {string} type - 类型：success, error, info, warning
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
      background: ${type === 'success' ? '#6bcb77' : type === 'error' ? '#ff4757' : type === 'warning' ? '#ffd93d' : '#00d4ff'};
      color: ${type === 'warning' ? '#000' : '#fff'};
      max-width: 400px;
      word-break: break-word;
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
   * 加载技能列表（带重试）
   * @param {number} attempt - 当前尝试次数
   */
  async loadSkills(attempt = 1) {
    if (this.isLoading) return;
    
    this.isLoading = true;
    this.showLoading(true);
    
    try {
      const data = await this.fetchWithTimeout('/skills');
      this.skills = data.skills || [];
      this.applyFilters();
      this.renderList();
      this.showToast(`已加载 ${this.skills.length} 个技能`, 'success');
    } catch (e) {
      console.error(`加载技能失败 (尝试 ${attempt}/${this.retryAttempts}):`, e);
      
      if (attempt < this.retryAttempts) {
        await this.delay(1000 * attempt);
        return this.loadSkills(attempt + 1);
      }
      
      this.showToast(`加载技能失败: ${e.message}`, 'error');
      this.skills = [];
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
    let filtered = [...this.skills];
    
    // 应用状态过滤
    if (this.currentFilter !== 'all') {
      filtered = filtered.filter(s => 
        this.currentFilter === 'enabled' ? s.enabled : !s.enabled
      );
    }
    
    // 应用分类过滤
    if (this.currentCategory !== 'all') {
      filtered = filtered.filter(s => s.category === this.currentCategory);
    }
    
    // 应用搜索过滤
    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(s => 
        s.name.toLowerCase().includes(query) ||
        (s.display_name && s.display_name.toLowerCase().includes(query)) ||
        (s.description && s.description.toLowerCase().includes(query))
      );
    }
    
    this.filteredSkills = filtered;
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
      const result = await this.fetchWithTimeout('/skills/install', {
        method: 'POST',
        body: JSON.stringify({ url })
      });
      
      this.showToast(`技能安装成功: ${result.name || url}`, 'success');
      await this.loadSkills();
    } catch (e) {
      console.error('安装技能失败:', e);
      this.showToast(`安装失败: ${e.message}`, 'error');
      this.showLoading(false);
    }
  }

  /**
   * 从市场安装技能
   * @param {string} skillName - 技能名称
   */
  async installFromMarketplace(skillName) {
    if (!confirm(`确定要安装技能 "${skillName}" 吗？`)) return;
    
    this.showLoading(true);
    
    try {
      const result = await this.fetchWithTimeout(`/skills/marketplace/${skillName}/install`, {
        method: 'POST'
      });
      
      this.showToast(`技能 "${skillName}" 安装成功`, 'success');
      await this.loadSkills();
    } catch (e) {
      console.error('从市场安装技能失败:', e);
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
      await this.fetchWithTimeout(`/skills/${name}`, {
        method: 'DELETE'
      });
      
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
      await this.fetchWithTimeout(`/skills/${name}/${action}`, {
        method: 'POST'
      });
      
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
      await this.fetchWithTimeout(`/skills/${name}/rate?rating=${rating}`, {
        method: 'POST'
      });
      
      this.showToast(`已为技能 "${name}" 评分 ${rating} 星`, 'success');
      await this.loadSkills();
    } catch (e) {
      console.error('评分失败:', e);
      this.showToast(`评分失败: ${e.message}`, 'error');
    }
  }

  /**
   * 查看技能详情
   * @param {string} name - 技能名称
   */
  async viewDetails(name) {
    const skill = this.skills.find(s => s.name === name);
    if (!skill) {
      this.showToast(`找不到技能 "${name}"`, 'error');
      return;
    }
    
    // 创建详情模态框
    const modal = document.createElement('div');
    modal.className = 'sm-details-modal';
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
        <h2 style="color: #00d4ff; margin-bottom: 16px;">
          ${skill.icon || '📦'} ${this.escapeHtml(skill.display_name || skill.name)}
        </h2>
        
        <div style="margin-bottom: 12px;">
          <b>名称:</b> <span style="color: #aaa;">${this.escapeHtml(skill.name)}</span>
        </div>
        
        <div style="margin-bottom: 12px;">
          <b>版本:</b> <span style="color: #aaa;">${skill.version || '1.0.0'}</span>
        </div>
        
        <div style="margin-bottom: 12px;">
          <b>状态:</b> 
          <span class="badge" style="background: ${skill.enabled ? '#6bcb77' : '#555'}; color: ${skill.enabled ? '#000' : '#fff'};">
            ${skill.enabled ? '已启用' : '已禁用'}
          </span>
        </div>
        
        <div style="margin-bottom: 12px;">
          <b>分类:</b> <span style="color: #aaa;">${skill.category || 'other'}</span>
        </div>
        
        ${skill.rating ? `
          <div style="margin-bottom: 12px;">
            <b>评分:</b> 
            <span style="color: #ffd93d;">★ ${skill.rating.toFixed(1)}</span>
            <span style="color: #888;">(${skill.rating_count || 0} 评分)</span>
          </div>
        ` : ''}
        
        <div style="margin-bottom: 16px;">
          <b>描述:</b>
          <p style="color: #aaa; margin-top: 8px; line-height: 1.6;">${this.escapeHtml(skill.description || '暂无描述')}</p>
        </div>
        
        ${skill.author ? `
          <div style="margin-bottom: 12px;">
            <b>作者:</b> <span style="color: #aaa;">${this.escapeHtml(skill.author)}</span>
          </div>
        ` : ''}
        
        ${skill.homepage ? `
          <div style="margin-bottom: 12px;">
            <b>主页:</b> <a href="${this.escapeHtml(skill.homepage)}" target="_blank" style="color: #00d4ff;">${this.escapeHtml(skill.homepage)}</a>
          </div>
        ` : ''}
        
        ${skill.license ? `
          <div style="margin-bottom: 12px;">
            <b>许可证:</b> <span style="color: #aaa;">${this.escapeHtml(skill.license)}</span>
          </div>
        ` : ''}
        
        ${skill.tags && skill.tags.length > 0 ? `
          <div style="margin-bottom: 16px;">
            <b>标签:</b>
            <div style="margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap;">
              ${skill.tags.map(tag => `
                <span class="badge" style="background: #3a3a5a; color: #aaa;">${this.escapeHtml(tag)}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
        
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 24px;">
          <button class="sm-btn" onclick="this.closest('.sm-details-modal').remove()">关闭</button>
          <button class="sm-btn sm-btn-primary" onclick="this.closest('.sm-details-modal').querySelector('#sm-toggle-btn').click()">
            ${skill.enabled ? '禁用' : '启用'}
          </button>
          <button id="sm-toggle-btn" style="display: none;"></button>
        </div>
      </div>
    `;
    
    // 切换状态按钮
    modal.querySelector('#sm-toggle-btn').addEventListener('click', async () => {
      await this.toggle(skill.name, skill.enabled);
      modal.remove();
    });
    
    // 添加按钮样式
    if (!document.querySelector('#sm-details-style')) {
      const style = document.createElement('style');
      style.id = 'sm-details-style';
      style.textContent = `
        .sm-btn {
          background: #2a2a4a;
          border: 1px solid #3a3a5a;
          color: #e0e0e0;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }
        .sm-btn:hover {
          background: #3a3a5a;
          border-color: #00d4ff;
        }
        .sm-btn-primary {
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
   * 搜索技能
   * @param {string} query - 搜索关键词
   */
  async search(query) {
    this.searchQuery = query;
    this.applyFilters();
    this.renderList();
    
    if (query.trim()) {
      this.showToast(`找到 ${this.filteredSkills.length} 个匹配的技能`, 'info');
    }
  }

  /**
   * 过滤技能
   * @param {string} filter - 过滤条件 (all, enabled, disabled)
   */
  filter(filter) {
    this.currentFilter = filter;
    this.applyFilters();
    this.renderList();
    
    // 更新过滤按钮样式
    this.container.querySelectorAll('.sm-filter-btn').forEach(btn => {
      btn.classList.toggle('sm-filter-active', btn.dataset.filter === filter);
    });
  }

  /**
   * 按分类过滤技能
   * @param {string} category - 分类名称
   */
  filterByCategory(category) {
    this.currentCategory = category;
    this.applyFilters();
    this.renderList();
    
    // 更新分类按钮样式
    this.container.querySelectorAll('.sm-category-btn').forEach(btn => {
      btn.classList.toggle('sm-category-active', btn.dataset.category === category);
    });
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
        
        const listEl = this.container.querySelector('.sm-list');
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
   * 渲染技能市场界面
   */
  render() {
    // 获取所有分类
    const categories = ['all', ...new Set(this.skills.map(s => s.category || 'other'))];
    
    this.container.innerHTML = `
      <div class="sm">
        <h2>🎯 技能市场</h2>
        
        <div class="sm-controls">
          <input type="text" 
                 placeholder="搜索技能..." 
                 oninput="this.closest('.sm')._s.search(this.value)"
                 style="flex: 1;">
          <button onclick="this.closest('.sm')._s.install()" class="sm-btn sm-btn-primary">📥 安装</button>
          <button onclick="this.closest('.sm')._s.loadSkills()" class="sm-btn">🔄 刷新</button>
        </div>
        
        <div class="sm-filters" style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
          <button class="sm-filter-btn sm-filter-active" data-filter="all" onclick="this.closest('.sm')._s.filter('all')">全部</button>
          <button class="sm-filter-btn" data-filter="enabled" onclick="this.closest('.sm')._s.filter('enabled')">已启用</button>
          <button class="sm-filter-btn" data-filter="disabled" onclick="this.closest('.sm')._s.filter('disabled')">已禁用</button>
        </div>
        
        <div class="sm-categories" style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
          ${categories.map(cat => `
            <button class="sm-category-btn ${cat === 'all' ? 'sm-category-active' : ''}" 
                    data-category="${cat}" 
                    onclick="this.closest('.sm')._s.filterByCategory('${cat}')">
              ${cat === 'all' ? '全部分类' : cat}
            </button>
          `).join('')}
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
        .sm-btn {
          background: #2a2a4a;
          border: 1px solid #3a3a5a;
          color: #e0e0e0;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }
        .sm-btn:hover { background: #3a3a5a; border-color: #00d4ff; }
        .sm-btn-primary {
          background: #00d4ff;
          color: #0a0a1e;
          border-color: #00d4ff;
        }
        .sm-filter-btn {
          background: #252540;
          border: 1px solid #3a3a5a;
          color: #888;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          transition: all 0.2s;
        }
        .sm-filter-btn:hover {
          background: #2a2a4a;
          border-color: #00d4ff;
          color: #e0e0e0;
        }
        .sm-filter-active {
          background: #00d4ff;
          color: #0a0a1e;
          border-color: #00d4ff;
        }
        .sm-category-btn {
          background: #252540;
          border: 1px solid #3a3a5a;
          color: #888;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          transition: all 0.2s;
        }
        .sm-category-btn:hover {
          background: #2a2a4a;
          border-color: #00d4ff;
          color: #e0e0e0;
        }
        .sm-category-active {
          background: #3a3a5a;
          color: #00d4ff;
          border-color: #00d4ff;
        }
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
          transition: transform 0.2s;
        }
        .rating span:hover { transform: scale(1.2); }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
          .sm-card { flex-direction: column; align-items: flex-start; gap: 12px; }
          .sm-actions { width: 100%; justify-content: flex-end; }
          .sm-filters { justify-content: center; }
          .sm-categories { justify-content: center; }
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
    
    if (!this.filteredSkills.length) {
      el.innerHTML = '<p style="color: #888; text-align: center; padding: 40px 20px;">暂无技能</p>';
      return;
    }
    
    el.innerHTML = this.filteredSkills.map(s => `
      <div class="sm-card ${s.enabled ? '' : 'disabled'}">
        <div style="flex: 1;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span class="icon">${s.icon || '📦'}</span>
            <b>${this.escapeHtml(s.display_name || s.name)}</b> <small style="color: #888;">v${s.version || '1.0.0'}</small>
            <span class="badge">${s.category || 'other'}</span>
            ${s.enabled ? '' : '<span class="badge" style="background: #555;">已禁用</span>'}
          </div>
          <small style="color: #aaa; display: block; margin-bottom: 8px;">${this.escapeHtml(s.description || '暂无描述')}</small>
          ${s.author ? `<small style="color: #666;">作者: ${this.escapeHtml(s.author)}</small>` : ''}
          ${s.rating ? `
            <br>
            <small style="color: #ffd93d;">★ ${s.rating.toFixed(1)} (${s.rating_count || 0} 评分)</small>
            <div class="rating">
              ${[1,2,3,4,5].map(i => `
                <span onclick="this.closest('.sm')._s.rate('${this.escapeHtml(s.name)}',${i})">${i <= Math.round(s.rating) ? '★' : '☆'}</span>
              `).join('')}
            </div>
          ` : ''}
        </div>
        <div class="sm-actions">
          <button onclick="this.closest('.sm')._s.viewDetails('${this.escapeHtml(s.name)}')">详情</button>
          <button onclick="this.closest('.sm')._s.toggle('${this.escapeHtml(s.name)}',${s.enabled})">
            ${s.enabled ? '禁用' : '启用'}
          </button>
          <button onclick="this.closest('.sm')._s.remove('${this.escapeHtml(s.name)}')">移除</button>
        </div>
      </div>
    `).join('');
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SkillMarketplace };
}
