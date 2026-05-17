const Settings = {
  show() {
    const s = App.state.settings;
    const modelOpts = [
      ...App.state.models.map(m => `<option value="${m}" ${m === s.model ? 'selected' : ''}>${m}</option>`),
      '<option value="gpt-4o"' + (s.model==='gpt-4o'?' selected':'') + '>gpt-4o</option>',
      '<option value="gpt-3.5-turbo"' + (s.model==='gpt-3.5-turbo'?' selected':'') + '>gpt-3.5-turbo</option>',
      '<option value="claude-3-opus"' + (s.model==='claude-3-opus'?' selected':'') + '>claude-3-opus</option>',
      '<option value="local"' + (s.model==='local'?' selected':'') + '>Local Model</option>'
    ].join('');

    App.showPanel('Settings', `
      <div class="setting-group"><label>Model</label><select id="setModel">${modelOpts}</select></div>
      <div class="setting-group"><label>Temperature</label>
        <div class="setting-range"><input type="range" id="setTemp" min="0" max="2" step="0.1" value="${s.temperature}" /><span class="range-value" id="setTempVal">${s.temperature}</span></div>
      </div>
      <div class="setting-group"><label>Max Tokens</label><input type="number" id="setMaxTokens" value="${s.maxTokens}" min="256" max="128000" step="256" /></div>
      <div class="setting-group"><label>System Prompt</label>
        <textarea id="setSystemPrompt" rows="4" style="width:100%;padding:8px;background:var(--bg-input);border:1px solid var(--border);border-radius:var(--radius);color:var(--text-primary);font-size:13px;resize:vertical;outline:none;font-family:inherit;">${s.systemPrompt}</textarea>
      </div>
      <div class="setting-group"><label>API Base URL</label><input type="text" id="setApiBase" value="http://localhost:8000" /></div>
      <button class="setting-btn" id="btnSaveSettings">Save Settings</button>
      <button class="setting-btn" id="btnClearData" style="background:var(--red);margin-top:8px;">Clear All Data</button>
    `);
    document.getElementById('setTemp').addEventListener('input', (e) => {
      document.getElementById('setTempVal').textContent = e.target.value;
    });
    document.getElementById('btnSaveSettings').addEventListener('click', () => this.save());
    document.getElementById('btnClearData').addEventListener('click', () => this.clearData());
  },

  save() {
    App.state.settings.model = document.getElementById('setModel').value;
    App.state.settings.temperature = parseFloat(document.getElementById('setTemp').value);
    App.state.settings.maxTokens = parseInt(document.getElementById('setMaxTokens').value);
    App.state.settings.systemPrompt = document.getElementById('setSystemPrompt').value;
    document.getElementById('modelInfo').textContent = 'Model: ' + App.state.settings.model;
    App.saveState();
    App.showToast('Settings saved');
  },

  clearData() {
    if (confirm('Clear all chat history and settings?')) {
      localStorage.removeItem('serpentai_state');
      App.state.chats = {};
      App.state.currentChatId = null;
      Sidebar.render();
      Chat.renderWelcome();
      App.showToast('Data cleared');
    }
  },
  init() {},
  populateModels() {}
};
