import { useEffect, useId, useRef } from 'react'
import type { ReactNode, RefObject } from 'react'
import { createPortal } from 'react-dom'

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'

/**
 * Modal dialog: traps Tab inside, closes with Escape and returns focus to the
 * element that opened it (WCAG 2.1 AA 2.1.2 / 2.4.3). The background is inert.
 */
export function Dialog({ title, children, actions, onClose, returnFocus, initialFocus, role = 'dialog' }: {
  title: ReactNode
  children: ReactNode
  actions: ReactNode
  onClose: () => void
  returnFocus?: RefObject<HTMLElement | null>
  initialFocus?: RefObject<HTMLElement | null>
  role?: 'dialog' | 'alertdialog'
}) {
  const titleId = useId()
  const bodyId = useId()
  const panel = useRef<HTMLDivElement>(null)
  const close = useRef(onClose)
  useEffect(() => { close.current = onClose })

  useEffect(() => {
    const opener = returnFocus?.current ?? (document.activeElement as HTMLElement | null)
    const root = document.getElementById('root')
    root?.setAttribute('inert', '')
    const first = initialFocus?.current ?? panel.current?.querySelector<HTMLElement>(FOCUSABLE)
    first?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); close.current(); return }
      if (event.key !== 'Tab' || !panel.current) return
      const items = [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)]
      if (items.length === 0) { event.preventDefault(); return }
      const [firstItem, lastItem] = [items[0], items[items.length - 1]]
      if (event.shiftKey && document.activeElement === firstItem) { event.preventDefault(); lastItem.focus() }
      else if (!event.shiftKey && document.activeElement === lastItem) { event.preventDefault(); firstItem.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      root?.removeAttribute('inert')
      opener?.focus()
    }
  }, [returnFocus, initialFocus])

  return createPortal(<div className="dialog-backdrop">
    <div ref={panel} className="dialog" role={role} aria-modal="true" aria-labelledby={titleId} aria-describedby={bodyId}>
      <h2 id={titleId} className="dialog-title">{title}</h2>
      <div id={bodyId} className="dialog-body">{children}</div>
      <div className="dialog-actions">{actions}</div>
    </div>
  </div>, document.body)
}
