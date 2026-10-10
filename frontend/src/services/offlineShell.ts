export function registerOfflineShell(): void {
  if (import.meta.env.PROD && 'serviceWorker' in navigator) {
    void navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`)
      .catch(() => { /* App remains usable online; no false offline-ready claim. */ })
  }
}
