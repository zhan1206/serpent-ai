const Sidebar = {
  render() {
    const list = document.getElementById('chatList');
    const chats = Object.values(App.state.chats).sort((a, b) => b.createdAt - a.createdAt);
    if (chats.length === 0) {
      list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;">No chat history</div>';
      return;
    }
    list.innerHTML = chats.map(c => `
      <div class="chat-item ${c.id === App.state.currentChatId ? 'active' : ''}" data-id="${c.id}">
        <span class="chat-item-title">${this.esc(c.title)}</span>
        <button class="chat-item-delete" data-delete="${c.id}" title="Delete">&#x1F5D1;</button>
      </div>
    `).join('');
    list.querySelectorAll('.chat-item').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target.closest('.chat-item-delete')) return;
        App.loadChat(el.dataset.id);
      });
    });
    list.querySelectorAll('.chat-item-delete').forEach(el => {
      el.addEventListener('click', (e) => { e.stopPropagation(); this.deleteChat(el.dataset.delete); });
    });
  },

  deleteChat(id) {
    delete App.state.chats[id];
    if (App.state.currentChatId === id) {
      const r = Object.keys(App.state.chats);
      if (r.length > 0) App.loadChat(r[0]);
      else { App.state.currentChatId = null; Chat.renderWelcome(); }
    }
    this.render();
    App.saveState();
  },

  init() {
    this.render();
    if (App.state.currentChatId && App.state.chats[App.state.currentChatId]) {
      const chat = App.state.chats[App.state.currentChatId];
      if (chat.messages.length > 0) Chat.renderMessages(chat.messages);
      else Chat.renderWelcome();
    } else {
      Chat.renderWelcome();
    }
  },

  esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
};
