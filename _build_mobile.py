#!/usr/bin/env python3
"""构建 SerpentAI 移动端客户端所有文件"""
import os

BASE = os.path.join(os.path.dirname(__file__), 'mobile')
COMP = os.path.join(BASE, 'src', 'components')
os.makedirs(COMP, exist_ok=True)

def w(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  ✓ {path}')

# ===================== index.html =====================
w('index.html', r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no">
    <meta name="theme-color" content="#1a1a2e" media="(prefers-color-scheme: dark)">
    <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="SerpentAI">
    <link rel="manifest" href="manifest.json">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%90%8D%3C/text%3E%3C/svg%3E">
    <title>SerpentAI</title>
    <link rel="stylesheet" href="src/styles.css">
</head>
<body>
    <div id="app">
        <header class="app-header">
            <div class="header-left">
                <span class="logo">&#x1F40D;</span>
                <h1 class="header-title">SerpentAI</h1>
            </div>
            <div class="header-right">
                <button id="btn-theme" class="icon-btn" aria-label="切换主题">
                    <span class="theme-icon">&#x1F319;</span>
                </button>
                <button id="btn-menu" class="icon-btn" aria-label="更多选项">
                    <span>&#x22EE;</span>
                </button>
            </div>
        </header>
        <main class="app-content">
            <div id="view-container"></div>
        </main>
        <nav class="bottom-nav">
            <button class="nav-item active" data-view="chat">
                <span class="nav-icon">&#x1F4AC;</span>
                <span class="nav-label">聊天</span>
            </button>
            <button class="nav-item" data-view="voice">
                <span class="nav-icon">&#x1F3A4;</span>
                <span class="nav-label">语音</span>
            </button>
            <button class="nav-item" data-view="skills">
                <span class="nav-icon">&#x1F9E9;</span>
                <span class="nav-label">技能</span>
            </button>
            <button class="nav-item" data-view="settings">
                <span class="nav-icon">&#x2699;&#xFE0F;</span>
                <span class="nav-label">设置</span>
            </button>
        </nav>
    </div>
    <div id="install-banner" class="install-banner hidden">
        <span>&#x1F40D; 将 SerpentAI 添加到主屏幕</span>
        <button id="btn-install" class="install-btn">安装</button>
        <button id="btn-install-dismiss" class="install-dismiss">&times;</button>
    </div>
    <script src="src/components/MessageBubble.js"></script>
    <script src="src/components/VoiceButton.js"></script>
    <script src="src/components/ChatView.js"></script>
    <script src="src/components/VoiceView.js"></script>
    <script src="src/components/SkillsView.js"></script>
    <script src="src/components/SettingsView.js"></script>
    <script src="src/app.js"></script>
</body>
</html>
''')

# ===================== manifest.json =====================
w('manifest.json', r'''{
    "name": "SerpentAI",
    "short_name": "SerpentAI",
    "description": "终极自托管全功能AI智能体 - 移动端",
    "start_url": "/mobile/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#1a1a2e",
    "orientation": "portrait",
    "scope": "/mobile/",
    "lang": "zh-CN",
    "categories": ["productivity", "utilities"],
    "icons": [
        {
            "src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'%3E%3Crect width='192' height='192' rx='32' fill='%231a1a2e'/%3E%3Ctext x='96' y='130' text-anchor='middle' font-size='120'%3E%F0%9F%90%8D%3C/text%3E%3C/svg%3E",
            "sizes": "192x192",
            "type": "image/svg+xml"
        },
        {
            "src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'%3E%3Crect width='512' height='512' rx='64' fill='%231a1a2e'/%3E%3Ctext x='256' y='360' text-anchor='middle' font-size='320'%3E%F0%9F%90%8D%3C/text%3E%3C/svg%3E",
            "sizes": "512x512",
            "type": "image/svg+xml"
        }
    ],
    "shortcuts": [
        {
            "name": "新对话",
            "short_name": "对话",
            "url": "/mobile/#chat",
            "icons": [{"src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 96'%3E%3Ctext y='.9em' font-size='80'%3E%F0%9F%92%AC%3C/text%3E%3C/svg%3E", "sizes": "96x96", "type": "image/svg+xml"}]
        },
        {
            "name": "语音输入",
            "short_name": "语音",
            "url": "/mobile/#voice",
            "icons": [{"src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 96'%3E%3Ctext y='.9em' font-size='80'%3E%F0%9F%8E%A4%3C/text%3E%3C/svg%3E", "sizes": "96x96", "type": "image/svg+xml"}]
        }
    ]
}
''')

# ===================== sw.js =====================
w('sw.js', r'''/* SerpentAI Service Worker - 离线支持与缓存策略 */
const CACHE_NAME = 'serpentai-v1';
const STATIC_ASSETS = [
    '/mobile/',
    '/mobile/index.html',
    '/mobile/src/styles.css',
    '/mobile/src/app.js',
    '/mobile/src/components/MessageBubble.js',
    '/mobile/src/components/VoiceButton.js',
    '/mobile/src/components/ChatView.js',
    '/mobile/src/components/VoiceView.js',
    '/mobile/src/components/SkillsView.js',
    '/mobile/src/components/SettingsView.js',
    '/mobile/manifest.json',
];

const API_CACHE_NAME = 'serpentai-api-v1';
const API_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys
                .filter(k => k !== CACHE_NAME && k !== API_CACHE_NAME)
                .map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    // API requests: network-first with cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const clone = response.clone();
                    caches.open(API_CACHE_NAME).then(cache =>
                        cache.put(event.request, clone)
                    );
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }
    // Static assets: cache-first
    event.respondWith(
        caches.match(event.request)
            .then(cached => cached || fetch(event.request).then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            }))
    );
});

// Push notification support
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : { title: 'SerpentAI', body: '您有新消息' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"%3E%3Crect width="192" height="192" rx="32" fill="%231a1a2e"/%3E%3Ctext x="96" y="130" text-anchor="middle" font-size="120"%3E%F0%9F%90%8D%3C/text%3E%3C/svg%3E',
            badge: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"%3E%3Ctext y=".9em" font-size="80"%3E%F0%9F%90%8D%3C/text%3E%3C/svg%3E',
            vibrate: [200, 100, 200],
            data: data.url || ''
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        self.clients.matchAll({ type: 'window' }).then(clients => {
            for (const client of clients) {
                if (client.url.includes('/mobile/') && 'focus' in client) {
                    return client.focus();
                }
            }
            return self.clients.openWindow('/mobile/');
        })
    );
});

// Background sync
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-messages') {
        event.waitUntil(syncPendingMessages());
    }
});

async function syncPendingMessages() {
    const db = await openDB();
    const tx = db.transaction('pending', 'readonly');
    const store = tx.objectStore('pending');
    const pending = await store.getAll();
    for (const item of pending) {
        try {
            await fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item.data)
            });
            const delTx = db.transaction('pending', 'readwrite');
            delTx.objectStore('pending').delete(item.id);
        } catch (e) {
            console.error('Sync failed:', e);
        }
    }
}

function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open('serpentai-offline');
        req.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains('pending')) {
                db.createObjectStore('pending', { keyPath: 'id', autoIncrement: true });
            }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}
