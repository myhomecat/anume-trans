// Web Push Service Worker — 탭이 닫혀도 백그라운드에서 푸시 수신
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {}; }
  const title = data.title || '만화 번역';
  const options = {
    body: data.body || '',
    data: { url: data.url || '/' },
    tag: 'anume-job',
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((cs) => {
      for (const c of cs) { if ('focus' in c) return c.focus(); }
      return clients.openWindow(url);
    })
  );
});
