const Status = {
  async show() {
    App.showPanel('System Status', '<div style="text-align:center;padding:20px;color:var(--text-muted);">Checking...</div>');
    try {
      const [health, memStats, agentStats] = await Promise.all([
        App.apiCall('/health'),
        App.apiCall('/api/memory/stats').catch(() => null),
        App.apiCall('/api/agent/stats').catch(() => null)
      ]);

      let html = '<div class="status-section"><h4>System</h4>';
      html += '<div class="status-row"><span class="status-label">Status</span><span class="status-value ' + (health.status==='healthy'?'online':'offline') + '">' + (health.status==='healthy'?'\u{1F7E2} Healthy':'\u{1F534} Error') + '</span></div>';
      html += '<div class="status-row"><span class="status-label">Version</span><span class="status-value">' + (health.version||'-') + '</span></div>';
      html += '<div class="status-row"><span class="status-label">Environment</span><span class="status-value">' + (health.environment||'-') + '</span></div>';
      html += '</div>';

      if (health.database) {
        html += '<div class="status-section"><h4>Database</h4>';
        for (const [k,v] of Object.entries(health.database)) {
          const ok = v===true||v==='ok'||v==='healthy';
          html += '<div class="status-row"><span class="status-label">'+k+'</span><span class="status-value '+(ok?'online':'offline')+'">'+v+'</span></div>';
        }
        html += '</div>';
      }

      const renderSection = (title, obj) => {
        if (!obj) return '';
        let s = '<div class="status-section"><h4>'+title+'</h4>';
        for (const [k,v] of Object.entries(obj)) {
          const val = typeof v==='object' ? JSON.stringify(v) : String(v);
          s += '<div class="status-row"><span class="status-label">'+k+'</span><span class="status-value">'+val+'</span></div>';
        }
        return s + '</div>';
      };
      html += renderSection('Memory', memStats);
      html += renderSection('Agent', agentStats);

      html += '<div class="status-section"><h4>Actions</h4>';
      html += '<button class="setting-btn" id="btnClearSession">Clear Current Session Memory</button>';
      html += '<button class="setting-btn" style="background:var(--red);margin-top:8px;" id="btnClearAll">Clear All Memory</button>';
      html += '</div>';

      document.getElementById('panelContent').innerHTML = html;
      document.getElementById('btnClearSession')?.addEventListener('click', () => this.clearCurrentSession());
      document.getElementById('btnClearAll')?.addEventListener('click', () => this.clearAllMemory());
    } catch {
      document.getElementById('panelContent').innerHTML = '<div style="text-align:center;padding:20px;color:var(--red);"><p>Cannot connect to backend</p></div>';
    }
  },

  async clearCurrentSession() {
    if (!App.state.currentChatId) { App.showToast('No active session'); return; }
    try {
      await App.apiCall('/api/memory/clear?session_id='+App.state.currentChatId, {method:'DELETE'});
      App.showToast('Session memory cleared');
    } catch { App.showToast('Operation failed'); }
  },

  async clearAllMemory() {
    if (!confirm('Clear ALL memory? This cannot be undone.')) return;
    try {
      await App.apiCall('/api/memory/clear', {method:'DELETE'});
      App.showToast('All memory cleared');
    } catch { App.showToast('Operation failed'); }
  },
  init() {}
};
