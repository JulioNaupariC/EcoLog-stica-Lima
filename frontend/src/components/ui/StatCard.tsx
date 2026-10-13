import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

/** A real figure from an existing endpoint; never an estimate. */
export function StatCard({ icon: Icon, label, value, detail, loading }: {
  icon: LucideIcon
  label: string
  value: ReactNode
  detail?: ReactNode
  loading?: boolean
}) {
  return <div className="stat-card">
    <span className="stat-card-icon"><Icon aria-hidden="true" size={20} /></span>
    <dl>
      <dt className="stat-card-label">{label}</dt>
      <dd className="stat-card-value">{loading ? <span className="skeleton-line skeleton-line--value" aria-hidden="true" /> : value}</dd>
      {detail ? <dd className="stat-card-detail">{detail}</dd> : null}
    </dl>
  </div>
}