''')

# ===================== src/styles.css =====================
w('src/styles.css', r'''/* SerpentAI 移动端样式 - Mobile First */
:root {
    --primary: #6c5ce7;
    --primary-light: #a29bfe;
    --primary-dark: #4834d4;
    --accent: #00cec9;
    --danger: #ff6b6b;
    --success: #00b894;
    --warning: #fdcb6e;
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --safe-left: env(safe-area-inset-left, 0px);
    --safe-right: env(safe-area-inset-right, 0px);
    --header-h: 56px;
    --nav-h: 60px;
    --radius: 16px;
    --radius-sm: 10px;
    --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Light theme */
:root, [data-theme="light"] {
    --bg: #f8f9fa;
    --bg-card: #ffffff;
    --bg-input: #f1f3f5;
    --bg-bubble-user: #6c5ce7;
    --bg-bubble-ai: #ffffff;
    --text: #212529;
    --text-secondary: #868e96;
    --text-bubble-user: #ffffff;
    --text-bubble-ai: #212529;
    --border: #dee2e6;
    --shadow: 0 2px 12px rgba(0,0,0,0.08);
}

/* Dark theme */
@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
        --bg: #0f0f1a;
        --bg-card: #1a1a2e;
        --bg-input: #16213e;
        --bg-bubble-user: #6c5ce7;
        --bg-bubble-ai: #1a1a2e;
        --text: #e9ecef;
        --text-secondary: #868e96;
        --text-bubble-user: #ffffff;
        --text-bubble-ai: #e9ecef;
        --border: #2d3436;
        --shadow: 0 2px 12px rgba(0,0,0,0.3);
    }
}
[data-theme="dark"] {
    --bg: #0f0f1a;
    --bg-card: #1a1a2e;
    --bg-input: #16213e;
    --bg-bubble-user: #6c5ce7;
    --bg-bubble-ai: #1a1a2e;
    --text: #e9ecef;
    --text-secondary: #868e96;
    --text-bubble-user: #ffffff;
    --text-bubble-ai: #e9ecef;
    --border: #2d3436;
    --shadow: 0 2px 12px rgba(0,0,0,0.3);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}

html, body {
    height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", sans-serif;
    font-size: 16px;
    background: var(--bg);
    color: var(--text);
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
}

#app {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-width: 100vw;
}

/* ===== Header ===== */
.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: var(--header-h);
    padding: 0 16px;
    padding-top: var(--safe-top);
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    z-index: 100;
    flex-shrink: 0;
}
.header-left {
    display: flex;
    align-items: center;
    gap: 8px;
}
.logo {
    font-size: 24px;
}
.header-title {
    font-size: 18px;
    font-weight: 700;
}
.header-right {
    display: flex;
    gap: 4px;
}
.icon-btn {
    width: 40px;
    height: 40px;
    border: none;
    background: none;
    font-size: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--text);
    transition: background var(--transition);
}
.icon-btn:active {
    background: var(--bg-input);
}

/* ===== Main Content ===== */
.app-content {
    flex: 1;
    overflow: hidden;
    position: relative;
}
#view-container {
    width: 100%;
    height: 100%;
}
.view {
    display: none;
    flex-direction: column;
    height: 100%;
    animation: fadeIn 0.2s ease;
}
.view.active {
    display: flex;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ===== Bottom Nav ===== */
.bottom-nav {
    display: flex;
    align-items: center;
    justify-content: space-around;
    height: var(--nav-h);
    padding-bottom: var(--safe-bottom);
    background: var(--bg-card);
    border-top: 1px solid var(--border);
    flex-shrink: 0;
    z-index: 100;
}
.nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 16px;
    border: none;
    background: none;
    font-size: 11px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: color var(--transition);
    position: relative;
}
.nav-item .nav-icon {
    font-size: 22px;
    transition: transform var(--transition);
}
.nav-item.active {
    color: var(--primary);
}
.nav-item.active .nav-icon {
    transform: scale(1.15);
}
.nav-item::after {
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%) scaleX(0);
    width: 24px;
    height: 3px;
    border-radius: 2px;
    background: var(--primary);
    transition: transform var(--transition);
}
.nav-item.active::after {
    transform: translateX(-50%) scaleX(1);
}

/* ===== Chat View ===== */
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
}
.chat-messages::-webkit-scrollbar {
    width: 3px;
}
.chat-messages::-webkit-scrollbar-thumb {
    background: var(--text-secondary);
    border-radius: 3px;
}
.chat-input-bar {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    padding: 10px 12px;
    padding-bottom: calc(10px + var(--safe-bottom));
    background: var(--bg-card);
    border-top: 1px solid var(--border);
}
.chat-input-wrapper {
    flex: 1;
    display: flex;
    align-items: flex-end;
    background: var(--bg-input);
    border-radius: 22px;
    padding: 6px 14px;
    min-height: 44px;
    max-height: 120px;
}
.chat-input-wrapper textarea {
    flex: 1;
    border: none;
    background: none;
    resize: none;
    font-size: 15px;
    line-height: 1.5;
    color: var(--text);
    max-height: 100px;
    outline: none;
    font-family: inherit;
}
.chat-input-wrapper textarea::placeholder {
    color: var(--text-secondary);
}
.send-btn {
    width: 44px;
    height: 44px;
    border: none;
    background: var(--primary);
    color: #fff;
    border-radius: 50%;
    font-size: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background var(--transition), transform 0.15s;
    flex-shrink: 0;
}
.send-btn:active {
    transform: scale(0.92);
}
.send-btn:disabled {
    background: var(--text-secondary);
    opacity: 0.5;
}

/* ===== Message Bubble ===== */
.message {
    display: flex;
    margin-bottom: 10px;
    animation: bubbleIn 0.2s ease;
}
.message.user {
    justify-content: flex-end;
}
.message.assistant {
    justify-content: flex-start;
}
@keyframes bubbleIn {
    from { opacity: 0; transform: translateY(10px) scale(0.97); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}
.bubble {
    max-width: 78%;
    padding: 10px 14px;
    border-radius: var(--radius);
    font-size: 15px;
    line-height: 1.55;
    word-wrap: break-word;
    position: relative;
    box-shadow: var(--shadow);
}
.message.user .bubble {
    background: var(--bg-bubble-user);
    color: var(--text-bubble-user);
    border-bottom-right-radius: 4px;
}
.message.assistant .bubble {
    background: var(--bg-bubble-ai);
    color: var(--text-bubble-ai);
    border-bottom-left-radius: 4px;
}
.bubble pre {
    background: rgba(0,0,0,0.15);
    border-radius: 8px;
    padding: 10px;
    overflow-x: auto;
    font-size: 13px;
    margin: 6px 0;
}
.bubble code {
    font-family: "SF Mono", "Fira Code", monospace;
    font-size: 13px;
}
.bubble .msg-time {
    font-size: 11px;
    opacity: 0.6;
    margin-top: 4px;
}
.message-actions {
    display: flex;
    gap: 4px;
    margin-top: 4px;
}
.msg-action-btn {
    border: none;
    background: none;
    font-size: 14px;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    opacity: 0.7;
    transition: opacity 0.2s;
}
.msg-action-btn:active {
    opacity: 1;
}
.typing-indicator {
    display: flex;
    gap: 4px;
    padding: 8px 0;
}
.typing-indicator span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-secondary);
    animation: typingDot 1.4s infinite both;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingDot {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}

