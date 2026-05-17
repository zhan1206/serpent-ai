/**
 * SerpentAI Plugin Store UI
 */
class PluginStore {
  constructor(containerId, apiBaseUrl = '/api') {
    this.container = document.getElementById(containerId);
    this.apiUrl = apiBaseUrl;
    this.plugins = [];
    this.init();
  }
  async init() { this.render(); await this.loadPlugins(); }
  async loadPlugins() {
    try {
      const resp = await fetch(`${this.apiUrl}/plugins`);
      const data = await resp.json();
      this.plugins = data.plugins || [];
      this.renderList();
    } catch (e) { console.error(e); }
  }
  async toggle(name, state) {
    const endpoint = (state === 'started' || state === 'loaded' || state === 'initialized') ? 'unload' : 'load';
    await fetch(`${this.apiUrl}/plugins/${endpoint}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ name }) });
    await this.loadPlugins();
  }
  async reload(name) {
    await fetch(`${this.apiUrl}/plugins/reload`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ name }) });
    await this.loadPlugins();
  }
  async search(query) {
    if (!query.trim()) return this.loadPlugins();
    const resp = await fetch(`${this.apiUrl}/plugins/search?query=${encodeURIComponent(query)}`);
    const data = await resp.json();
    this.plugins = data.results || [];
    this.renderList();
  }
  render() {
    this.container.innerHTML = `<div class="ps"><h2>🔌 插件商店</h2>
      <div class="ps-controls"><input placeholder="搜索插件..." oninput="this.closest('.ps')._s.search(this.value)">
      <button onclick="this.closest('.ps')._s.loadPlugins()">刷新</button></div>
      <div class="ps-list"></div></div>`;
    this.container.querySelector('.ps')._s = this;
  }
  renderList() {
    const el = this.container.querySelector('.ps-list');
    if (!this.plugins.length) { el.innerHTML = '<p>暂无插件</p>'; return; }
    el.innerHTML = this.plugins.map(p => `<div class="ps-card ${p.state}">
      <div><b>${p.name}</b> <small>v${p.version}</small> <span class="badge ${p.type}">${p.type}</span>
      <span class="badge ${p.state}">${p.state}</span><br><small>${p.description}</small></div>
      <div class="ps-actions"><button onclick="this.closest('.ps')._s.toggle('${p.name}','${p.state}')">${(p.state==='started'||p.state==='loaded')?'卸载':'加载'}</button>
      <button onclick="this.closest('.ps')._s.reload('${p.name}')">重载</button></div></div>`).join('');
  }
}
if (typeof module !== 'undefined') module.exports = { PluginStore };
