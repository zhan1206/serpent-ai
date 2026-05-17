/**
 * SerpentAI Skill Marketplace UI
 */
class SkillMarketplace {
  constructor(containerId, apiBaseUrl = '/api') {
    this.container = document.getElementById(containerId);
    this.apiUrl = apiBaseUrl;
    this.skills = [];
    this.init();
  }
  async init() { this.render(); await this.loadSkills(); }
  async loadSkills() {
    try {
      const resp = await fetch(`${this.apiUrl}/skills`);
      const data = await resp.json();
      this.skills = data.skills || [];
      this.renderList();
    } catch (e) { console.error(e); }
  }
  async install(url) {
    if (!url) { url = prompt('技能URL:'); if (!url) return; }
    await fetch(`${this.apiUrl}/skills/install`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ url }) });
    await this.loadSkills();
  }
  async remove(name) {
    if (!confirm(`移除 ${name}?`)) return;
    await fetch(`${this.apiUrl}/skills/${name}`, { method: 'DELETE' });
    await this.loadSkills();
  }
  async toggle(name, enabled) {
    await fetch(`${this.apiUrl}/skills/${name}/${enabled ? 'disable' : 'enable'}`, { method: 'POST' });
    await this.loadSkills();
  }
  async rate(name, r) {
    await fetch(`${this.apiUrl}/skills/${name}/rate?rating=${r}`, { method: 'POST' });
    await this.loadSkills();
  }
  async search(query) {
    if (!query.trim()) return this.loadSkills();
    const resp = await fetch(`${this.apiUrl}/skills/search?query=${encodeURIComponent(query)}`);
    const data = await resp.json();
    this.skills = data.results || [];
    this.renderList();
  }
  render() {
    this.container.innerHTML = `<div class="sm"><h2>🎯 技能市场</h2>
      <div class="sm-controls"><input placeholder="搜索技能..." oninput="this.closest('.sm')._s.search(this.value)">
      <button onclick="this.closest('.sm')._s.install()">📥 安装</button>
      <button onclick="this.closest('.sm')._s.loadSkills()">刷新</button></div>
      <div class="sm-list"></div></div>`;
    this.container.querySelector('.sm')._s = this;
  }
  renderList() {
    const el = this.container.querySelector('.sm-list');
    if (!this.skills.length) { el.innerHTML = '<p>暂无技能</p>'; return; }
    el.innerHTML = this.skills.map(s => `<div class="sm-card ${s.enabled ? '' : 'disabled'}">
      <div><span class="icon">${s.icon||'📦'}</span> <b>${s.display_name||s.name}</b> <small>v${s.version}</small>
      <span class="badge">${s.category}</span><br><small>${s.description}</small>
      ${s.rating ? `<br><small>★${s.rating} (${s.rating_count})</small>` : ''}</div>
      <div class="sm-actions"><button onclick="this.closest('.sm')._s.toggle('${s.name}',${s.enabled})">${s.enabled?'禁用':'启用'}</button>
      <button onclick="this.closest('.sm')._s.remove('${s.name}')">移除</button></div></div>`).join('');
  }
}
if (typeof module !== 'undefined') module.exports = { SkillMarketplace };
