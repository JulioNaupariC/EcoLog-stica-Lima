import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { CheckCircle2, Info, X } from 'lucide-react'
import { ToastContext } from './toastContext'
import type { ToastTone } from './toastContext'

interface ToastItem { id: number, tone: ToastTone, message: string }

const TOAST_DURATION_MS = 5000

/**
 * Transient confirmations in a polite live region. Errors that need action
 * stay inline (Alert); toasts only confirm completed operations.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const next = useRef(0)
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>())

  const dismiss = useCallback((id: number) => {
    clearTimeout(timers.current.get(id))
    timers.current.delete(id)
    setItems(current => current.filter(item => item.id !== id))
  }, [])

  const notify = useCallback((message: string, tone: ToastTone = 'success') => {
    const id = ++next.current
    setItems(current => [...current.slice(-2), { id, tone, message }])
    timers.current.set(id, setTimeout(() => dismiss(id), TOAST_DURATION_MS))
  }, [dismiss])

  useEffect(() => {
    const pending = timers.current
    return () => { pending.forEach(timer => clearTimeout(timer)); pending.clear() }
  }, [])

  const value = useMemo(() => ({ notify }), [notify])
  return <ToastContext value={value}>
    {children}
    <div className="toast-region" role="region" aria-live="polite" aria-relevant="additions" aria-label="Notificaciones">
      {items.map(item => {
        const Icon = item.tone === 'success' ? CheckCircle2 : Info
        return <div key={item.id} className={`toast toast--${item.tone}`}>
          <Icon aria-hidden="true" size={20} />
          <p>{item.message}</p>
          <button type="button" className="toast-close" onClick={() => dismiss(item.id)} aria-label="Cerrar notificación">
            <X aria-hidden="true" size={18} />
          </button>
        </div>
      })}
    </div>
  </ToastContext>
}
