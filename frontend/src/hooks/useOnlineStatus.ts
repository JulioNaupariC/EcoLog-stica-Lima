import { useEffect, useState } from 'react'

/** Browser connectivity is a hint; successful API requests prove server access. */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() => typeof navigator === 'undefined' ? true : navigator.onLine)

  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    update()
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])
  return online
}
