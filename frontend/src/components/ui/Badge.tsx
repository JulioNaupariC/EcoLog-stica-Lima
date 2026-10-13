import type { ReactNode } from 'react'
import { AlertTriangle, Ban, CheckCircle2, Circle, Clock, Leaf, Truck, XCircle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cx } from './cx'

export type BadgeTone = 'success' | 'neutral' | 'warning' | 'danger' | 'info' | 'sustain'

const TONE_ICON: Record<BadgeTone, LucideIcon> = {
  success: CheckCircle2,
  neutral: Circle,
  warning: AlertTriangle,
  danger: XCircle,
  info: Clock,
  sustain: Leaf,
}

/** Status pill: the text always carries the meaning; color and icon only reinforce it. */
export function Badge({ tone = 'neutral', icon, children, className }: {
  tone?: BadgeTone
  icon?: LucideIcon | null
  children: ReactNode
  className?: string
}) {
  const Icon = icon === null ? null : icon ?? TONE_ICON[tone]
  return <span className={cx('badge', `badge--${tone}`, className)}>
    {Icon ? <Icon aria-hidden="true" size={14} strokeWidth={2.25} /> : null}
    {children}
  </span>
}

export type StatusKey =
  | 'ACTIVO' | 'INACTIVO' | 'HABILITADO' | 'NO_HABILITADO' | 'VENCIDA'
  | 'PENDIENTE' | 'EN_RUTA' | 'ENTREGADO' | 'NO_ENTREGADO'

const STATUS: Record<StatusKey, { tone: BadgeTone, label: string, icon?: LucideIcon }> = {
  ACTIVO: { tone: 'success', label: 'Activo' },
  INACTIVO: { tone: 'neutral', label: 'Inactivo', icon: Ban },
  HABILITADO: { tone: 'success', label: 'Habilitado' },
  NO_HABILITADO: { tone: 'warning', label: 'No habilitado' },
  VENCIDA: { tone: 'danger', label: 'Licencia vencida' },
  PENDIENTE: { tone: 'info', label: 'Pendiente' },
  EN_RUTA: { tone: 'info', label: 'En ruta', icon: Truck },
  ENTREGADO: { tone: 'success', label: 'Entregado' },
  NO_ENTREGADO: { tone: 'danger', label: 'No entregado' },
}

export function StatusBadge({ status, className }: { status: StatusKey, className?: string }) {
  const { tone, label, icon } = STATUS[status]
  return <Badge tone={tone} icon={icon} className={className}>{label}</Badge>
}
