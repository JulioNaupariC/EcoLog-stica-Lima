import type { ReactNode, Ref } from 'react'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import { cx } from './cx'

export type AlertTone = 'info' | 'success' | 'warning' | 'danger'
const ICON = { info: Info, success: CheckCircle2, warning: AlertTriangle, danger: XCircle }

/** Inline message. Errors are announced assertively (role=alert), the rest politely. */
export function Alert({ tone = 'info', title, children, role, className, ref, tabIndex, actions }: {
  tone?: AlertTone
  title?: ReactNode
  children?: ReactNode
  role?: 'alert' | 'status' | 'note'
  className?: string
  ref?: Ref<HTMLDivElement>
  tabIndex?: number
  actions?: ReactNode
}) {
  const Icon = ICON[tone]
  return <div ref={ref} tabIndex={tabIndex} role={role ?? (tone === 'danger' ? 'alert' : 'status')}
    className={cx('alert', `alert--${tone}`, className)}>
    <Icon aria-hidden="true" size={20} className="alert-icon" />
    <div className="alert-body">
      {title ? <strong className="alert-title">{title}</strong> : null}
      {children ? <div className="alert-content">{children}</div> : null}
      {actions ? <div className="alert-actions">{actions}</div> : null}
    </div>
  </div>
}
