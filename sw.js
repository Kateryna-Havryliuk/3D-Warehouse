// ==========================================
// SERVICE WORKER - ОФЛАЙН РЕЖИМ
// ==========================================

const CACHE_NAME = 'pragmatec-warehouse-v3';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js',
    'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js',
    'https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js'
];

// ВСТАНОВЛЕННЯ - кешуємо статику
self.addEventListener('install', (event) => {
    console.log('🔧 SW: Встановлення...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('📦 Кешуємо статичні ресурси...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('✅ SW встановлено');
                return self.skipWaiting();
            })
            .catch(err => console.error('❌ Помилка кешування:', err))
    );
});

// АКТИВАЦІЯ - чистимо старі кеші
self.addEventListener('activate', (event) => {
    console.log('🚀 SW: Активація...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME)
                    .map(name => {
                        console.log('🗑️ Видаляємо старий кеш:', name);
                        return caches.delete(name);
                    })
            );
        })
        .then(() => {
            console.log('✅ SW активовано');
            return self.clients.claim();
        })
    );
});

// ЗАПИТИ - стратегія кешування
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // API запити - Network First з fallback на кеш
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleAPIRequest(request));
        return;
    }

    // Статичні ресурси - Cache First
    event.respondWith(
        caches.match(request).then(response => {
            // Повертаємо з кешу або йдемо в мережу
            return response || fetch(request).then(fetchResponse => {
                // Кешуємо нові ресурси
                if (fetchResponse.ok) {
                    const clone = fetchResponse.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(request, clone);
                    });
                }
                return fetchResponse;
            });
        }).catch(() => {
            // Офлайн і немає в кеші
            console.log('📴 Офлайн запит:', url.pathname);
            
            // Заглушка для зображень
            if (request.destination === 'image') {
                return new Response('🖼️', { status: 200 });
            }
        })
    );
});

// Обробка API запитів
async function handleAPIRequest(request) {
    try {
        // Спробуємо мережу першою
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Кешуємо успішну відповідь для офлайну
            const clone = networkResponse.clone();
            const cache = await caches.open(CACHE_NAME);
            
            // Додаємо позначку часу
            const body = await clone.json();
            body._cachedAt = new Date().toISOString();
            body._fromCache = false;
            
            const modifiedResponse = new Response(JSON.stringify(body), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
            
            cache.put(request, modifiedResponse);
            return networkResponse;
        }
        
        return networkResponse;
        
    } catch (error) {
        // МЕРЕЖА НЕДОСТУПНА - шукаємо в кеші
        console.log('📴 Офлайн режим для:', request.url);
        
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            const body = await cachedResponse.json();
            body._fromCache = true;
            body._offline = true;
            
            return new Response(JSON.stringify(body), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        // Немає в кеші - повертаємо порожню відповідь
        return new Response(JSON.stringify({
            _offline: true,
            _error: 'Немає зєднання та даних в кеші',
            items: [],
            total_items: 0,
            total_quantity: 0
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Фонова синхронізація (коли зв'язок відновлюється)
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-warehouse-data') {
        console.log('🔄 Фонова синхронізація...');
        event.waitUntil(notifyClientsToSync());
    }
});

// Повідомлення клієнтам про синхронізацію
async function notifyClientsToSync() {
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({
            type: 'SYNC_REQUIRED',
            message: 'Відновлено зєднання. Синхронізуйте дані.'
        });
    });
}

// Отримання повідомлень від клієнта
self.addEventListener('message', (event) => {
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});