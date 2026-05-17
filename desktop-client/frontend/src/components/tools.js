const Tools = {
  async show() {
    App.showPanel('Tools', '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</div>');
    try {
      const data = await App.apiCall('/api/tools');
      this.renderTools(data.tools || []);
    } catch {
      App.showPanel('Tools', '<div style="text-align:center;padding:20px;color:var(--red);"><p>Cannot connect to backend</p><p style="font-size:12px;margin-top:8px;">Make sure backend is running on localhost:8000</p></div>');
    }
  },

  renderTools(tools) {
    const grouped = {};
    tools.forEach(t => {
      const cat = t.category || 'Uncategorized';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(t);
    });
    let html = '<div style="margin-bottom:16px;"><input type="text" id="toolSearch" placeholder="Search tools..." style="width:100%;padding:8px 12px;background:var(--bg-input);border:1px solid var(--border);border-radius:var(--radius);color:var(--text-primary);font-size:13px;outline:none;" /></div>';
    html += '<div style="margin-bottom:12px;font-size:12px;color:var(--text-muted);">Total: ' + tools.length + ' tools</div>';
    for (const [cat, items] of Object.entries(grouped)) {
      html += '<div class="tool-category-header">' + cat + '</div>';
      items.forEach(t => {
        html += '<div class="tool-card" data-name="' + (t.name||'') + '"><div class="tool-card-name">' + (t.name||'unknown') + '</div><div class="tool-card-desc">' + (t.description||'No description') + '</div><div class="tool-card-meta"><span>' + (t.type||'builtin') + '</span></div></div>';
      });
    }
    document.getElementById('panelContent').innerHTML = html;
    document.getElementById('toolSearch')?.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      document.querySelectorAll('.tool-card').forEach(card => {
        card.style.display = (card.dataset.name||'').toLowerCase().includes(q) ? '' : 'none';
      });
    });
  },
  init() {}
};