/* ===== Voice View ===== */
.voice-view {
    align-items: center;
    justify-content: center;
    gap: 32px;
    padding: 24px;
}
.voice-status {
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
    text-align: center;
}
.voice-transcript {
    width: 100%;
    min-height: 120px;
    padding: 20px;
    background: var(--bg-card);
    border-radius: var(--radius);
    font-size: 16px;
    line-height: 1.6;
    color: var(--text);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
}
.voice-result {
    width: 100%;
    padding: 20px;
    background: var(--bg-card);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
}
.voice-result h3 {
    font-size: 14px;
    color: var(--primary);
    margin-bottom: 8px;
}
.voice-result p {
    font-size: 15px;
    line-height: 1.6;
    color: var(--text);
}
.voice-btn-large {
    width: 88px;
    height: 88px;
    border-radius: 50%;
    border: 4px solid var(--primary);
    background: var(--bg-card);
    color: var(--primary);
    font-size: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all var(--transition);
    position: relative;
}
.voice-btn-large:active, .voice-btn-large.recording {
    transform: scale(1.08);
    background: var(--primary);
    color: #fff;
    border-color: var(--primary-dark);
}
.voice-btn-large.recording {
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(108,92,231,0.4); }
    50% { box-shadow: 0 0 0 16px rgba(108,92,231,0); }
}
.waveform-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    height: 40px;
}
.waveform-bar {
    width: 3px;
    background: var(--primary);
    border-radius: 3px;
    transition: height 0.1s;
}

/* ===== Skills View ===== */
.skills-view {
    padding: 16px;
    overflow-y: auto;
}
.skills-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}
.skills-header h2 {
    font-size: 20px;
    font-weight: 700;
}
.skill-category {
    margin-bottom: 20px;
}
.skill-category-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    padding-left: 4px;
}
.skill-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.skill-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    transition: transform 0.15s;
}
.skill-card:active {
    transform: scale(0.98);
}
.skill-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    background: var(--bg-input);
    flex-shrink: 0;
}
.skill-info {
    flex: 1;
    min-width: 0;
}
.skill-name {
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.skill-desc {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.skill-badge {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
    flex-shrink: 0;
}
.skill-badge.builtin {
    background: rgba(0,206,201,0.15);
    color: var(--accent);
}
.skill-badge.mcp {
    background: rgba(108,92,231,0.15);
    color: var(--primary);
}
.skill-badge.custom {
    background: rgba(253,203,110,0.15);
    color: #e17055;
}

/* ===== Settings View ===== */
.settings-view {
    padding: 16px;
    overflow-y: auto;
}
.settings-group {
    margin-bottom: 20px;
}
.settings-group-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    padding-left: 4px;
}
.settings-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    margin-bottom: 1px;
}
.settings-item:first-of-type {
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}
.settings-item:last-of-type {
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}
.settings-item:only-of-type {
    border-radius: var(--radius-sm);
}
.settings-item + .settings-item {
    border-top: none;
}
.settings-item-label {
    font-size: 15px;
}
.settings-item-desc {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
}
.toggle {
    width: 50px;
    height: 30px;
    border-radius: 15px;
    background: var(--border);
    border: none;
    position: relative;
    cursor: pointer;
    transition: background var(--transition);
    flex-shrink: 0;
}
.toggle.on {
    background: var(--primary);
}
.toggle::after {
    content: '';
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #fff;
    position: absolute;
    top: 2px;
    left: 2px;
    transition: transform var(--transition);
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.toggle.on::after {
    transform: translateX(20px);
}
.settings-select {
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--bg-input);
    color: var(--text);
    font-size: 14px;
    font-family: inherit;
}
.settings-input {
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--bg-input);
    color: var(--text);
    font-size: 14px;
    font-family: inherit;
    width: 160px;
    text-align: right;
}
.danger-btn {
    width: 100%;
    padding: 14px;
    border: none;
    background: rgba(255,107,107,0.1);
    color: var(--danger);
    font-size: 15px;
    font-weight: 600;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background var(--transition);
}
.danger-btn:active {
    background: rgba(255,107,107,0.2);
}

/* ===== Install Banner ===== */
.install-banner {
    position: fixed;
    bottom: calc(var(--nav-h) + var(--safe-bottom) + 12px);
    left: 12px;
    right: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    background: var(--bg-card);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    z-index: 200;
    font-size: 14px;
}
.install-banner.hidden {
    display: none;
}
.install-btn {
    padding: 8px 18px;
    border: none;
    background: var(--primary);
    color: #fff;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    flex-shrink: 0;
}
.install-dismiss {
    border: none;
    background: none;
    font-size: 18px;
    color: var(--text-secondary);
    cursor: pointer;
    flex-shrink: 0;
}

/* ===== Pull to Refresh ===== */
.pull-indicator {
    text-align: center;
    padding: 12px;
    font-size: 13px;
    color: var(--text-secondary);
    transition: transform 0.2s;
}

/* ===== Empty State ===== */
.empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    text-align: center;
}
.empty-state .empty-icon {
    font-size: 56px;
    margin-bottom: 16px;
}
.empty-state h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
}
.empty-state p {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ===== Loading Spinner ===== */
.spinner {
    width: 24px;
    height: 24px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin {
    to { transform: rotate(360deg); }
}

/* ===== Responsive tablet ===== */
@media (min-width: 768px) {
    .bubble {
        max-width: 65%;
    }
    .chat-messages {
        padding: 16px 24px;
    }
    .skills-view, .settings-view {
        max-width: 600px;
        margin: 0 auto;
    }
}

/* ===== Swipe hint ===== */
.swipe-container {
    position: relative;
    overflow: hidden;
}
''')

# ===================== src/components/MessageBubble.js =====================
w('src/components/MessageBubble.js', r'''/* MessageBubble - 聊天消息气泡组件 */
class MessageBubble {
    constructor(container, options = {}) {
        this.container = container;
        this.onAction = options.onAction || (() => {});
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.swipeThreshold = 60;
    }

    create(msg) {
        const div = document.createElement('div');
        div.className = `message ${msg.role}`;
        div.dataset.id = msg.id || Date.now().toString();

        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        const content = document.createElement('div');
        content.className = 'bubble-content';
        content.innerHTML = this._formatContent(msg.content);
        bubble.appendChild(content);

        if (msg.timestamp) {
            const time = document.createElement('div');
            time.className = 'msg-time';
            const d = new Date(msg.timestamp);
            time.textContent = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
            bubble.appendChild(time);
        }

        div.appendChild(bubble);

        // Swipe gestures on assistant messages
        if (msg.role === 'assistant') {
            this._addSwipeGesture(div, msg);
        }

        // Haptic feedback
        div.addEventListener('touchstart', () => {
            if (navigator.vibrate) navigator.vibrate(3);
        }, { passive: true });

        return div;
    }

    _formatContent(text) {
        if (!text) return '';
        // Code blocks
        text = text.replace(/```(\w*)\n([\s\S]*?)```/g,
            '<pre><code>$2</code></pre>');
        // Inline code
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Italic
        text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
        // Line breaks
        text = text.replace(/\n/g, '<br>');
        return text;
    }

    _addSwipeGesture(el, msg) {
        el.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });

        el.addEventListener('touchend', (e) => {
            const dx = e.changedTouches[0].clientX - this.touchStartX;
            const dy = e.changedTouches[0].clientY - this.touchStartY;
            if (Math.abs(dx) > this.swipeThreshold && Math.abs(dy) < 40) {
                if (navigator.vibrate) navigator.vibrate(15);
                if (dx > 0) {
                    this.onAction('copy', msg);
                } else {
                    this.onAction('delete', msg);
                }
            }
        }, { passive: true });
    }

    createTyping() {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.id = 'typing-indicator';
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        const typing = document.createElement('div');
        typing.className = 'typing-indicator';
        typing.innerHTML = '<span></span><span></span><span></span>';
        bubble.appendChild(typing);
        div.appendChild(bubble);
        return div;
    }
}

