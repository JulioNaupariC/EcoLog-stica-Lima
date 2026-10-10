/* Cache only the built, public SPA shell. Never cache API, cookies or user data. */
const PREFIX = 'ecologistica-shell-'
const BUILD_VERSION = '__SHELL_VERSION__'
let shell
async function currentShell() {
  if (shell) return shell
  const names = (await caches.keys()).filter(name => name === PREFIX + BUILD_VERSION)
  for (const name of names) {
    const cache = await caches.open(name)
    const metadata = await cache.match(new URL('offline-shell.json', self.registration.scope))
    if (metadata) {
      const manifest = await metadata.json()
      shell = { cache, files: new Set(manifest.files.map(file => new URL(file, self.registration.scope).href)) }
      return shell
    }
  }
  return null
}
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const response = await fetch(new URL('offline-shell.json', self.registration.scope), { cache: 'no-store' })
    if (!response.ok) throw new Error('Offline shell unavailable')
    const manifest = await response.clone().json()
    if (manifest.version !== BUILD_VERSION) throw new Error('Shell version mismatch')
    const cache = await caches.open(PREFIX + manifest.version)
    try {
      await cache.addAll(manifest.files.map(file => new URL(file, self.registration.scope).href))
      await cache.put(new URL('offline-shell.json', self.registration.scope), response)
    } catch (error) { await caches.delete(PREFIX + manifest.version); throw error }
  })())
})
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    // Waiting workers activate only after old tabs close; do not break old chunks.
    for (const name of await caches.keys()) {
      if (name.startsWith(PREFIX) && name !== PREFIX + BUILD_VERSION) await caches.delete(name)
    }
    await self.clients.claim()
  })())
})
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== self.location.origin) return
  const base = new URL(self.registration.scope).pathname
  const navigation = request.mode === 'navigate' && ['', 'login', 'conductor/itinerario'].includes(url.pathname.slice(base.length).replace(/\/$/u, ''))
  // Only known built asset paths and approved SPA navigations can hit the cache.
  if (!navigation && !url.pathname.startsWith(base + 'assets/')) return
  event.respondWith((async () => {
    const stored = await currentShell()
    const key = navigation ? new URL('index.html', self.registration.scope).href : request.url
    if (stored && (navigation || stored.files.has(key))) {
      const cached = await stored.cache.match(key)
      if (cached) return cached
    }
    return fetch(request)
  })())
})
