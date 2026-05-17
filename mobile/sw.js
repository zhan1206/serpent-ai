/* SerpentAI Service Worker - 离线支持与缓存策略 */
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
