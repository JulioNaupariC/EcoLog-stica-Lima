import { useEffect, useState } from 'react'

export const ONLINE_STATUS_POLL_MS = 5000

/** Browser connectivity is a hint; successful API requests prove server access. */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() => typeof navigator === 'undefined' ? true : navigator.onLine)

  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    update()
    // `online`/`offline` events are not guaranteed by every browser: re-read periodically.
    const poll = setInterval(update, ONLINE_STATUS_POLL_MS)
    return () => {
      clearInterval(poll)
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])
  return online
}