window.MessageBubble = MessageBubble;
''')

# ===================== src/components/VoiceButton.js =====================
w('src/components/VoiceButton.js', r'''/* VoiceButton - 语音输入按钮组件 */
class VoiceButton {
    constructor(container, options = {}) {
        this.container = container;
        this.onStart = options.onStart || (() => {});
        this.onStop = options.onStop || (() => {});
        this.onResult = options.onResult || (() => {});
        this.isRecording = false;
        this.isSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        this.recognition = null;
        this.audioCtx = null;
        this.analyser = null;
        this.bars = [];
        this.animFrame = null;

        if (this.isSupported) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.lang = 'zh-CN';
            this.recognition.interimResults = true;
            this.recognition.continuous = true;

            this.recognition.onresult = (e) => {
                let final = '';
                let interim = '';
                for (let i = e.resultIndex; i < e.results.length; i++) {
                    if (e.results[i].isFinal) {
                        final += e.results[i][0].transcript;
                    } else {
                        interim += e.results[i][0].transcript;
                    }
                }
                if (final) this.onResult(final, true);
                else if (interim) this.onResult(interim, false);
            };

            this.recognition.onerror = (e) => {
                console.warn('语音识别错误:', e.error);
                if (e.error !== 'no-speech') {
                    this.stop();
                }
            };

            this.recognition.onend = () => {
                if (this.isRecording) this.stop();
            };
        }
    }

    create() {
        const wrapper = document.createElement('div');
        wrapper.className = 'voice-btn-wrapper';
        wrapper.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:16px;';

        this.btn = document.createElement('button');
        this.btn.className = 'voice-btn-large';
        this.btn.innerHTML = '&#x1F3A4;';
        this.btn.setAttribute('aria-label', '语音输入');

        this.waveform = document.createElement('div');
        this.waveform.className = 'waveform-container';
        for (let i = 0; i < 20; i++) {
            const bar = document.createElement('div');
            bar.className = 'waveform-bar';
            bar.style.height = '4px';
            this.waveform.appendChild(bar);
            this.bars.push(bar);
        }

        if (this.isSupported) {
            this.btn.addEventListener('click', () => {
                this.isRecording ? this.stop() : this.start();
            });
        } else {
            this.btn.disabled = true;
            this.btn.style.opacity = '0.4';
            this.btn.title = '您的浏览器不支持语音识别';
        }

        wrapper.appendChild(this.btn);
        wrapper.appendChild(this.waveform);
        return wrapper;
    }

    async start() {
        if (!this.isSupported || this.isRecording) return;
        this.isRecording = true;
        this.btn.classList.add('recording');
        this.btn.innerHTML = '&#x23F9;';
        if (navigator.vibrate) navigator.vibrate(30);
        this.onStart();

        try {
            // Start waveform animation
            this._startWaveform();
            this.recognition.start();
        } catch (e) {
            console.error('启动语音识别失败:', e);
            this.stop();
        }
    }

    stop() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.btn.classList.remove('recording');
        this.btn.innerHTML = '&#x1F3A4;';
        this._stopWaveform();
        if (navigator.vibrate) navigator.vibrate(20);

        try {
            this.recognition.stop();
        } catch (e) {}
        this.onStop();
    }

    _startWaveform() {
        const animate = () => {
            this.bars.forEach((bar, i) => {
                const h = this.isRecording
                    ? Math.random() * 32 + 4
                    : 4;
                bar.style.height = h + 'px';
            });
            this.animFrame = requestAnimationFrame(animate);
        };
        animate();
    }

    _stopWaveform() {
        cancelAnimationFrame(this.animFrame);
        this.bars.forEach(bar => { bar.style.height = '4px'; });
    }

    destroy() {
        this.stop();
        if (this.audioCtx) this.audioCtx.close();
    }
}

window.VoiceButton = VoiceButton;
''')

# ===================== src/components/ChatView.js =====================
w('src/components/ChatView.js', r'''/* ChatView - 聊天界面视图 */
class ChatView {
    constructor(api) {
        this.api = api;
        this.bubble = new MessageBubble();
        this.messages = [];
        this.sessionId = this._getOrCreateSession();
        this.isLoading = false;
        this.isPulling = false;
        this.pullStartY = 0;
        this.pullEl = null;
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view active';
        view.id = 'chat-view';

        // Pull indicator
        this.pullEl = document.createElement('div');
        this.pullEl.className = 'pull-indicator';
        this.pullEl.textContent = '下拉刷新';
        this.pullEl.style.opacity = '0';
        view.appendChild(this.pullEl);

        // Messages container
        this.msgContainer = document.createElement('div');
        this.msgContainer.className = 'chat-messages';
        this._addPullToRefresh(this.msgContainer);

        // Load stored messages
        this._loadMessages();
        if (this.messages.length === 0) {
            this.msgContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#x1F40D;</div>
                    <h3>SerpentAI</h3>
                    <p>我是您的AI智能助手，随时为您效劳。<br>有什么我可以帮您的吗？</p>
                </div>`;
        } else {
            this.messages.forEach(msg => {
                this.msgContainer.appendChild(this.bubble.create(msg));
            });
        }
        view.appendChild(this.msgContainer);

        // Input bar
        this.inputBar = document.createElement('div');
        this.inputBar.className = 'chat-input-bar';

        this.inputWrapper = document.createElement('div');
        this.inputWrapper.className = 'chat-input-wrapper';

        this.textarea = document.createElement('textarea');
        this.textarea.placeholder = '输入消息...';
        this.textarea.rows = 1;
        this.textarea.addEventListener('input', () => this._autoResize());
        this.textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._sendMessage();
            }
        });

        this.inputWrapper.appendChild(this.textarea);

        this.sendBtn = document.createElement('button');
        this.sendBtn.className = 'send-btn';
        this.sendBtn.innerHTML = '&#x2191;';
        this.sendBtn.disabled = true;
        this.sendBtn.addEventListener('click', () => this._sendMessage());

        this.inputBar.appendChild(this.inputWrapper);
        this.inputBar.appendChild(this.sendBtn);
        view.appendChild(this.inputBar);

        // Watch textarea for enabling send
        this.textarea.addEventListener('input', () => {
            this.sendBtn.disabled = !this.textarea.value.trim();
        });

        return view;
    }

    _getOrCreateSession() {
        let sid = localStorage.getItem('serpent_session_id');
        if (!sid) {
            sid = 'mobile_' + Date.now() + '_' + Math.random().toString(36).substr(2, 8);
            localStorage.setItem('serpent_session_id', sid);
        }
        return sid;
    }

    _autoResize() {
        this.textarea.style.height = 'auto';
        this.textarea.style.height = Math.min(this.textarea.scrollHeight, 100) + 'px';
    }

    async _sendMessage() {
        const text = this.textarea.value.trim();
        if (!text || this.isLoading) return;

        // Clear empty state
        const empty = this.msgContainer.querySelector('.empty-state');
        if (empty) empty.remove();

        const userMsg = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
            timestamp: Date.now()
        };

        this.messages.push(userMsg);
        this.msgContainer.appendChild(this.bubble.create(userMsg));
        this._saveMessages();

        this.textarea.value = '';
        this.textarea.style.height = 'auto';
        this.sendBtn.disabled = true;
        this._scrollToBottom();

        // Show typing indicator
        this.isLoading = true;
        const typing = this.bubble.createTyping();
        this.msgContainer.appendChild(typing);
        this._scrollToBottom();

        try {
            const response = await this.api.chat(this.sessionId, text);
            this.msgContainer.removeChild(typing);

            const aiMsg = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.response || response.content || '（无响应）',
                timestamp: Date.now(),
                model: response.model,
                usage: response.usage
            };
            this.messages.push(aiMsg);
            this.msgContainer.appendChild(this.bubble.create(aiMsg));
            this._saveMessages();
        } catch (e) {
            this.msgContainer.removeChild(typing);
            const errMsg = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `请求失败: ${e.message}`,
                timestamp: Date.now()
            };
            this.messages.push(errMsg);
            this.msgContainer.appendChild(this.bubble.create(errMsg));
        }

        this.isLoading = false;
        this._scrollToBottom();
    }

    _scrollToBottom() {
        requestAnimationFrame(() => {
            this.msgContainer.scrollTop = this.msgContainer.scrollHeight;
        });
    }

    _loadMessages() {
        try {
            const data = localStorage.getItem('serpent_messages');
            if (data) this.messages = JSON.parse(data);
        } catch (e) {
            this.messages = [];
        }
    }

    _saveMessages() {
        try {
            // Keep last 200 messages
            const toSave = this.messages.slice(-200);
            localStorage.setItem('serpent_messages', JSON.stringify(toSave));
        } catch (e) {
            console.warn('保存消息失败:', e);
        }
    }

    clearChat() {
        this.messages = [];
        localStorage.removeItem('serpent_messages');
        this.msgContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">&#x1F40D;</div>
                <h3>SerpentAI</h3>
                <p>我是您的AI智能助手，随时为您效劳。<br>有什么我可以帮您的吗？</p>
            </div>`;
    }

    _addPullToRefresh(el) {
        el.addEventListener('touchstart', (e) => {
            if (el.scrollTop <= 0) {
                this.pullStartY = e.touches[0].clientY;
                this.isPulling = true;
            }
        }, { passive: true });

        el.addEventListener('touchmove', (e) => {
            if (!this.isPulling) return;
            const dy = e.touches[0].clientY - this.pullStartY;
            if (dy > 0 && dy < 120) {
                this.pullEl.style.opacity = Math.min(dy / 80, 1);
                this.pullEl.textContent = dy > 60 ? '松开刷新' : '下拉刷新';
            }
        }, { passive: true });

        el.addEventListener('touchend', (e) => {
            if (!this.isPulling) return;
            this.isPulling = false;
            this.pullEl.style.opacity = '0';
            const dy = e.changedTouches[0].clientY - this.pullStartY;
            if (dy > 60) {
                if (navigator.vibrate) navigator.vibrate(10);
                this._refreshChat();
            }
        }, { passive: true });
    }

    async _refreshChat() {
        try {
            const health = await fetch('/health').then(r => r.json());
            if (health.status === 'healthy') {
                this.pullEl.textContent = '已连接';
            } else {
                this.pullEl.textContent = '服务异常';
            }
        } catch {
            this.pullEl.textContent = '离线模式';
        }
        setTimeout(() => { this.pullEl.style.opacity = '0'; }, 1500);
    }
}

window.ChatView = ChatView;
''')

# ===================== src/components/VoiceView.js =====================
w('src/components/VoiceView.js', r'''/* VoiceView - 语音交互视图 */
class VoiceView {
    constructor(api) {
        this.api = api;
        this.voiceBtn = new VoiceButton(null, {
            onStart: () => this._onStart(),
            onStop: () => this._onStop(),
            onResult: (text, isFinal) => this._onResult(text, isFinal)
        });
        this.fullTranscript = '';
        this.isProcessing = false;
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view';
        view.id = 'voice-view';

        // Status
        this.statusEl = document.createElement('div');
        this.statusEl.className = 'voice-status';
        this.statusEl.textContent = '点击麦克风开始说话';
        view.appendChild(this.statusEl);

        // Voice button
        const btnWrapper = this.voiceBtn.create();
        view.appendChild(btnWrapper);

        // Transcript
        this.transcriptEl = document.createElement('div');
        this.transcriptEl.className = 'voice-transcript';
        this.transcriptEl.textContent = '识别到的文字将显示在这里...';
        view.appendChild(this.transcriptEl);

        // AI Response
        this.resultEl = document.createElement('div');
        this.resultEl.className = 'voice-result hidden';
        view.appendChild(this.resultEl);

        // Submit button (for sending voice text to chat)
        this.submitBtn = document.createElement('button');
        this.submitBtn.className = 'send-btn';
        this.submitBtn.innerHTML = '&#x27A4; 发送到聊天';
        this.submitBtn.style.cssText = 'width:auto;padding:12px 24px;border-radius:24px;font-size:15px;';
        this.submitBtn.disabled = true;
        this.submitBtn.addEventListener('click', () => this._sendToChat());
        view.appendChild(this.submitBtn);

        return view;
    }

    _onStart() {
        this.statusEl.textContent = '正在聆听...';
        this.fullTranscript = '';
        this.transcriptEl.textContent = '正在识别...';
        this.resultEl.classList.add('hidden');
        this.submitBtn.disabled = true;
    }

    _onStop() {
        if (!this.fullTranscript.trim()) {
            this.statusEl.textContent = '未检测到语音，请重试';
            return;
        }
        this.statusEl.textContent = '识别完成';
        this.submitBtn.disabled = false;
    }

    _onResult(text, isFinal) {
        if (isFinal) {
            this.fullTranscript += text;
            this.transcriptEl.textContent = this.fullTranscript;
        } else {
            this.transcriptEl.textContent = this.fullTranscript + text;
        }
    }

    async _sendToChat() {
        if (!this.fullTranscript.trim() || this.isProcessing) return;
        this.isProcessing = true;
        this.submitBtn.disabled = true;
        this.statusEl.textContent = '正在思考...';

        try {
            const response = await this.api.chat(
                localStorage.getItem('serpent_session_id') || 'mobile_voice',
                this.fullTranscript
            );
            this.resultEl.classList.remove('hidden');
            this.resultEl.innerHTML = `
                <h3>&#x1F40D; SerpentAI 回复</h3>
                <p>${this._formatContent(response.response || response.content || '无响应')}</p>`;
            this.statusEl.textContent = '回复完成';

            // Speak the response if available
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(response.response || response.content || '');
                utterance.lang = 'zh-CN';
                utterance.rate = 1.1;
                speechSynthesis.speak(utterance);
            }
        } catch (e) {
            this.statusEl.textContent = `请求失败: ${e.message}`;
        }

        this.isProcessing = false;
    }

    _formatContent(text) {
        return text
            .replace(/```[\s\S]*?```/g, '<pre style="font-size:12px;overflow-x:auto;padding:8px;background:rgba(0,0,0,0.1);border-radius:6px;margin:4px 0">$&</pre>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }
}

window.VoiceView = VoiceView;
''')

# ===================== src/components/SkillsView.js =====================
w('src/components/SkillsView.js', r'''/* SkillsView - 技能/工具管理视图 */
class SkillsView {
    constructor(api) {
        this.api = api;
        this.tools = [];
        this.categories = [];
        this.isLoading = false;
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view';
        view.id = 'skills-view';

        this.container = document.createElement('div');
        this.container.className = 'skills-view';
        view.appendChild(this.container);

        this._render();

        // Auto-load on first show
        if (this.tools.length === 0) this.loadTools();

        return view;
    }

    _render() {
        this.container.innerHTML = `
            <div class="skills-header">
                <h2>&#x1F9E9; 技能中心</h2>
                <button class="icon-btn" id="btn-reload-skills" aria-label="刷新">&#x1F504;</button>
            </div>
            <div id="skills-loading" style="text-align:center;padding:40px;">
                <div class="spinner" style="margin:0 auto 12px;"></div>
                <p style="color:var(--text-secondary);font-size:14px;">正在加载技能...</p>
            </div>
            <div id="skills-content"></div>`;

        document.getElementById('btn-reload-skills').addEventListener('click', () => {
            this.loadTools();
        });
    }

    async loadTools() {
        if (this.isLoading) return;
        this.isLoading = true;

        const loading = document.getElementById('skills-loading');
        const content = document.getElementById('skills-content');
        if (loading) loading.style.display = '';
        if (content) content.innerHTML = '';

        try {
            const data = await this.api.getTools();
            this.tools = data.tools || [];
            this.categories = data.categories || [];

            if (this.tools.length === 0) {
                if (content) content.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">&#x1F9E9;</div>
                        <h3>暂无技能</h3>
                        <p>请确保后端服务已启动并注册了工具</p>
                    </div>`;
                return;
            }

            this._renderTools(content);
        } catch (e) {
            if (content) content.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#x26A0;&#xFE0F;</div>
                    <h3>加载失败</h3>
                    <p>${e.message}<br>请检查后端连接: ${this.api.baseUrl}</p>
                </div>`;
        }

        if (loading) loading.style.display = 'none';
        this.isLoading = false;
    }

    _renderTools(container) {
        if (!container) return;

        // Group by category
        const grouped = {};
        this.tools.forEach(tool => {
            const cat = tool.category || '其他';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(tool);
        });

        const iconMap = {
            'search': '&#x1F50D;', 'file': '&#x1F4C4;', 'web': '&#x1F310;',
            'system': '&#x2699;&#xFE0F;', 'communication': '&#x1F4E8;',
            'productivity': '&#x1F4DD;', 'custom': '&#x2728;',
            '其他': '&#x1F527;'
        };

        let html = '';
        for (const [cat, tools] of Object.entries(grouped)) {
            const icon = iconMap[cat] || '&#x1F527;';
            html += `<div class="skill-category">
                <div class="skill-category-title">${icon} ${cat}</div>
                <div class="skill-list">`;

            tools.forEach(tool => {
                const badgeClass = tool.type === 'builtin' ? 'builtin' : tool.type === 'mcp' ? 'mcp' : 'custom';
                const badgeText = tool.type === 'builtin' ? '内置' : tool.type === 'mcp' ? 'MCP' : '自定义';
                const desc = (tool.description || '').substring(0, 50);

                html += `<div class="skill-card" data-tool="${this._escAttr(tool.name || tool.tool_name)}">
                    <div class="skill-icon">${icon}</div>
                    <div class="skill-info">
                        <div class="skill-name">${this._esc(tool.name || tool.tool_name)}</div>
                        <div class="skill-desc">${this._esc(desc)}</div>
                    </div>
                    <span class="skill-badge ${badgeClass}">${badgeText}</span>
                </div>`;
            });

            html += '</div></div>';
        }

        container.innerHTML = html;

        // Tap to show details
        container.querySelectorAll('.skill-card').forEach(card => {
            card.addEventListener('click', () => {
                if (navigator.vibrate) navigator.vibrate(5);
                const name = card.dataset.tool;
                this._showToolDetail(name);
            });
        });
    }

    _showToolDetail(name) {
        const tool = this.tools.find(t => (t.name || t.tool_name) === name);
        if (!tool) return;

        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:300;display:flex;align-items:flex-end;justify-content:center;';
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });

        const sheet = document.createElement('div');
        sheet.style.cssText = 'background:var(--bg-card);border-radius:20px 20px 0 0;padding:20px;padding-bottom:calc(20px + var(--safe-bottom));width:100%;max-width:500px;max-height:60vh;overflow-y:auto;animation:slideUp 0.3s ease;';
        sheet.innerHTML = `
            <style>@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }</style>
            <div style="width:40px;height:4px;border-radius:2px;background:var(--border);margin:0 auto 16px;"></div>
            <h3 style="font-size:18px;margin-bottom:8px;">${this._esc(tool.name || tool.tool_name)}</h3>
            <p style="color:var(--text-secondary);font-size:14px;line-height:1.5;margin-bottom:12px;">${this._esc(tool.description || '暂无描述')}</p>
            ${tool.parameters ? `<pre style="font-size:12px;padding:12px;background:var(--bg-input);border-radius:8px;overflow-x:auto;">${this._esc(JSON.stringify(tool.parameters, null, 2))}</pre>` : ''}
            <div style="margin-top:12px;">
                <span class="skill-badge ${tool.type === 'builtin' ? 'builtin' : tool.type === 'mcp' ? 'mcp' : 'custom'}">${tool.type || 'unknown'}</span>
                ${tool.category ? `<span style="font-size:12px;color:var(--text-secondary);margin-left:8px;">${this._esc(tool.category)}</span>` : ''}
            </div>`;

        overlay.appendChild(sheet);
        document.body.appendChild(overlay);
    }

    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    _escAttr(s) {
        return (s || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
}

window.SkillsView = SkillsView;
''')

# ===================== src/components/SettingsView.js =====================
w('src/components/SettingsView.js', r'''/* SettingsView - 设置面板视图 */
class SettingsView {
    constructor(api) {
        this.api = api;
        this.settings = this._loadSettings();
    }

    render() {
        const view = document.createElement('div');
        view.className = 'view';
        view.id = 'settings-view';

        this.container = document.createElement('div');
        this.container.className = 'settings-view';
        view.appendChild(this.container);

        this._renderSettings();
        return view;
    }

    _renderSettings() {
        this.container.innerHTML = `
            <div class="settings-group">
                <div class="settings-group-title">通用</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">API 地址</div>
                        <div class="settings-item-desc">后端服务地址</div>
                    </div>
                    <input type="text" class="settings-input" id="setting-api-url"
                        value="${this._esc(this.settings.apiUrl || 'http://localhost:8000')}"
                        placeholder="http://localhost:8000">
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">模型</div>
                        <div class="settings-item-desc">默认对话模型</div>
                    </div>
                    <select class="settings-select" id="setting-model">
                        <option value="gpt-4o" ${this.settings.model === 'gpt-4o' ? 'selected' : ''}>GPT-4o</option>
                        <option value="gpt-4o-mini" ${this.settings.model === 'gpt-4o-mini' ? 'selected' : ''}>GPT-4o Mini</option>
                        <option value="gpt-3.5-turbo" ${this.settings.model === 'gpt-3.5-turbo' ? 'selected' : ''}>GPT-3.5 Turbo</option>
                        <option value="claude-3-5-sonnet" ${this.settings.model === 'claude-3-5-sonnet' ? 'selected' : ''}>Claude 3.5 Sonnet</option>
                        <option value="claude-3-haiku" ${this.settings.model === 'claude-3-haiku' ? 'selected' : ''}>Claude 3 Haiku</option>
                    </select>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">会话ID</div>
                        <div class="settings-item-desc">${this._esc(this._getSessionId())}</div>
                    </div>
                    <button class="icon-btn" id="btn-copy-session" aria-label="复制">&#x1F4CB;</button>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">界面</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">深色模式</div>
                        <div class="settings-item-desc">切换深色/浅色主题</div>
                    </div>
                    <button class="toggle ${this.settings.theme === 'dark' || (!this.settings.theme && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'on' : ''}" id="setting-theme"></button>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">触觉反馈</div>
                        <div class="settings-item-desc">操作时振动</div>
                    </div>
                    <button class="toggle ${this.settings.haptic !== false ? 'on' : ''}" id="setting-haptic"></button>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">语音</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">语音回复</div>
                        <div class="settings-item-desc">语音模式下朗读AI回复</div>
                    </div>
                    <button class="toggle ${this.settings.voiceReply !== false ? 'on' : ''}" id="setting-voice-reply"></button>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">识别语言</div>
                        <div class="settings-item-desc">语音识别语言</div>
                    </div>
                    <select class="settings-select" id="setting-lang">
                        <option value="zh-CN" ${this.settings.lang === 'zh-CN' ? 'selected' : ''}>中文</option>
                        <option value="en-US" ${this.settings.lang === 'en-US' ? 'selected' : ''}>English</option>
                        <option value="ja-JP" ${this.settings.lang === 'ja-JP' ? 'selected' : ''}>日本語</option>
                    </select>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">数据</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">消息数量</div>
                        <div class="settings-item-desc">本地存储的消息条数</div>
                    </div>
                    <span style="color:var(--text-secondary);font-size:14px;">${this._getMessageCount()}</span>
                </div>
                <div style="padding:8px 0;">
                    <button class="danger-btn" id="btn-clear-chat">清空聊天记录</button>
                </div>
                <div style="padding:4px 0;">
                    <button class="danger-btn" id="btn-clear-session">重置会话</button>
                </div>
            </div>

            <div class="settings-group">
                <div class="settings-group-title">关于</div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">版本</div>
                        <div class="settings-item-desc">SerpentAI Mobile v1.0.0</div>
                    </div>
                </div>
                <div class="settings-item">
                    <div>
                        <div class="settings-item-label">PWA</div>
                        <div class="settings-item-desc">${window.matchMedia('(display-mode: standalone)').matches ? '已安装' : '未安装'}</div>
                    </div>
                    <span style="color:${window.matchMedia('(display-mode: standalone)').matches ? 'var(--success)' : 'var(--text-secondary)'};font-size:14px;">${window.matchMedia('(display-mode: standalone)').matches ? '&#x2705;' : '&#x274C;'}</span>
                </div>
            </div>
        `;

        this._bindEvents();
    }

    _bindEvents() {
        // API URL
        const apiInput = document.getElementById('setting-api-url');
        if (apiInput) {
            apiInput.addEventListener('change', () => {
                this.settings.apiUrl = apiInput.value.replace(/\/+$/, '');
                this._saveSettings();
                this.api.baseUrl = this.settings.apiUrl;
            });
        }

        // Model
        const modelSelect = document.getElementById('setting-model');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                this.settings.model = modelSelect.value;
                this._saveSettings();
            });
        }

        // Copy session
        const copyBtn = document.getElementById('btn-copy-session');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(this._getSessionId()).then(() => {
                    if (navigator.vibrate) navigator.vibrate(10);
                    copyBtn.innerHTML = '&#x2705;';
                    setTimeout(() => { copyBtn.innerHTML = '&#x1F4CB;'; }, 1500);
                });
            });
        }

        // Theme toggle
        const themeToggle = document.getElementById('setting-theme');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                themeToggle.classList.toggle('on');
                const isDark = themeToggle.classList.contains('on');
                this.settings.theme = isDark ? 'dark' : 'light';
                this._saveSettings();
                document.documentElement.setAttribute('data-theme', this.settings.theme);
            });
        }

        // Haptic toggle
        const hapticToggle = document.getElementById('setting-haptic');
        if (hapticToggle) {
            hapticToggle.addEventListener('click', () => {
                hapticToggle.classList.toggle('on');
                this.settings.haptic = hapticToggle.classList.contains('on');
                this._saveSettings();
            });
        }

        // Voice reply toggle
        const voiceReplyToggle = document.getElementById('setting-voice-reply');
        if (voiceReplyToggle) {
            voiceReplyToggle.addEventListener('click', () => {
                voiceReplyToggle.classList.toggle('on');
                this.settings.voiceReply = voiceReplyToggle.classList.contains('on');
                this._saveSettings();
            });
        }

        // Language
        const langSelect = document.getElementById('setting-lang');
        if (langSelect) {
            langSelect.addEventListener('change', () => {
                this.settings.lang = langSelect.value;
                this._saveSettings();
            });
        }

        // Clear chat
        const clearChatBtn = document.getElementById('btn-clear-chat');
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', () => {
                if (confirm('确定要清空聊天记录吗？')) {
                    localStorage.removeItem('serpent_messages');
                    this._renderSettings();
                    if (navigator.vibrate) navigator.vibrate(20);
                }
            });
        }

        // Clear session
        const clearSessionBtn = document.getElementById('btn-clear-session');
        if (clearSessionBtn) {
            clearSessionBtn.addEventListener('click', async () => {
                if (confirm('确定要重置会话吗？这将清除服务端上下文。')) {
                    const sid = this._getSessionId();
                    try {
                        await this.api.resetSession(sid);
                    } catch (e) {}
                    localStorage.removeItem('serpent_session_id');
                    localStorage.removeItem('serpent_messages');
                    this._renderSettings();
                    if (navigator.vibrate) navigator.vibrate(20);
                }
            });
        }
    }

    _loadSettings() {
        try {
            const data = localStorage.getItem('serpent_settings');
            return data ? JSON.parse(data) : {};
        } catch { return {}; }
    }

    _saveSettings() {
        localStorage.setItem('serpent_settings', JSON.stringify(this.settings));
    }

    _getSessionId() {
        return localStorage.getItem('serpent_session_id') || 'N/A';
    }

    _getMessageCount() {
        try {
            const msgs = JSON.parse(localStorage.getItem('serpent_messages') || '[]');
            return msgs.length;
        } catch { return 0; }
    }

    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }
}

window.SettingsView = SettingsView;
''')

# ===================== src/app.js =====================
w('src/app.js', r'''/* SerpentAI Mobile App - 主应用入口 */
(function() {
    'use strict';

    // ===== API Client =====
    class SerpentAPI {
        constructor() {
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            this.baseUrl = (settings.apiUrl || 'http://localhost:8000').replace(/\/+$/, '');
        }

        get _model() {
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            return settings.model || 'gpt-4o';
        }

        async chat(sessionId, message) {
            const res = await fetch(`${this.baseUrl}/api/agent/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId,
                    model: this._model
                })
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            return res.json();
        }

        async getTools(params = {}) {
            const query = new URLSearchParams();
            if (params.category) query.set('category', params.category);
            if (params.type) query.set('tool_type', params.type);
            const res = await fetch(`${this.baseUrl}/api/tools?${query}`);
            if (!res.ok) throw new Error(`获取工具列表失败: ${res.status}`);
            return res.json();
        }

        async getToolCategories() {
            const res = await fetch(`${this.baseUrl}/api/tools/categories`);
            if (!res.ok) throw new Error(`获取分类失败: ${res.status}`);
            return res.json();
        }

        async resetSession(sessionId) {
            const res = await fetch(`${this.baseUrl}/api/agent/reset?session_id=${encodeURIComponent(sessionId)}`, {
                method: 'POST'
            });
            if (!res.ok) throw new Error(`重置会话失败: ${res.status}`);
            return res.json();
        }

        async getHealth() {
            const res = await fetch(`${this.baseUrl}/health`);
            return res.json();
        }

        async getStats() {
            const res = await fetch(`${this.baseUrl}/api/agent/stats`);
            if (!res.ok) throw new Error(`获取统计失败: ${res.status}`);
            return res.json();
        }
    }

    // ===== App Controller =====
    class App {
        constructor() {
            this.api = new SerpentAPI();
            this.currentView = 'chat';
            this.views = {};
            this.ws = null;
        }

        init() {
            // Apply saved theme
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            if (settings.theme) {
                document.documentElement.setAttribute('data-theme', settings.theme);
                this._updateThemeIcon(settings.theme);
            } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                this._updateThemeIcon('dark');
            }

            // Initialize views
            this.views.chat = new ChatView(this.api);
            this.views.voice = new VoiceView(this.api);
            this.views.skills = new SkillsView(this.api);
            this.views.settings = new SettingsView(this.api);

            // Render initial view
            const container = document.getElementById('view-container');
            Object.values(this.views).forEach(view => {
                container.appendChild(view.render());
            });

            // Navigation
            document.querySelectorAll('.nav-item').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const viewName = btn.dataset.view;
                    if (navigator.vibrate) navigator.vibrate(5);
                    this.switchView(viewName);
                });
            });

            // Theme toggle in header
            document.getElementById('btn-theme').addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'light' ? 'dark' : current === 'dark' ? 'light' : 'light';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('serpent_settings', JSON.stringify({
                    ...JSON.parse(localStorage.getItem('serpent_settings') || '{}'),
                    theme: next
                }));
                this._updateThemeIcon(next);
                if (navigator.vibrate) navigator.vibrate(5);
            });

            // Menu button
            document.getElementById('btn-menu').addEventListener('click', () => {
                this.switchView('settings');
            });

            // Register service worker
            this._registerSW();

            // PWA install prompt
            this._setupInstallPrompt();

            // WebSocket for real-time updates
            this._connectWebSocket();
        }

        switchView(name) {
            if (!this.views[name]) return;
            this.currentView = name;

            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            const targetView = document.getElementById(name + '-view');
            if (targetView) targetView.classList.add('active');

            document.querySelectorAll('.nav-item').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.view === name);
            });

            // Lazy-load skills
            if (name === 'skills') {
                this.views.skills.loadTools();
            }
        }

        _updateThemeIcon(theme) {
            const icon = document.querySelector('.theme-icon');
            if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }

        _registerSW() {
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/mobile/sw.js')
                    .then(reg => console.log('SW registered:', reg.scope))
                    .catch(err => console.warn('SW registration failed:', err));
            }
        }

        _setupInstallPrompt() {
            let deferredPrompt;
            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                deferredPrompt = e;
                const banner = document.getElementById('install-banner');
                if (banner) banner.classList.remove('hidden');
            });

            const installBtn = document.getElementById('btn-install');
            if (installBtn) {
                installBtn.addEventListener('click', async () => {
                    if (!deferredPrompt) return;
                    deferredPrompt.prompt();
                    const result = await deferredPrompt.userChoice;
                    if (result.outcome === 'accepted') {
                        if (navigator.vibrate) navigator.vibrate(30);
                    }
                    deferredPrompt = null;
                    document.getElementById('install-banner').classList.add('hidden');
                });
            }

            const dismissBtn = document.getElementById('btn-install-dismiss');
            if (dismissBtn) {
                dismissBtn.addEventListener('click', () => {
                    document.getElementById('install-banner').classList.add('hidden');
                });
            }
        }

        _connectWebSocket() {
            const settings = JSON.parse(localStorage.getItem('serpent_settings') || '{}');
            const wsUrl = (settings.apiUrl || 'http://localhost:8000')
                .replace('http', 'ws') + '/ws';

            try {
                this.ws = new WebSocket(wsUrl);
                this.ws.onopen = () => console.log('WebSocket connected');
                this.ws.onmessage = (e) => {
                    try {
                        const data = JSON.parse(e.data);
                        if (data.type === 'notification') {
                            this._showNotification(data.title, data.body);
                        }
                    } catch {}
                };
                this.ws.onclose = () => {
                    // Reconnect after 5s
                    setTimeout(() => this._connectWebSocket(), 5000);
                };
                this.ws.onerror = () => this.ws.close();
            } catch {
                // WebSocket not available, fine
            }
        }

        _showNotification(title, body) {
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification(title, { body, icon: '🐍' });
            }
        }
    }

    // ===== Boot =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new App().init());
    } else {
        new App().init();
    }
})();
''')

print('\n所有文件已创建完成！')
print('文件列表:')
for root, dirs, files in os.walk(BASE):
    for f in sorted(files):
        rel = os.path.relpath(os.path.join(root, f), BASE)
        size = os.path.getsize(os.path.join(root, f))
        print(f'  {rel} ({size:,} bytes)')
